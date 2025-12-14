#!/usr/bin/env python3
import sys
import subprocess
import os
import re

# Paths
HOME = os.path.expanduser("~")
XSESSIONRC = os.path.join(HOME, ".xsessionrc")
ALACRITTY_CONFIG = os.path.join(HOME, ".config", "alacritty", "alacritty.toml")

# Helper function to run shell commands easily
def run_cmd(cmd_list):
    try:
        subprocess.run(cmd_list, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")

# Check for arguments
if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <mode>")
    print("Modes:")
    print("  highdpi  - Enable high-DPI settings")
    print("  normal   - Revert to normal settings")
    sys.exit(1)

mode = sys.argv[1]

# --- High-DPI Mode Settings ---
if mode == "highdpi":
    print("Enabling high-DPI settings...")

    # Set XFCE settings
    run_cmd(["xfconf-query", "-c", "xsettings", "-p", "/Gdk/WindowScalingFactor", "-s", "2"])
    run_cmd(["xfconf-query", "-c", "xfwm4", "-p", "/general/theme", "-s", "Default-xhdpi"])
    run_cmd(["xfconf-query", "-c", "xsettings", "-p", "/Gtk/CursorThemeSize", "-s", "42"])
    run_cmd(["xfconf-query", "-c", "xsettings", "-p", "/Xft/DPI", "-s", "95"]) # this was 192 but it looks better at 95

    # Update .xsessionrc
    if os.path.exists(XSESSIONRC):
        with open(XSESSIONRC, "r") as f:
            content = f.read()

        if "export QT_SCALE_FACTOR=2" not in content:
            print("Adding QT_SCALE_FACTOR to ~/.xsessionrc")
            with open(XSESSIONRC, "a") as f:
                f.write("\nexport QT_SCALE_FACTOR=2\n")
        else:
            print("QT_SCALE_FACTOR already set in ~/.xsessionrc")
    else:
        # Create file if it doesn't exist
        with open(XSESSIONRC, "w") as f:
            f.write("export QT_SCALE_FACTOR=2\n")

    # Update Alacritty config
    if os.path.exists(ALACRITTY_CONFIG):
        print("Setting Alacritty font size to 24 for high-DPI")
        with open(ALACRITTY_CONFIG, "r") as f:
            content = f.read()

        # Regex replacement (equivalent to sed)
        new_content = re.sub(r"size = \d+\.\d+", "size = 24.0", content)

        with open(ALACRITTY_CONFIG, "w") as f:
            f.write(new_content)
    else:
        print(f"Alacritty config not found at {ALACRITTY_CONFIG}")

    print("High-DPI settings enabled. Please log out and back in.")

# --- Normal Mode Settings ---
elif mode == "normal":
    print("Reverting to normal settings...")

    # Reset XFCE settings
    run_cmd(["xfconf-query", "-c", "xsettings", "-p", "/Gdk/WindowScalingFactor", "-s", "1"])
    run_cmd(["xfconf-query", "-c", "xfwm4", "-p", "/general/theme", "-s", "Default"])
    run_cmd(["xfconf-query", "-c", "xsettings", "-p", "/Gtk/CursorThemeSize", "-s", "24"])
    run_cmd(["xfconf-query", "-c", "xsettings", "-p", "/Xft/DPI", "-s", "96"])

    # Update .xsessionrc
    if os.path.exists(XSESSIONRC):
        with open(XSESSIONRC, "r") as f:
            lines = f.readlines()

        # Rewrite file skipping the QT_SCALE_FACTOR line
        with open(XSESSIONRC, "w") as f:
            found = False
            for line in lines:
                if "export QT_SCALE_FACTOR=2" not in line:
                    f.write(line)
                else:
                    found = True

            if found:
                print("Removing QT_SCALE_FACTOR from ~/.xsessionrc")
            else:
                print("QT_SCALE_FACTOR not found in ~/.xsessionrc")

    # Update Alacritty config
    if os.path.exists(ALACRITTY_CONFIG):
        print("Setting Alacritty font size to 14 for normal mode")
        with open(ALACRITTY_CONFIG, "r") as f:
            content = f.read()

        new_content = re.sub(r"size = \d+\.\d+", "size = 14.0", content)

        with open(ALACRITTY_CONFIG, "w") as f:
            f.write(new_content)
    else:
         print(f"Alacritty config not found at {ALACRITTY_CONFIG}")

    print("Normal settings restored. Please log out and back in.")

else:
    print(f"Error: Invalid mode '{mode}'.")
    print("Usage: script.py <mode>")
    print("Modes:")
    print("  highdpi  - Enable high-DPI settings")
    print("  normal   - Revert to normal settings")
    sys.exit(1)
