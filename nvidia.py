#!/usr/bin/env python3
"""
Simple NVIDIA GPU Switcher
Toggles between NVIDIA GPU and integrated graphics
Requires root privileges
"""

import os
import sys
import subprocess
from pathlib import Path

# Configuration file paths
XORG_CONF_DIR = "/etc/X11/xorg.conf.d"
NVIDIA_CONF = f"{XORG_CONF_DIR}/10-nvidia-drm-outputclass.conf"
LIGHTDM_SETUP = "/etc/lightdm/nvidia.sh"
LIGHTDM_CONF_D = "/etc/lightdm/lightdm.conf.d"
LIGHTDM_NVIDIA_CONF = f"{LIGHTDM_CONF_D}/20-nvidia.conf"
STATE_FILE = "/tmp/gpu-mode.state"
UDEV_RULES_FILE = "/etc/udev/rules.d/00-remove-nvidia.rules"

# NVIDIA configuration template (BusID will be inserted)
NVIDIA_CONFIG_TEMPLATE = """Section "OutputClass"
    Identifier "nvidia"
    MatchDriver "nvidia-drm"
    Driver "nvidia"
EndSection

Section "ServerLayout"
    Identifier "layout"
    Screen 0 "nvidia"
    Inactive "intel"
EndSection

Section "Device"
    Identifier "nvidia"
    Driver "nvidia"
    BusID "{busid}"
    Option "ForceCompositionPipeline" "on"
EndSection

Section "Screen"
    Identifier "nvidia"
    Device "nvidia"
    Option "AllowEmptyInitialConfiguration"
EndSection

Section "Device"
    Identifier "intel"
    Driver "modesetting"
EndSection

Section "Screen"
    Identifier "intel"
    Device "intel"
EndSection
"""

# udev rules to power down NVIDIA GPU
UDEV_RULES_CONTENT = """# Remove NVIDIA USB xHCI Host Controller devices, if present
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x0c0330", ATTR{power/control}="auto", ATTR{remove}="1"

# Remove NVIDIA USB Type-C UCSI devices, if present
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x0c8000", ATTR{power/control}="auto", ATTR{remove}="1"

# Remove NVIDIA Audio devices, if present
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x040300", ATTR{power/control}="auto", ATTR{remove}="1"

# Remove NVIDIA VGA/3D controller devices
ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x03[0-9]*", ATTR{power/control}="auto", ATTR{remove}="1"
"""

