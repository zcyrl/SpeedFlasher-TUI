#!/usr/bin/env bash
# ==============================================================================
# SpeedFlasher TUI - Linux System Installer & Global CLI Setup
# By Mehraann (patched UI by Softbrick)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "========================================================================"
echo "       SpeedFlasher TUI - Linux Installer"
echo "       By Mehraann (patched UI by Softbrick)"
echo "========================================================================"

echo "[*] Checking Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "[!] python3 is required. Please install python3 with your package manager."
    exit 1
fi

echo "[*] Setting file execution permissions..."
chmod +x "$SCRIPT_DIR"/bin/linux/* 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/bin/device/* 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true

echo "[*] Creating global 'flashable' command in $BIN_DIR..."
mkdir -p "$BIN_DIR"
cat << EOF > "$BIN_DIR/flashable"
#!/usr/bin/env bash
SPEEDFLASHER_DIR="$SCRIPT_DIR"
cd "\$SPEEDFLASHER_DIR"
exec python3 main.py "\$@"
EOF
chmod +x "$BIN_DIR/flashable"

# Create Desktop entry
if [ -d "$HOME/.local/share" ]; then
    mkdir -p "$DESKTOP_DIR"
    cat << EOF > "$DESKTOP_DIR/speedflasher-tui.desktop"
[Desktop Entry]
Name=SpeedFlasher TUI
Comment=Universal Android Flashable Package Maker by Mehraann (patched UI by Softbrick)
Exec=$BIN_DIR/flashable
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=Utility;Development;
EOF
    chmod +x "$DESKTOP_DIR/speedflasher-tui.desktop" 2>/dev/null || true
    echo "[*] Created desktop menu entry: SpeedFlasher TUI"
fi

echo "========================================================================"
echo "[✓] Installation successful!"
echo "You can now run SpeedFlasher TUI from ANY terminal by typing:"
echo ""
echo "    flashable"
echo ""
echo "Launching SpeedFlasher TUI now..."
echo "========================================================================"
sleep 1
exec "$BIN_DIR/flashable" "$@"
