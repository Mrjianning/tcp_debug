import asyncio
import base64
import websockets
import socket
import json
import threading
import os
import re
import shutil
import sys
import subprocess
import ipaddress
from urllib.parse import unquote
from urllib.parse import parse_qs
from urllib.parse import urlparse

# 配置
HTTP_PORT = 8080
WS_PORT = 8765
HOST = os.environ.get("TCP_DEBUG_HOST", "0.0.0.0")
MAX_RECV_BUFFER = 1024 * 1024
WS_MAX_SIZE = None

# 当前资源所在目录。PyInstaller 打包后资源会被解压到 _MEIPASS。
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, "dist")
NETPLAN_FILE = os.environ.get("TCP_DEBUG_NETPLAN_FILE", "/etc/netplan/01-network-manager-all.yaml")


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def get_lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def validate_connect_target(ip, port):
    ip = str(ip or "").strip()
    if not ip:
        raise ValueError("服务器IP不能为空")

    try:
        port = int(port)
    except (TypeError, ValueError):
        raise ValueError("端口必须是 1-65535")

    if not 1 <= port <= 65535:
        raise ValueError("端口必须是 1-65535")

    return ip, port


def build_outgoing_payload(json_text):
    data = json.loads(json_text)
    compact_text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return compact_text.encode("utf-8") + b"\n"


def get_mapping_payload_target(message):
    if not isinstance(message, dict):
        return None
    params = message.get("params")
    if isinstance(params, dict):
        data = params.get("data")
        if isinstance(data, dict):
            return data
        return params
    return message


def export_mapping_file_if_present(message):
    target = get_mapping_payload_target(message)
    if not isinstance(target, dict):
        return None

    file_name = str(target.get("fileName") or "").strip()
    output_path = str(target.get("outPutPath") or "").strip()
    base64_data = str(target.get("base64Data") or "").strip()
    if not file_name or not output_path or not base64_data:
        return None

    safe_name = os.path.basename(file_name)
    if not safe_name:
        raise ValueError("导出文件名为空")

    output_dir = os.path.abspath(output_path)
    os.makedirs(output_dir, exist_ok=True)
    export_path = os.path.join(output_dir, safe_name)
    decoded = base64.b64decode(base64_data, validate=True)
    with open(export_path, "wb") as f:
        f.write(decoded)
    return export_path


def read_static_file(file_path, content_type):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    body = content.encode("utf-8")
    headers = (
        "HTTP/1.1 200 OK\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n"
    )
    return headers + content


def build_json_response(payload, status="200 OK"):
    content = json.dumps(payload, ensure_ascii=False)
    body = content.encode("utf-8")
    headers = (
        f"HTTP/1.1 {status}\r\n"
        "Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n"
    )
    return headers + content


def parse_http_json_body(request_text):
    header_text, sep, body = request_text.partition("\r\n\r\n")
    if not sep:
        return {}
    if not body.strip():
        return {}
    return json.loads(body)


def run_command(command, timeout=30):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except FileNotFoundError as e:
        return {"returncode": 127, "stdout": "", "stderr": str(e)}
    except subprocess.TimeoutExpired as e:
        return {"returncode": 124, "stdout": e.stdout or "", "stderr": e.stderr or f"命令超时: {' '.join(command)}"}


def read_link_carrier(interface_name):
    carrier_path = os.path.join("/sys/class/net", interface_name, "carrier")
    try:
        with open(carrier_path, "r", encoding="utf-8") as f:
            return f.read().strip() == "1"
    except OSError:
        return False