def get_nvidia_busid():
    """Detect NVIDIA GPU BusID from lspci"""
    try:
        result = subprocess.run(
            ["lspci", "-nn"],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            # Look for NVIDIA VGA or 3D controller
            if "NVIDIA" in line and ("VGA" in line or "3D" in line):
                # Extract PCI address (e.g., "01:00.0")
                pci_addr = line.split()[0]
                # Convert to X.org BusID format: "PCI:1:0:0"
                parts = pci_addr.replace(".", ":").split(":")
                busid = f"PCI:{int(parts[0], 16)}:{int(parts[1], 16)}:{int(parts[2])}"
                return busid
    except (subprocess.CalledProcessError, IndexError, ValueError) as e:
        print(f"Warning: Could not detect NVIDIA BusID: {e}")
    return None

# LightDM display setup script content
LIGHTDM_SETUP_SCRIPT = """#!/bin/sh
xrandr --setprovideroutputsource modesetting NVIDIA-0
xrandr --auto
"""

# LightDM configuration for NVIDIA
LIGHTDM_NVIDIA_CONFIG = """[Seat:*]
display-setup-script=/etc/lightdm/nvidia.sh
"""

def run_cmd(cmd_list):
    """Run a command and return success status"""
    try:
        subprocess.run(cmd_list, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        return False

def check_root():
    """Check if running as root"""
    if os.geteuid() != 0:
        print("Error: This script must be run as root (use sudo)")
        sys.exit(1)

def get_current_mode():
    """Determine current GPU mode"""
    if os.path.exists(NVIDIA_CONF):
        return "nvidia"
    else:
        return "intel"

def is_gpu_powered_down():
    """Check if udev rules for GPU power down are installed"""
    return os.path.exists(UDEV_RULES_FILE)

def switch_to_nvidia():
    """Enable NVIDIA GPU"""
    print("Switching to NVIDIA GPU...")

    # Remove udev rules if present (need GPU powered on)
    if os.path.exists(UDEV_RULES_FILE):
        os.remove(UDEV_RULES_FILE)
        print(f"Removed udev rules: {UDEV_RULES_FILE}")
        # Reload udev rules
        run_cmd(["udevadm", "control", "--reload-rules"])
        print("Reloaded udev rules")

    # Detect NVIDIA BusID
    busid = get_nvidia_busid()
    if not busid:
        print("Error: Could not detect NVIDIA GPU BusID")
        print("Make sure NVIDIA drivers are installed and the GPU is detected by lspci")
        print("If GPU was powered down, a reboot may be required first")
        sys.exit(1)
    print(f"Detected NVIDIA GPU at BusID: {busid}")

    # Create xorg.conf.d directory if it doesn't exist
    Path(XORG_CONF_DIR).mkdir(parents=True, exist_ok=True)

    # Create NVIDIA config with detected BusID
    nvidia_config = NVIDIA_CONFIG_TEMPLATE.format(busid=busid)
    with open(NVIDIA_CONF, 'w') as f:
        f.write(nvidia_config)
    print(f"Created NVIDIA config at {NVIDIA_CONF}")

    # Create LightDM display setup script
    lightdm_dir = os.path.dirname(LIGHTDM_SETUP)
    Path(lightdm_dir).mkdir(parents=True, exist_ok=True)

    with open(LIGHTDM_SETUP, 'w') as f:
        f.write(LIGHTDM_SETUP_SCRIPT)
    os.chmod(LIGHTDM_SETUP, 0o755)
    print(f"Created LightDM setup script at {LIGHTDM_SETUP}")

    # Create LightDM configuration in conf.d directory
    Path(LIGHTDM_CONF_D).mkdir(parents=True, exist_ok=True)
    with open(LIGHTDM_NVIDIA_CONF, 'w') as f:
        f.write(LIGHTDM_NVIDIA_CONFIG)
    print(f"Created LightDM config at {LIGHTDM_NVIDIA_CONF}")

    # Save state
    with open(STATE_FILE, 'w') as f:
        f.write("nvidia")

    print("✓ Switched to NVIDIA GPU")
    print("Please restart your display manager or reboot for changes to take effect")
    print("  Reboot: sudo reboot")
    print("  Or restart display manager (LightDM): sudo systemctl restart lightdm")

def switch_to_intel(power_down=False):
    """Disable NVIDIA GPU (use integrated graphics)"""
    print("Switching to integrated graphics...")

    # Remove NVIDIA config
    if os.path.exists(NVIDIA_CONF):
        os.remove(NVIDIA_CONF)
        print(f"Removed NVIDIA config: {NVIDIA_CONF}")
    else:
        print("NVIDIA config not found, already using integrated graphics")

    # Remove LightDM display setup script
    if os.path.exists(LIGHTDM_SETUP):
        os.remove(LIGHTDM_SETUP)
        print(f"Removed LightDM setup script: {LIGHTDM_SETUP}")

    # Remove LightDM config
    if os.path.exists(LIGHTDM_NVIDIA_CONF):
        os.remove(LIGHTDM_NVIDIA_CONF)
        print(f"Removed LightDM config: {LIGHTDM_NVIDIA_CONF}")

    # Handle GPU power down option
    if power_down:
        # Create udev rules directory if needed
        udev_dir = os.path.dirname(UDEV_RULES_FILE)
        Path(udev_dir).mkdir(parents=True, exist_ok=True)
        
        with open(UDEV_RULES_FILE, 'w') as f:
            f.write(UDEV_RULES_CONTENT)
        print(f"Created udev rules for GPU power down: {UDEV_RULES_FILE}")
        
        # Reload udev rules
        run_cmd(["udevadm", "control", "--reload-rules"])
        print("Reloaded udev rules")
        print("GPU will be powered down on next reboot")
    else:
        # Remove udev rules if they exist
        if os.path.exists(UDEV_RULES_FILE):
            os.remove(UDEV_RULES_FILE)
            print(f"Removed udev rules: {UDEV_RULES_FILE}")
            run_cmd(["udevadm", "control", "--reload-rules"])

    # Save state
    with open(STATE_FILE, 'w') as f:
        f.write("intel" + ("-powerdown" if power_down else ""))

    print("✓ Switched to integrated graphics")
    if power_down:
        print("✓ GPU power down enabled (will take effect after reboot)")
    print("Please restart your display manager or reboot for changes to take effect")
    print("  Reboot: sudo reboot")
    print("  Or restart display manager (LightDM): sudo systemctl restart lightdm")

def show_status():
    """Show current GPU status"""
    mode = get_current_mode()
    power_down = is_gpu_powered_down()
    
    print(f"Current GPU mode: {mode}")

    if mode == "nvidia":
        print("  NVIDIA GPU is active")
        print(f"  Config: {NVIDIA_CONF}")
        print(f"  LightDM setup: {LIGHTDM_SETUP}")
        print(f"  LightDM config: {LIGHTDM_NVIDIA_CONF}")
    else:
        print("  Integrated graphics is active")
        print(f"  NVIDIA config: not present")
        print(f"  LightDM setup: not present")
        print(f"  LightDM config: not present")
    
    if power_down:
        print("  GPU power down: ENABLED")
        print(f"  udev rules: {UDEV_RULES_FILE}")
    else:
        print("  GPU power down: disabled")

    return mode

def main():
    if len(sys.argv) < 2:
        print("NVIDIA GPU Switcher")
        print("=" * 50)
        print()
        show_status()
        print()
        print("Usage:")
        print("  sudo python3 nvidia.py nvidia            - Switch to NVIDIA GPU")
        print("  sudo python3 nvidia.py intel             - Switch to integrated graphics")
        print("  sudo python3 nvidia.py intel --powerdown - Switch to integrated + power down GPU")
        print("  sudo python3 nvidia.py toggle            - Toggle between GPUs")
        print("  sudo python3 nvidia.py status            - Show current GPU status")
        sys.exit(0)

    command = sys.argv[1].lower()
    power_down = "--powerdown" in sys.argv or "-p" in sys.argv

    if command == "status":
        show_status()
        sys.exit(0)

    check_root()

    if command == "nvidia":
        switch_to_nvidia()
    elif command == "intel":
        switch_to_intel(power_down=power_down)
    elif command == "toggle":
        mode = get_current_mode()
        if mode == "nvidia":
            switch_to_intel(power_down=power_down)
        else:
            switch_to_nvidia()
    else:
        print(f"Unknown command: {command}")
        print("Valid commands: nvidia, intel, toggle, status")
        sys.exit(1)

if __name__ == "__main__":
    main()