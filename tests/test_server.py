import asyncio
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import server


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send(self, message):
        self.sent.append(message)


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_recv_forwarder_sends_messages_from_queue_to_websocket(self):
        websocket = FakeWebSocket()
        queue = asyncio.Queue()
        await queue.put(json.dumps({"_type": "system", "msg": "连接成功 127.0.0.1:9000"}))

        task = asyncio.create_task(server.recv_forwarder(websocket, queue))
        await asyncio.sleep(0.05)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertEqual(
            websocket.sent,
            [json.dumps({"_type": "system", "msg": "连接成功 127.0.0.1:9000"})],
        )

    async def test_validate_connect_target_rejects_invalid_port(self):
        with self.assertRaisesRegex(ValueError, "端口必须是 1-65535"):
            server.validate_connect_target("127.0.0.1", "abc")

    async def test_validate_connect_target_accepts_valid_target(self):
        self.assertEqual(
            server.validate_connect_target("127.0.0.1", "9000"),
            ("127.0.0.1", 9000),
        )

    async def test_build_outgoing_payload_compacts_pretty_json_to_one_line(self):
        pretty_json = '{\n  "moduleType": 8,\n  "params": {\n    "operationCommand": 2\n  }\n}'

        payload = server.build_outgoing_payload(pretty_json)

        self.assertEqual(
            payload,
            b'{"moduleType":8,"params":{"operationCommand":2}}\n',
        )

    async def test_build_outgoing_payload_accepts_large_model_json(self):
        model_json = json.dumps({
            "moduleType": 8,
            "eventType": 3,
            "params": {
                "operationCommand": 6,
                "paramType": 21,
                "data": {
                    "detectModelList": [
                        {
                            "modelBaseParam": {
                                "modelName": "large.engine",
                                "modelBase64Data": "A" * (2 * 1024 * 1024),
                            }
                        }
                    ]
                },
            },
        })

        payload = server.build_outgoing_payload(model_json)

        self.assertGreater(len(payload), 2 * 1024 * 1024)
        self.assertTrue(payload.endswith(b"\n"))

    async def test_websocket_large_message_limit_allows_model_payloads(self):
        self.assertIsNone(server.WS_MAX_SIZE)

    async def test_default_host_listens_on_all_interfaces_for_lan_access(self):
        self.assertEqual(server.HOST, "0.0.0.0")

    async def test_build_http_response_serves_json_files(self):
        os.makedirs(os.path.join(server.BASE_DIR, "json"), exist_ok=True)
        target = os.path.join(server.BASE_DIR, "json", "unitTestCommand.json")
        with open(target, "w", encoding="utf-8") as f:
            json.dump({"eventType": 4}, f)

        try:
            response = server.build_http_response("GET /json/unitTestCommand.json HTTP/1.1\r\n\r\n")
        finally:
            os.remove(target)

        self.assertIn("HTTP/1.1 200 OK", response)
        self.assertIn("Content-Type: application/json; charset=utf-8", response)
        self.assertIn('"eventType": 4', response)

    async def test_build_http_response_serves_vite_dist_assets(self):
        dist_assets_dir = os.path.join(server.BASE_DIR, "dist", "assets")
        os.makedirs(dist_assets_dir, exist_ok=True)
        target = os.path.join(dist_assets_dir, "app-test.js")
        with open(target, "w", encoding="utf-8") as f:
            f.write('console.log("vite asset");\n')

        try:
            response = server.build_http_response("GET /assets/app-test.js HTTP/1.1\r\n\r\n")
        finally:
            os.remove(target)

        self.assertIn("HTTP/1.1 200 OK", response)
        self.assertIn("Content-Type: application/javascript; charset=utf-8", response)
        self.assertIn("vite asset", response)

    async def test_build_http_response_serves_vite_css_with_text_css_type(self):
        dist_assets_dir = os.path.join(server.BASE_DIR, "dist", "assets")
        os.makedirs(dist_assets_dir, exist_ok=True)
        target = os.path.join(dist_assets_dir, "app-test.css")
        with open(target, "w", encoding="utf-8") as f:
            f.write('body { color: red; }\n')

        try:
            response = server.build_http_response("GET /assets/app-test.css HTTP/1.1\r\n\r\n")
        finally:
            os.remove(target)

        self.assertIn("HTTP/1.1 200 OK", response)
        self.assertIn("Content-Type: text/css; charset=utf-8", response)
        self.assertIn("body { color: red; }", response)

    async def test_build_http_response_serves_event_definitions_json(self):
        response = server.build_http_response("GET /json/eventDefinitions.json HTTP/1.1\r\n\r\n")

        self.assertIn("HTTP/1.1 200 OK", response)
        self.assertIn("Content-Type: application/json; charset=utf-8", response)
        self.assertIn('"name": "EventType"', response)

    async def test_build_http_response_returns_directory_picker_path(self):
        with mock.patch.object(server, "choose_directory_path", return_value=r"D:\exports") as picker:
            response = server.build_http_response("GET /api/choose-directory?title=%E9%80%89%E6%8B%A9%E5%AF%BC%E5%87%BA%E7%9B%AE%E5%BD%95 HTTP/1.1\r\n\r\n")

        picker.assert_called_once_with("选择导出目录")
        self.assertIn("HTTP/1.1 200 OK", response)
        self.assertIn("Content-Type: application/json; charset=utf-8", response)
        self.assertIn('"path": "D:\\\\exports"', response)

    async def test_build_http_response_returns_empty_path_when_directory_picker_cancelled(self):
        with mock.patch.object(server, "choose_directory_path", return_value=""):
            response = server.build_http_response("GET /api/choose-directory HTTP/1.1\r\n\r\n")

        self.assertIn("HTTP/1.1 200 OK", response)
        self.assertIn('"path": ""', response)

    async def test_parse_network_interfaces_from_ip_addr_json(self):
        ip_json = [
            {
                "ifname": "enp1s0",
                "address": "A0:36:9F:33:75:F3",
                "operstate": "UP",
                "addr_info": [
                    {"family": "inet", "local": "192.168.3.188", "prefixlen": 24},
                    {"family": "inet6", "local": "fe80::1", "prefixlen": 64},
                ],
            },
            {
                "ifname": "enp2s0",
                "address": "a0:36:9f:0c:5c:3f",
                "operstate": "DOWN",
                "addr_info": [],
            },
            {
                "ifname": "enp3s0",
                "address": "a0:36:9f:0c:5c:40",
                "operstate": "UP",
                "addr_info": [],
            },
        ]

        interfaces = server.parse_network_interfaces(ip_json, carrier_reader=lambda name: name in {"enp1s0", "enp3s0"})

        self.assertEqual(interfaces[0]["name"], "enp1s0")
        self.assertEqual(interfaces[0]["macAddress"], "A0:36:9F:33:75:F3")
        self.assertEqual(interfaces[0]["ipv4Address"], "192.168.3.188/24")
        self.assertTrue(interfaces[0]["linkDetected"])
        self.assertTrue(interfaces[0]["configureEnabled"])
        self.assertEqual(interfaces[1]["ipv4Address"], "")
        self.assertFalse(interfaces[1]["linkDetected"])
        self.assertFalse(interfaces[1]["configureEnabled"])
        self.assertTrue(interfaces[2]["linkDetected"])
        self.assertEqual(interfaces[2]["ipv4Address"], "")
        self.assertFalse(interfaces[2]["configureEnabled"])

    async def test_generate_netplan_yaml_uses_mac_bound_static_ip_config(self):
        yaml_text = server.generate_netplan_yaml([
            {
                "macAddress": "A0:36:9F:33:75:F3",
                "targetName": "enp88",
                "ipv4Address": "192.168.3.188/24",
            },
            {
                "macAddress": "a0:36:9f:0c:5c:3f",
                "targetName": "enpPanGu0",
                "ipv4Address": "192.168.2.100/24",
            },
        ])

        self.assertIn("renderer: NetworkManager", yaml_text)
        self.assertIn("enp88:", yaml_text)
        self.assertIn("macaddress: A0:36:9F:33:75:F3", yaml_text)
        self.assertIn("set-name: enp88", yaml_text)
        self.assertIn("addresses: [192.168.3.188/24]", yaml_text)
        self.assertIn("dhcp4: no", yaml_text)

    async def test_generate_netplan_yaml_skips_disabled_interfaces_without_validation(self):
        yaml_text = server.generate_netplan_yaml([
            {
                "enabled": True,
                "macAddress": "A0:36:9F:33:75:F3",
                "targetName": "enp88",
                "ipv4Address": "192.168.3.188/24",
            },
            {
                "enabled": False,
                "macAddress": "not-a-mac",
                "targetName": "",
                "ipv4Address": "",
            },
        ])

        self.assertIn("enp88:", yaml_text)
        self.assertNotIn("not-a-mac", yaml_text)

    async def test_generate_netplan_yaml_rejects_invalid_ip(self):
        with self.assertRaisesRegex(ValueError, "IPv4地址格式错误"):
            server.generate_netplan_yaml([
                {"enabled": True, "macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "192.168.999.1/24"}
            ])

    async def test_generate_netplan_yaml_defaults_plain_ipv4_to_24_prefix(self):
        yaml_text = server.generate_netplan_yaml([
            {"enabled": True, "macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "10.66.71.101"}
        ])

        self.assertIn("addresses: [10.66.71.101/24]", yaml_text)

    async def test_generate_netplan_yaml_rejects_invalid_static_prefix_zero(self):
        with self.assertRaisesRegex(ValueError, "IPv4掩码长度必须是 1-30"):
            server.generate_netplan_yaml([
                {"enabled": True, "macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "10.66.71.101/0"}
            ])

    async def test_apply_network_config_writes_yaml_and_runs_netplan_commands(self):
        commands = []

        def fake_runner(command, timeout=30):
            commands.append(command)
            return {"returncode": 0, "stdout": "ok", "stderr": ""}

        with tempfile.TemporaryDirectory() as temp_dir:
            netplan_file = os.path.join(temp_dir, "01-network-manager-all.yaml")
            result = server.apply_network_config(
                [{"macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "192.168.3.188/24"}],
                runner=fake_runner,
                netplan_file=netplan_file,
                platform_name="linux",
                geteuid=lambda: 0,
            )

            with open(netplan_file, "r", encoding="utf-8") as f:
                written = f.read()

        self.assertTrue(result["ok"])
        self.assertIn("enp88:", written)
        self.assertEqual(
            commands,
            [
                ["netplan", "generate"],
                ["netplan", "apply"],
                ["systemctl", "restart", "NetworkManager"],
            ],
        )

    async def test_apply_network_config_reports_command_failure_without_http_500(self):
        def fake_apply_failure(command, timeout=30):
            return {
                "returncode": 1 if command == ["netplan", "apply"] else 0,
                "stdout": "",
                "stderr": "netplan apply failed",
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            netplan_file = os.path.join(temp_dir, "01-network-manager-all.yaml")
            result = server.apply_network_config(
                [{"macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "192.168.3.188/24"}],
                runner=fake_apply_failure,
                netplan_file=netplan_file,
                platform_name="linux",
                geteuid=lambda: 0,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "netplan apply failed")

    async def test_apply_network_config_backs_up_existing_invalid_netplan_yaml(self):
        commands = []

        def fake_runner(command, timeout=30):
            commands.append(command)
            return {"returncode": 0, "stdout": "ok", "stderr": ""}

        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_file = os.path.join(temp_dir, "50-bad.yaml")
            with open(invalid_file, "w", encoding="utf-8") as f:
                f.write("network:\n  ethernets:\n    bad0:\n      addresses: [10.66.71.101/0]\n")

            netplan_file = os.path.join(temp_dir, "01-network-manager-all.yaml")
            result = server.apply_network_config(
                [{"macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "10.66.71.101"}],
                runner=fake_runner,
                netplan_file=netplan_file,
                platform_name="linux",
                geteuid=lambda: 0,
            )

            backup_file = invalid_file + ".invalid.bak"
            self.assertTrue(result["ok"])
            self.assertFalse(os.path.exists(invalid_file))
            self.assertTrue(os.path.exists(backup_file))
            self.assertEqual(result["repairedFiles"], [backup_file])

    async def test_apply_network_config_backs_up_networkmanager_generated_yaml_files(self):
        def fake_runner(command, timeout=30):
            return {"returncode": 0, "stdout": "ok", "stderr": ""}

        with tempfile.TemporaryDirectory() as temp_dir:
            nm_file = os.path.join(temp_dir, "90-NM-cc271960.yaml")
            with open(nm_file, "w", encoding="utf-8") as f:
                f.write("network:\n  version: 2\n")

            netplan_file = os.path.join(temp_dir, "01-network-manager-all.yaml")
            result = server.apply_network_config(
                [{"macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "10.66.71.101"}],
                runner=fake_runner,
                netplan_file=netplan_file,
                platform_name="linux",
                geteuid=lambda: 0,
            )

            backup_file = nm_file + ".tcp_debug.bak"
            self.assertTrue(result["ok"])
            self.assertFalse(os.path.exists(nm_file))
            self.assertTrue(os.path.exists(backup_file))
            self.assertIn(backup_file, result["repairedFiles"])

    async def test_active_web_interface_change_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "当前Web连接正在使用网口"):
            server.validate_no_active_web_interface_change(
                [{"macAddress": "A0:36:9F:33:75:F3", "targetName": "renamed0", "ipv4Address": "10.66.71.101/24"}],
                [{"name": "enp88", "macAddress": "A0:36:9F:33:75:F3", "ipv4Address": "10.66.71.100/24"}],
                "10.66.71.20",
            )

    async def test_active_web_interface_same_config_is_allowed(self):
        server.validate_no_active_web_interface_change(
            [{"macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "10.66.71.100/24"}],
            [{"name": "enp88", "macAddress": "A0:36:9F:33:75:F3", "ipv4Address": "10.66.71.100/24"}],
            "10.66.71.20",
        )

    async def test_mark_active_web_interface_forces_configuration_enabled(self):
        interfaces = server.mark_active_web_interface([
            {"name": "enp88", "macAddress": "A0:36:9F:33:75:F3", "ipv4Address": "10.66.71.101/24", "configureEnabled": False},
            {"name": "enp2s0", "macAddress": "A0:36:9F:0C:5C:3F", "ipv4Address": "192.168.2.100/24", "configureEnabled": True},
        ], "10.66.71.205")

        self.assertTrue(interfaces[0]["isActiveWebInterface"])
        self.assertTrue(interfaces[0]["configureEnabled"])
        self.assertFalse(interfaces[1]["isActiveWebInterface"])

    async def test_apply_network_config_rejects_non_linux_platform(self):
        with self.assertRaisesRegex(RuntimeError, "仅支持 Linux"):
            server.apply_network_config(
                [{"enabled": True, "macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "192.168.3.188/24"}],
                platform_name="win32",
            )

    async def test_apply_network_config_requires_root_without_sudo_prompt(self):
        with self.assertRaisesRegex(PermissionError, "请以 root 权限启动"):
            server.apply_network_config(
                [{"enabled": True, "macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "192.168.3.188/24"}],
                platform_name="linux",
                geteuid=lambda: 1000,
            )

    async def test_build_http_response_serves_network_interfaces_api(self):
        with mock.patch.object(server, "list_network_interfaces", return_value=[{"name": "enp1s0", "ipv4Address": "192.168.3.188/24"}]):
            response = server.build_http_response("GET /api/network/interfaces HTTP/1.1\r\n\r\n")

        self.assertIn("HTTP/1.1 200 OK", response)
        self.assertIn('"name": "enp1s0"', response)
        self.assertIn('"ipv4Address": "192.168.3.188/24"', response)
        self.assertIn('"isActiveWebInterface": false', response)

    async def test_build_http_response_previews_network_config_from_post_body(self):
        body = json.dumps({
            "interfaces": [
                {"macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "192.168.3.188/24"}
            ]
        })
        response = server.build_http_response(f"POST /api/network/preview HTTP/1.1\r\nContent-Length: {len(body)}\r\n\r\n{body}")

        self.assertIn("HTTP/1.1 200 OK", response)
        self.assertIn('"yaml"', response)
        self.assertIn("enp88", response)

    async def test_build_http_response_returns_apply_failure_as_json_200(self):
        body = json.dumps({
            "interfaces": [
                {"macAddress": "A0:36:9F:33:75:F3", "targetName": "enp88", "ipv4Address": "192.168.3.188/24"}
            ]
        })
        with mock.patch.object(server, "list_network_interfaces", return_value=[]), \
             mock.patch.object(server, "apply_network_config", return_value={"ok": False, "error": "netplan apply failed", "outputs": []}):
            response = server.build_http_response(f"POST /api/network/apply HTTP/1.1\r\nContent-Length: {len(body)}\r\n\r\n{body}")

        self.assertIn("HTTP/1.1 200 OK", response)
        self.assertIn('"ok": false', response)
        self.assertIn('"error": "netplan apply failed"', response)

    async def test_update_set_params_template_replaces_only_params_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = os.path.join(temp_dir, "setParams.json")
            original = {
                "moduleType": 8,
                "eventType": 5,
                "params": {
                    "operationCommand": 6,
                    "paramType": 1,
                    "engineName": "XrayEngine",
                    "data": {"old": True},
                },
            }
            received_data = {"actual": {"threshold": 12}, "enabled": 1}
            with open(target, "w", encoding="utf-8") as f:
                json.dump(original, f)

            updated = server.update_set_params_template(received_data, template_path=target)

            with open(target, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(updated["params"]["data"], received_data)
            self.assertEqual(saved["params"]["data"], received_data)
            self.assertEqual(saved["moduleType"], 8)
            self.assertEqual(saved["eventType"], 5)
            self.assertEqual(saved["params"]["operationCommand"], 6)
            self.assertEqual(saved["params"]["paramType"], 1)
            self.assertEqual(saved["params"]["engineName"], "XrayEngine")

    async def test_build_http_response_updates_set_params_template(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = os.path.join(temp_dir, "setParams.json")
            with open(target, "w", encoding="utf-8") as f:
                json.dump({
                    "moduleType": 8,
                    "eventType": 5,
                    "params": {
                        "operationCommand": 6,
                        "paramType": 1,
                        "engineName": "XrayEngine",
                        "data": {"old": True},
                    },
                }, f)
            body = json.dumps({"data": {"newParam": 42}})

            with mock.patch.object(server, "SET_PARAMS_TEMPLATE_FILE", target):
                response = server.build_http_response(
                    f"POST /api/json/update-set-params HTTP/1.1\r\nContent-Length: {len(body)}\r\n\r\n{body}"
                )

            with open(target, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertIn("HTTP/1.1 200 OK", response)
            self.assertIn('"ok": true', response)
            self.assertEqual(saved["params"]["data"], {"newParam": 42})

    async def test_export_mapping_file_decodes_base64_to_output_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            message = {
                "params": {
                    "data": {
                        "fileName": "map.txt",
                        "fileSize": 4,
                        "base64Data": "VEVTVA==",
                        "outPutPath": temp_dir,
                    }
                }
            }

            exported_path = server.export_mapping_file_if_present(message)

            self.assertEqual(exported_path, os.path.join(temp_dir, "map.txt"))
            with open(exported_path, "rb") as f:
                self.assertEqual(f.read(), b"TEST")


if __name__ == "__main__":
    unittest.main()
