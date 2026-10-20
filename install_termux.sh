#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# SpeedFlasher TUI - One-Step Termux Installer & Global Shortcut Creator
# By Mehraann (patched UI by Softbrick)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"

echo "========================================================================"
echo "      SpeedFlasher TUI (Antumbra Edition) - Termux Installer"
echo "      By Mehraann (patched UI by Softbrick)"
echo "========================================================================"

echo "[*] Requesting Android storage permission..."
if [ ! -d "$HOME/storage" ]; then
    termux-setup-storage || true
fi

echo "[*] Updating package index and installing dependencies..."
pkg update -y || true
pkg install -y python zstd android-tools || true

echo "[*] Making internal binaries executable..."
chmod +x "$SCRIPT_DIR"/bin/device/* 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true

echo "[*] Creating global 'flashable' command in $PREFIX/bin..."
mkdir -p "$PREFIX/bin"
cat << 'EOF' > "$PREFIX/bin/flashable"
#!/data/data/com.termux/files/usr/bin/bash
SPEEDFLASHER_DIR="__INSTALL_DIR__"
cd "$SPEEDFLASHER_DIR"
exec python main.py "$@"
EOF

sed -i "s|__INSTALL_DIR__|$SCRIPT_DIR|g" "$PREFIX/bin/flashable"
chmod +x "$PREFIX/bin/flashable"

echo "========================================================================"
echo "[✓] Installation complete!"
echo "You can now run SpeedFlasher from ANY directory in Termux by typing:"
echo ""
echo "    flashable"
echo ""
echo "Launching SpeedFlasher TUI now..."
echo "========================================================================"
sleep 1
exec "$PREFIX/bin/flashable" "$@"