def parse_network_interfaces(ip_addr_json, carrier_reader=read_link_carrier):
    interfaces = []
    for item in ip_addr_json:
        name = str(item.get("ifname") or "").strip()
        if not name or name == "lo":
            continue
        ipv4_addresses = []
        for addr in item.get("addr_info") or []:
            if addr.get("family") == "inet" and addr.get("local"):
                prefix = addr.get("prefixlen")
                ipv4_addresses.append(f"{addr.get('local')}/{prefix}" if prefix is not None else str(addr.get("local")))
        link_detected = bool(carrier_reader(name))
        interfaces.append({
            "name": name,
            "targetName": name,
            "macAddress": str(item.get("address") or "").strip(),
            "ipv4Address": ipv4_addresses[0] if ipv4_addresses else "",
            "ipv4Addresses": ipv4_addresses,
            "linkDetected": link_detected,
            "configureEnabled": link_detected and bool(ipv4_addresses),
            "linkState": "已插入网线" if link_detected else "未插入网线",
            "operState": str(item.get("operstate") or "").strip(),
        })
    return interfaces


def list_network_interfaces(runner=run_command):
    result = runner(["ip", "-j", "addr", "show"], timeout=10)
    if result["returncode"] != 0:
        raise RuntimeError((result.get("stderr") or result.get("stdout") or "读取网口信息失败").strip())
    return parse_network_interfaces(json.loads(result["stdout"]))


def validate_mac_address(mac):
    mac = str(mac or "").strip()
    if not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac):
        raise ValueError(f"MAC地址格式错误: {mac}")
    return mac


def validate_interface_name(name):
    name = str(name or "").strip()
    if not name:
        raise ValueError("网口名称不能为空")
    if len(name) > 15 or not re.match(r"^[A-Za-z0-9_.:-]+$", name):
        raise ValueError(f"网口名称格式错误: {name}")
    return name


def validate_ipv4_cidr(value):
    value = str(value or "").strip()
    if "/" not in value:
        value = f"{value}/24"
    try:
        parsed = ipaddress.ip_interface(value)
    except ValueError:
        raise ValueError(f"IPv4地址格式错误: {value}")
    if parsed.version != 4:
        raise ValueError(f"IPv4地址格式错误: {value}")
    if not 1 <= parsed.network.prefixlen <= 30:
        raise ValueError(f"IPv4掩码长度必须是 1-30: {value}")
    return f"{parsed.ip}/{parsed.network.prefixlen}"


def normalize_network_config_entries(entries):
    normalized = []
    for entry in entries or []:
        if entry.get("enabled") is False or entry.get("configureEnabled") is False:
            continue
        normalized.append({
            "macAddress": validate_mac_address(entry.get("macAddress")),
            "targetName": validate_interface_name(entry.get("targetName") or entry.get("name")),
            "ipv4Address": validate_ipv4_cidr(entry.get("ipv4Address")),
        })
    if not normalized:
        raise ValueError("至少需要选择一个网口配置")
    return normalized


def generate_netplan_yaml(entries):
    normalized = normalize_network_config_entries(entries)
    lines = [
        "network:",
        "  version: 2",
        "  renderer: NetworkManager",
        "  ethernets:",
    ]
    for entry in normalized:
        lines.extend([
            f"    {entry['targetName']}:",
            "      match:",
            f"        macaddress: {entry['macAddress']}",
            f"      set-name: {entry['targetName']}",
            f"      addresses: [{entry['ipv4Address']}]",
            "      dhcp4: no",
        ])
    return "\n".join(lines) + "\n"


def has_invalid_static_ipv4_prefix(text):
    for value in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}/(\d{1,2})\b", text):
        prefix = int(value)
        if not 1 <= prefix <= 30:
            return True
    return False


def backup_invalid_netplan_files(netplan_dir, skip_file=None):
    repaired_files = []
    if not os.path.isdir(netplan_dir):
        return repaired_files

    skip_path = os.path.abspath(skip_file) if skip_file else ""
    for name in os.listdir(netplan_dir):
        if not name.endswith((".yaml", ".yml")):
            continue
        file_path = os.path.abspath(os.path.join(netplan_dir, name))
        if file_path == skip_path:
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        if not has_invalid_static_ipv4_prefix(content):
            continue

        backup_path = file_path + ".invalid.bak"
        suffix = 1
        while os.path.exists(backup_path):
            backup_path = f"{file_path}.invalid.{suffix}.bak"
            suffix += 1
        shutil.move(file_path, backup_path)
        repaired_files.append(backup_path)
    return repaired_files


