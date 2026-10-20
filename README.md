# SpeedFlasher TUI (Antumbra Edition)

```text
 ███████╗██████╗ ███████╗███████╗██████╗ ███████╗██╗      █████╗ ███████╗██╗  ██╗███████╗██████╗ 
 ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝██║     ██╔══██╗██╔════╝██║  ██║██╔════╝██╔══██╗
 ███████╗██████╔╝█████╗  █████╗  ██║  ██║█████╗  ██║     ███████║███████╗███████║█████╗  ██████╔╝
 ╚════██║██╔═══╝ ██╔══╝  ██╔══╝  ██║  ██║██╔══╝  ██║     ██╔══██║╚════██║██╔══██║██╔══╝  ██╔══██╗
 ██████╔╝██║     ███████╗███████╗██████╔╝██║     ███████╗██║  ██║███████║██║  ██║███████╗██║  ██║
 ╚═════╝ ╚═╝     ╚══════╝╚══════╝╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
```

<div align="center">

### Universal Android Flashable Package Maker
**By Mehraann (patched UI by Softbrick)**

*Celestial Antumbra-styled TUI with live animated blinking stars, multi-threaded ZSTD compression, AVB 2.0 flags patcher, and multi-OS Fastboot + Recovery generation.*

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Termux-blue.svg)](#os-installation-and-usage-guides)
[![License](https://img.shields.io/badge/License-GPL%20v3-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20Only-brightgreen.svg)](#features)

</div>

---

## Overview

**SpeedFlasher TUI** converts firmware partition image dumps (`.img` or `.img.zst`) into universal flashable ZIP packages compatible with:
1. **Custom Recoveries**: TWRP, OrangeFox, PBRP, Lineage Recovery (POSIX `update-binary`).
2. **Windows Fastboot**: Native `flash_windows.bat` flasher script.
3. **Linux Fastboot**: Native `flash_linux.sh` flasher script.
4. **Android Termux Fastboot**: Native `flash_termux.sh` flasher script for on-the-go OTG flashing.

Featuring a patched, retro-futuristic **Antumbra-inspired TUI** with:
- ✨ **Twinkling Starfield Animation**: Celestial background stars (`✦`, `✧`, `·`) twinkling smoothly around the UI at 30-60 FPS without flicker.
- 🎨 **Theme Engine**: Penumbra (default dark cosmic lavender), System Dark, Catppuccin Mocha, Rosé Pine, and Gruvbox.
- 🗂️ **Interactive Directory Browser**: Navigate folders directly from terminal to select firmware image directories.
- 🔍 **Partition Inspector**: Auto-classifies Dynamic Super groups (`system`, `vendor`, `product`, `system_dlkm`, `system_ext`, etc.), direct bootchain partitions, and firmware images.
- 🛡️ **AVB 2.0 (vbmeta) Patching**: Real-time flag patching (`skip`, `disable`, `enable`).
- ⚡ **Zero Mandatory External Dependencies**: Runs out-of-the-box on clean Python 3 across Windows, Linux, and Android Termux.

---

## Keyboard Controls

| Key | Action |
| :--- | :--- |
| `↑` / `↓` or `k` / `j` | Navigate menus and form fields |
| `Enter` / `Space` | Select menu action, toggle switch, or edit field |
| `Tab` / `Shift+Tab` | Jump to next / previous form control |
| `Esc` / `b` | Go back / cancel / exit |
| `1` - `9` | Quick jump to numbered menu item |

---

## OS Installation and Usage Guides

### 1. Android Termux Guide (No PC Required)

Run SpeedFlasher directly on your Android phone using Termux!

#### One-Line Quick Install
Open Termux and run:
```bash
pkg update -y && pkg install -y git python zstd android-tools
git clone https://github.com/zcyrl/SpeedFlasher-TUI.git
cd SpeedFlasher-TUI
bash install_termux.sh
```

#### Running SpeedFlasher in Termux
Once installed, you can launch the TUI from **any directory** simply by typing:
```bash
flashable
```
*(Or navigate to the folder and run `python main.py`)*

#### Flashing via OTG in Termux
1. Put the target phone in Fastboot mode.
2. Connect it to your Termux device using a USB-C OTG cable.
3. Extract the generated `Flashable.zip`.
4. Run:
   ```bash
   bash flash_termux.sh
   ```

---

### 2. Windows Guide (Windows 10 / 11)

#### Requirements
- Windows 10 or 11 (64-bit)
- Python 3.8 or newer (If not installed, `setup.bat` will automatically guide you)

#### Quick Setup
1. Clone or download the repository:
   ```cmd
   git clone https://github.com/zcyrl/SpeedFlasher-TUI.git
   cd SpeedFlasher-TUI
   ```
2. Double-click **`install_windows.bat`** (or `start.bat`).
   - Creates a **"SpeedFlasher TUI"** shortcut directly on your Desktop.
   - Automatically bootstraps dependencies if needed.

#### Launching the TUI
- Double-click the Desktop shortcut or **`start.bat`**
- Or run in Command Prompt / Windows Terminal / PowerShell:
  ```cmd
  python main.py
  ```

#### Flashing on Windows
1. Extract the generated ZIP in `output/`.
2. Boot target phone into Fastboot mode.
3. Connect via USB and double-click `flash_windows.bat`.

---

### 3. Linux Guide (Ubuntu, Debian, Arch, Fedora)

#### Quick Install
```bash
git clone https://github.com/zcyrl/SpeedFlasher-TUI.git
cd SpeedFlasher-TUI
bash install.sh
```
`install.sh` sets file permissions, registers a global `flashable` terminal command in `~/.local/bin`, and creates an application desktop entry.

#### Running on Linux
Launch from any terminal with:
```bash
flashable
```
Or:
```bash
python3 main.py
```

---

## Command-Line Arguments & Automation

You can also use SpeedFlasher headlessly in automated CI/CD pipelines or scripts:

```text
usage: main.py [-h] [-i IMGS_PATH] [-d DEVICE] [-c CODENAME] [-v VERSION]
               [-m MAINTAINER] [--vbmeta {skip,disable,enable}]
               [--zstd-level ZSTD_LEVEL] [--zip-level ZIP_LEVEL] [-o OUTPUT]
               [--no-fastboot] [--tui] [--gui] [--prompt]
```

### CLI Options
- `-i, --imgs-path`: Path to folder containing dumped `.img` partition files.
- `-d, --device`: Target device marketing name (e.g., `Infinix GT 20 Pro`).
- `-c, --codename`: Board codename (e.g., `X6853`).
- `-v, --version`: Firmware version (e.g., `V14.0.1.0`).
- `-m, --maintainer`: Maintainer name (default: `Mehraann`).
- `--vbmeta`: AVB 2.0 flag policy (`skip`, `disable`, `enable`).
- `--zstd-level`: Zstandard compression level (`0`-`22`, default: `1`).
- `--zip-level`: ZIP compression level (`0`-`9`, default: `1`).
- `-o, --output`: Custom output path for the flashable ZIP.
- `--no-fastboot`: Exclude fastboot scripts from the final ZIP package.
- `--tui`: Force launch the Antumbra TUI.
- `--gui`: Launch the legacy Windows 11 Fluent Glass GUI.
- `--prompt`: Launch the classic linear console wizard.

### Headless CLI Example
```bash
python3 main.py -i /path/to/extracted/firmware \
               -d "Infinix GT 20 Pro" \
               -c "X6853" \
               -v "14.0.1.0" \
               -m "Mehraann" \
               --vbmeta disable \
               --zstd-level 3
```

---

## Partition Classification Engine

SpeedFlasher automatically scans and sorts partitions into appropriate flashing logic:

1. **Super / Dynamic Partitions**:
   `system`, `vendor`, `product`, `system_ext`, `system_dlkm`, `vendor_dlkm`, `odm`, `odm_dlkm`, `my_product`, `my_stock`, etc.
   *Handled via `lptools` in recovery and fastbootd flashing.*

2. **Bootchain & Direct Partitions**:
   `boot`, `dtbo`, `init_boot`, `vendor_boot`, `recovery`, `vbmeta`, `vbmeta_system`, `vbmeta_vendor`, `pvmfw`.
   *Flashed directly to bootloader partitions with slot detection.*

3. **Firmware Partitions**:
   `lk`, `logo`, `md1img`, `tee`, `scp`, `sspm`, `spmfw`, `gz`, `dpm`, `pi_img`, `cam_vpu`, `preloader`, etc.
   *Flashed safely to peripheral storage partitions.*

---

## Credits & Attribution

- **Original SpeedFlasher Engine**: Created by **Mehraann** ([@sheikhmehraann](https://github.com/sheikhmehraann))
- **Patched Antumbra TUI Edition**: Created and patched by **Softbrick**
- **Design Inspiration**: Antumbra TUI & Penumbra by Shomy

---

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See [LICENSE](LICENSE) for details.
