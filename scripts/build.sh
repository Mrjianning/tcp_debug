#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"
BUILD_ROOT="$PROJECT_ROOT/build/linux"
RELEASE_DIR="$PROJECT_ROOT/build/release/tcp_debug-linux"
ARTIFACTS_DIR="$PROJECT_ROOT/build/artifacts/tcp_debug-linux"
CONDA_ENV_PREFIX="$PROJECT_ROOT/build/conda/tcp_debug-build"

echo "[1/6] Checking build environment..."
if [ -n "${CONDA_PREFIX:-}" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
    PYTHON_CMD="$CONDA_PREFIX/bin/python"
    echo "Using active conda environment: $CONDA_PREFIX"
elif command -v conda >/dev/null 2>&1; then
    if [ ! -x "$CONDA_ENV_PREFIX/bin/python" ]; then
        echo "Conda detected. Creating local build environment: $CONDA_ENV_PREFIX"
        conda create -y -p "$CONDA_ENV_PREFIX" python=3.10
    else
        echo "Conda detected. Reusing local build environment: $CONDA_ENV_PREFIX"
    fi
    PYTHON_CMD="$CONDA_ENV_PREFIX/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "Python not found. Please install Python 3 or activate a conda environment first." >&2
    exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found. Please install Node.js first." >&2
    exit 1
fi

echo "Python command: $PYTHON_CMD"

echo "[2/6] Installing Python dependencies..."
"$PYTHON_CMD" -m pip install --upgrade pip || "$PYTHON_CMD" -m pip install --upgrade pip --break-system-packages
"$PYTHON_CMD" -m pip install -r requirements.txt pyinstaller || "$PYTHON_CMD" -m pip install -r requirements.txt pyinstaller --break-system-packages

echo "[3/6] Building Vue frontend..."
npm install
npm run build

echo "[4/6] Building tcp_debug..."
if command -v pgrep >/dev/null 2>&1 && pgrep -x tcp_debug >/dev/null 2>&1; then
    echo "tcp_debug is running. Please close it before building." >&2
    exit 1
fi

"$PYTHON_CMD" -m PyInstaller \
    --clean \
    --noconfirm \
    --onefile \
    --name tcp_debug \
    --icon "$PROJECT_ROOT/assets/icon.ico" \
    --distpath "$BUILD_ROOT" \
    --workpath "$BUILD_ROOT/temp" \
    --specpath "$BUILD_ROOT" \
    --add-data "$PROJECT_ROOT/src/dist:dist" \
    --add-data "$PROJECT_ROOT/src/json:json" \
    --add-data "$PROJECT_ROOT/assets/icon.ico:assets" \
    "$PROJECT_ROOT/src/server.py"

echo "[5/6] Creating portable release directory..."
rm -rf "$RELEASE_DIR"
rm -rf "$ARTIFACTS_DIR"
mkdir -p "$RELEASE_DIR" "$ARTIFACTS_DIR/resources" "$ARTIFACTS_DIR/python-deps"
cp "$BUILD_ROOT/tcp_debug" "$RELEASE_DIR/tcp_debug"
cp "$PROJECT_ROOT/requirements.txt" "$ARTIFACTS_DIR/requirements.txt"
cp "$PROJECT_ROOT/package.json" "$ARTIFACTS_DIR/package.json"
[ -f "$PROJECT_ROOT/package-lock.json" ] && cp "$PROJECT_ROOT/package-lock.json" "$ARTIFACTS_DIR/package-lock.json"
cp -R "$PROJECT_ROOT/src/json" "$ARTIFACTS_DIR/resources/json"
cp -R "$PROJECT_ROOT/src/dist" "$ARTIFACTS_DIR/resources/dist"
"$PYTHON_CMD" -m pip download -r requirements.txt -d "$ARTIFACTS_DIR/python-deps"
cat > "$RELEASE_DIR/start.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec ./tcp_debug
EOF
cat > "$RELEASE_DIR/start-root.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(id -u)" -ne 0 ]; then
  echo "Network apply requires root. Re-run: sudo ./start-root.sh" >&2
  exit 1
fi
exec ./tcp_debug
EOF
cat > "$RELEASE_DIR/tcp_debug.service" <<'EOF'
[Unit]
Description=tcp_debug sorting service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/tcp_debug
ExecStart=/opt/tcp_debug/tcp_debug
Restart=on-failure
RestartSec=2
User=root

[Install]
WantedBy=multi-user.target
EOF
cat > "$RELEASE_DIR/install-service.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ "$(id -u)" -ne 0 ]; then
  echo "Install service with root privileges: sudo ./install-service.sh" >&2
  exit 1
fi
mkdir -p /opt/tcp_debug
cp tcp_debug start.sh start-root.sh README.txt /opt/tcp_debug/
cp tcp_debug.service /etc/systemd/system/tcp_debug.service
systemctl daemon-reload
systemctl enable tcp_debug.service
echo "Installed. Start with: sudo systemctl start tcp_debug"
EOF
chmod +x "$RELEASE_DIR/start.sh" "$RELEASE_DIR/start-root.sh" "$RELEASE_DIR/install-service.sh" "$RELEASE_DIR/tcp_debug"
cat > "$RELEASE_DIR/README.txt" <<'EOF'
tcp_debug Linux portable release

Start:
  ./start.sh

Network apply:
  To write /etc/netplan and run netplan/systemctl, start with root privileges:
  sudo ./start-root.sh

Install service:
  sudo ./install-service.sh
  sudo systemctl start tcp_debug

HTTP:
  http://127.0.0.1:8080
  http://<server-ip>:8080

Vue frontend is built into the tcp_debug executable. Do not run npm or Vue separately.
Debug materials are in build/artifacts/tcp_debug-linux on the build machine.
EOF

echo "[6/6] Cleaning temporary build files..."
rm -rf "$BUILD_ROOT/temp" "__pycache__"
rm -f "$BUILD_ROOT/tcp_debug.spec"

echo "Build finished."
echo "Output: $RELEASE_DIR"