def backup_networkmanager_generated_netplan_files(netplan_dir, skip_file=None):
    repaired_files = []
    if not os.path.isdir(netplan_dir):
        return repaired_files

    skip_path = os.path.abspath(skip_file) if skip_file else ""
    for name in os.listdir(netplan_dir):
        if not re.match(r"^90-NM-.*\.ya?ml$", name):
            continue
        file_path = os.path.abspath(os.path.join(netplan_dir, name))
        if file_path == skip_path:
            continue

        backup_path = file_path + ".tcp_debug.bak"
        suffix = 1
        while os.path.exists(backup_path):
            backup_path = f"{file_path}.tcp_debug.{suffix}.bak"
            suffix += 1
        shutil.move(file_path, backup_path)
        repaired_files.append(backup_path)
    return repaired_files


def validate_no_active_web_interface_change(entries, current_interfaces, client_ip):
    if not client_ip or client_ip in ("127.0.0.1", "::1"):
        return

    try:
        client_addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return

    active_interfaces = []
    for item in current_interfaces or []:
        ipv4_address = item.get("ipv4Address") or ""
        if not ipv4_address:
            continue
        try:
            current_interface = ipaddress.ip_interface(ipv4_address)
        except ValueError:
            continue
        if client_addr in current_interface.network:
            active_interfaces.append({
                "name": item.get("name"),
                "macAddress": str(item.get("macAddress") or "").lower(),
                "ipv4Address": f"{current_interface.ip}/{current_interface.network.prefixlen}",
            })

    if not active_interfaces:
        return

    normalized_entries = normalize_network_config_entries(entries)
    for entry in normalized_entries:
        entry_mac = entry["macAddress"].lower()
        for active in active_interfaces:
            if entry_mac != active["macAddress"]:
                continue
            if entry["targetName"] != active["name"] or entry["ipv4Address"] != active["ipv4Address"]:
                raise ValueError(
                    f"当前Web连接正在使用网口 {active['name']}({active['ipv4Address']})，"
                    "为避免失联，禁止在网页中修改该网口名称或IP；请改用本机桌面/串口/另一块网口操作"
                )


def mark_active_web_interface(interfaces, client_ip):
    marked = []
    try:
        client_addr = ipaddress.ip_address(client_ip) if client_ip else None
    except ValueError:
        client_addr = None

    for item in interfaces or []:
        next_item = dict(item)
        next_item["isActiveWebInterface"] = False
        ipv4_address = next_item.get("ipv4Address") or ""
        if client_addr and ipv4_address:
            try:
                current_interface = ipaddress.ip_interface(ipv4_address)
                if client_addr in current_interface.network:
                    next_item["isActiveWebInterface"] = True
                    next_item["configureEnabled"] = True
            except ValueError:
                pass
        marked.append(next_item)
    return marked


def get_effective_euid():
    if hasattr(os, "geteuid"):
        return os.geteuid()
    return None


def ensure_network_apply_environment(platform_name=sys.platform, geteuid=get_effective_euid):
    if not str(platform_name).startswith("linux"):
        raise RuntimeError("网络配置应用仅支持 Linux netplan 环境")
    effective_uid = geteuid()
    if effective_uid not in (0, None):
        raise PermissionError("请以 root 权限启动程序，例如 sudo ./tcp_debug；程序内部不会调用 sudo")


