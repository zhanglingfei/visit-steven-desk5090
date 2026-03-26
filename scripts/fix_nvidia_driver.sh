#!/bin/bash
# Fix NVIDIA driver version mismatch after power loss
# This script attempts to reload the NVIDIA driver module

set -e

echo "=== NVIDIA Driver Fix Script ==="
echo "Detected issue: Driver/library version mismatch"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to run with sudo"
    echo "Usage: sudo $0"
    exit 1
fi

echo "Step 1: Stopping services that may use NVIDIA GPU..."
systemctl stop display-manager 2>/dev/null || true
sleep 2

echo "Step 2: Unloading NVIDIA kernel modules..."
# Try to unload in reverse dependency order
modprobe -r nvidia-drm 2>/dev/null || true
modprobe -r nvidia-modeset 2>/dev/null || true
modprobe -r nvidia-uvm 2>/dev/null || true
modprobe -r nvidia 2>/dev/null || true

# Check if modules are still loaded
if lsmod | grep -q nvidia; then
    echo "WARNING: Some NVIDIA modules are still loaded. Trying force removal..."
    rmmod -f nvidia-drm 2>/dev/null || true
    rmmod -f nvidia-modeset 2>/dev/null || true
    rmmod -f nvidia-uvm 2>/dev/null || true
    rmmod -f nvidia 2>/dev/null || true
fi

if lsmod | grep -q nvidia; then
    echo "ERROR: Unable to unload NVIDIA modules. A system reboot is required."
    echo "Please run: sudo reboot"
    exit 1
fi

echo "Step 3: Reloading NVIDIA kernel modules..."
modprobe nvidia
modprobe nvidia-modeset 2>/dev/null || true
modprobe nvidia-drm 2>/dev/null || true
modprobe nvidia-uvm 2>/dev/null || true

echo "Step 4: Verifying driver..."
if nvidia-smi > /dev/null 2>&1; then
    echo "SUCCESS: NVIDIA driver is now working!"
    nvidia-smi --query-gpu=name,driver_version,temperature.gpu,power.draw --format=csv
else
    echo "ERROR: NVIDIA driver still not working. A system reboot is required."
    echo "Please run: sudo reboot"
    exit 1
fi

echo ""
echo "Step 5: Restarting display manager..."
systemctl start display-manager 2>/dev/null || true

echo ""
echo "=== Fix complete ==="