def apply_network_config(entries, runner=run_command, netplan_file=NETPLAN_FILE, platform_name=sys.platform, geteuid=get_effective_euid, client_ip=None, current_interfaces=None):
    ensure_network_apply_environment(platform_name=platform_name, geteuid=geteuid)
    if current_interfaces is not None:
        validate_no_active_web_interface_change(entries, current_interfaces, client_ip)
    yaml_text = generate_netplan_yaml(entries)
    netplan_dir = os.path.dirname(netplan_file)
    os.makedirs(netplan_dir, exist_ok=True)
    if os.path.exists(netplan_file):
        backup_file = f"{netplan_file}.bak"
        shutil.copy2(netplan_file, backup_file)
    with open(netplan_file, "w", encoding="utf-8") as f:
        f.write(yaml_text)
    try:
        os.chmod(netplan_file, 0o600)
    except OSError:
        pass

    repaired_files = backup_networkmanager_generated_netplan_files(netplan_dir, skip_file=netplan_file)
    repaired_files.extend(backup_invalid_netplan_files(netplan_dir, skip_file=netplan_file))
    outputs = []
    for command in [
        ["netplan", "generate"],
        ["netplan", "apply"],
        ["systemctl", "restart", "NetworkManager"],
    ]:
        result = runner(command, timeout=60)
        outputs.append({"command": " ".join(command), **result})
        if result["returncode"] != 0:
            error = (result.get("stderr") or result.get("stdout") or f"命令执行失败: {' '.join(command)}").strip()
            return {"ok": False, "error": error, "yaml": yaml_text, "outputs": outputs, "repairedFiles": repaired_files}
    return {"ok": True, "yaml": yaml_text, "outputs": outputs, "repairedFiles": repaired_files}


def choose_directory_path(title="选择导出目录"):
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return ""

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    try:
        return filedialog.askdirectory(parent=root, title=title) or ""
    finally:
        root.destroy()


def get_safe_static_path(base_dir, relative_path):
    abs_base = os.path.abspath(base_dir)
    file_path = os.path.abspath(os.path.join(base_dir, relative_path))
    if file_path != abs_base and not file_path.startswith(abs_base + os.sep):
        return None
    return file_path


def build_http_response(request_text, client_ip=None):
    request_line = request_text.splitlines()[0] if request_text.splitlines() else ""
    parts = request_line.split()
    if len(parts) < 2 or parts[0] not in ("GET", "POST"):
        return None

    method = parts[0]
    parsed_target = urlparse(parts[1])
    raw_path = unquote(parsed_target.path)
    query = parse_qs(parsed_target.query)
    dist_index_path = os.path.join(DIST_DIR, "index.html")

    if method == "GET" and raw_path == "/api/choose-directory":
        title = query.get("title", ["选择导出目录"])[0]
        try:
            return build_json_response({"path": choose_directory_path(title)})
        except Exception as e:
            return build_json_response({"path": "", "error": str(e)}, "500 Internal Server Error")

    if method == "GET" and raw_path == "/api/network/interfaces":
        try:
            return build_json_response({"interfaces": mark_active_web_interface(list_network_interfaces(), client_ip)})
        except Exception as e:
            return build_json_response({"interfaces": [], "error": str(e)}, "500 Internal Server Error")

    if method == "POST" and raw_path == "/api/network/preview":
        try:
            payload = parse_http_json_body(request_text)
            return build_json_response({"yaml": generate_netplan_yaml(payload.get("interfaces") or [])})
        except Exception as e:
            return build_json_response({"error": str(e)}, "400 Bad Request")

    if method == "POST" and raw_path == "/api/network/apply":
        try:
            payload = parse_http_json_body(request_text)
            result = apply_network_config(
                payload.get("interfaces") or [],
                client_ip=client_ip,
                current_interfaces=list_network_interfaces(),
            )
            return build_json_response(result)
        except Exception as e:
            return build_json_response({"ok": False, "error": str(e)}, "400 Bad Request")

    if method == "GET" and raw_path.startswith("/assets/") and os.path.isdir(DIST_DIR):
        relative_path = raw_path.lstrip("/")
        file_path = get_safe_static_path(DIST_DIR, relative_path)
        if not file_path:
            return "HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n<html><body>forbidden</body></html>"
        if not os.path.exists(file_path):
            return "HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n<html><body>not found</body></html>"
        content_type = CONTENT_TYPES.get(os.path.splitext(file_path)[1], "application/octet-stream")
        return read_static_file(file_path, content_type)

    if method != "GET":
        return "HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n<html><body>not found</body></html>"

    if raw_path == "/":
        if os.path.exists(dist_index_path):
            return read_static_file(dist_index_path, CONTENT_TYPES[".html"])
        return "HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n<html><body>frontend dist not found, run npm run build</body></html>"
    elif raw_path.startswith("/json/") and raw_path.endswith(".json"):
        relative_path = raw_path.lstrip("/")
        content_type = CONTENT_TYPES[".json"]
    else:
        return "HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n<html><body>not found</body></html>"

    file_path = get_safe_static_path(BASE_DIR, relative_path)
    if not file_path:
        return "HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n<html><body>forbidden</body></html>"

    if not os.path.exists(file_path):
        return "HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n<html><body>not found</body></html>"

    return read_static_file(file_path, content_type)


async def http_handler(reader, writer):
    """极简 HTTP 静态文件服务器"""
    request = await reader.read(4096)
    request_text = request.decode('utf-8', errors='ignore')
    peer = writer.get_extra_info("peername")
    client_ip = peer[0] if peer else None

    response = build_http_response(request_text, client_ip=client_ip)
    if response is None:
        writer.close()
        await writer.wait_closed()
        return

    writer.write(response.encode('utf-8'))
    await writer.drain()
    writer.close()
    await writer.wait_closed()


class TcpClientThread(threading.Thread):
    """独立线程管理 TCP 连接，并通过 queue 与 WebSocket 协程通信"""
    def __init__(self, ip, port, recv_queue):
        super().__init__(daemon=True)
        self.ip = ip
        self.port = port
        self.recv_queue = recv_queue      # asyncio.Queue
        self.sock = None
        self.running = False
        self.loop = None

    def notify(self, payload):
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self.recv_queue.put(json.dumps(payload, ensure_ascii=False)),
                self.loop
            )

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(3)
            self.sock.connect((self.ip, self.port))
            self.sock.settimeout(None)
            self.running = True
            
            # 通知前端连接成功
            self.notify({"_type": "system", "msg": f"连接成功 {self.ip}:{self.port}"})
            
            recv_buffer = b""
            while self.running:
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        break
                    recv_buffer += chunk
                    if len(recv_buffer) > MAX_RECV_BUFFER:
                        self.notify({"_type": "system", "msg": f"接收缓冲区超过{MAX_RECV_BUFFER}字节，已丢弃未分包数据"})
                        recv_buffer = b""
                        continue
                    
                    while b"\n" in recv_buffer:
                        msg_data, recv_buffer = recv_buffer.split(b"\n", 1)
                        if msg_data.strip():
                            try:
                                msg = json.loads(msg_data.decode("utf-8"))
                                try:
                                    exported_path = export_mapping_file_if_present(msg)
                                    if exported_path:
                                        self.notify({"_type": "system", "msg": f"映射文件已导出: {exported_path}"})
                                except Exception as export_error:
                                    self.notify({"_type": "system", "msg": f"映射文件导出失败: {str(export_error)}"})
                                # 判断日志级别颜色
                                tag = None
                                if msg.get("eventType") == 1 and "params" in msg:
                                    level = msg["params"].get("eventLevel", 0)
                                    if level == 1: tag = "ERROR"
                                    elif level == 2: tag = "WARNING"
                                    elif level == 3: tag = "INFO"
                                    elif level == 4: tag = "TRACE"
                                    elif level == 5: tag = "VERBOSE"
                                
                                payload = {
                                    "_type": "json",
                                    "data": msg,
                                    "tag": tag,
                                    "raw": msg_data.decode("utf-8", errors="ignore")
                                }
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                payload = {
                                    "_type": "raw",
                                    "raw": msg_data.decode("utf-8", errors="ignore")
                                }
                            
                            self.notify(payload)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.notify({"_type": "system", "msg": f"接收异常: {str(e)}"})
                    break
        except Exception as e:
            self.notify({"_type": "system", "msg": f"连接失败: {str(e)}"})
        finally:
            self.running = False
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                except OSError:
                    pass
            self.notify({"_type": "system", "msg": "服务器断开连接"})

    def send(self, data_bytes):
        if self.sock and self.running:
            try:
                self.sock.sendall(data_bytes)
                return True
            except Exception as e:
                self.notify({"_type": "system", "msg": f"发送失败: {str(e)}"})
                return False
        return False

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except OSError:
                pass


async def ws_handler(websocket):
    """WebSocket 处理器：每个浏览器客户端一个实例"""
    tcp_thread = None
    recv_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    forwarder_task = asyncio.create_task(recv_forwarder(websocket, recv_queue))
    
    try:
        async for message in websocket:
            try:
                cmd = json.loads(message)
                action = cmd.get("action")
                
                if action == "connect":
                    if tcp_thread and tcp_thread.running:
                        await websocket.send(json.dumps({"_type": "system", "msg": "已连接，请勿重复操作"}))
                        continue
                    
                    try:
                        ip, port = validate_connect_target(
                            cmd.get("ip", "10.66.71.240"),
                            cmd.get("port", 9000)
                        )
                    except ValueError as e:
                        await websocket.send(json.dumps({"_type": "system", "msg": str(e)}, ensure_ascii=False))
                        continue
                    
                    tcp_thread = TcpClientThread(ip, port, recv_queue)
                    tcp_thread.loop = loop
                    tcp_thread.start()
                
                elif action == "disconnect":
                    if tcp_thread:
                        tcp_thread.stop()
                        tcp_thread = None
                        await websocket.send(json.dumps({"_type": "system", "msg": "已请求断开连接"}, ensure_ascii=False))
                    else:
                        await websocket.send(json.dumps({"_type": "system", "msg": "未连接服务器"}, ensure_ascii=False))
                
                elif action == "send":
                    if not tcp_thread or not tcp_thread.running:
                        await websocket.send(json.dumps({"_type": "system", "msg": "请先连接服务器"}, ensure_ascii=False))
                        continue
                    
                    json_text = cmd.get("data", "")
                    if not json_text.strip():
                        await websocket.send(json.dumps({"_type": "system", "msg": "编辑框为空，请输入JSON"}, ensure_ascii=False))
                        continue
                    
                    try:
                        payload = build_outgoing_payload(json_text)
                        success = tcp_thread.send(payload)
                        if success:
                            await websocket.send(json.dumps({"_type": "system", "msg": "发送自定义JSON成功"}, ensure_ascii=False))
                    except json.JSONDecodeError:
                        await websocket.send(json.dumps({"_type": "system", "msg": "JSON格式错误，请检查"}, ensure_ascii=False))
            
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"_type": "system", "msg": "指令格式错误"}, ensure_ascii=False))
        
        # 客户端断开时清理 TCP
        if tcp_thread:
            tcp_thread.stop()
            
    except websockets.exceptions.ConnectionClosed:
        if tcp_thread:
            tcp_thread.stop()
    finally:
        if tcp_thread:
            tcp_thread.stop()
        forwarder_task.cancel()
        try:
            await forwarder_task
        except asyncio.CancelledError:
            pass


async def recv_forwarder(websocket, recv_queue):
    """独立协程：将 TCP 接收队列的数据转发到 WebSocket"""
    while True:
        msg = await recv_queue.get()
        await websocket.send(msg)


async def main():
    # 启动 HTTP 静态服务器
    http_server = await asyncio.start_server(http_handler, HOST, HTTP_PORT)
    print(f"HTTP 服务已启动: http://{HOST}:{HTTP_PORT}")
    if HOST == "0.0.0.0":
        print(f"局域网访问地址: http://{get_lan_ip()}:{HTTP_PORT}")
    
    # 启动 WebSocket 服务器
    ws_server = await websockets.serve(ws_handler, HOST, WS_PORT, max_size=WS_MAX_SIZE)
    print(f"WebSocket 服务已启动: ws://{HOST}:{WS_PORT}")
    
    await asyncio.gather(
        http_server.serve_forever(),
        ws_server.wait_closed()
    )


if __name__ == "__main__":
    asyncio.run(main())
