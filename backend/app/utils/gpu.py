import json
import subprocess
from pathlib import Path
from typing import Optional

from app.models.metrics import GpuMetrics


def get_gpu_metrics() -> GpuMetrics:
    """Get GPU metrics from available sources with fallback chain"""
    # Try NVIDIA first (most detailed info)
    metrics = _try_nvidia_smi()
    if metrics:
        return metrics

    # Try AMD ROCm (detailed info if available)
    metrics = _try_rocm_smi()
    if metrics:
        return metrics

    # Try AMD GPU via hwmon (basic info, no utilization)
    metrics = _try_amdgpu_hwmon()
    if metrics:
        return metrics

    return GpuMetrics(available=False)


def _try_nvidia_smi() -> Optional[GpuMetrics]:
    """Try to get GPU metrics from NVIDIA via nvidia-smi"""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.total,memory.used,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            # Log driver issues for debugging
            if "Driver/library version mismatch" in result.stdout or "Failed to initialize NVML" in result.stdout:
                print(f"[GPU] NVIDIA driver version mismatch detected. Driver restart may be needed.")
            return None
        parts = result.stdout.strip().split(",")
        if len(parts) < 5:
            return None
        return GpuMetrics(
            name=parts[0].strip(),
            utilization=float(parts[1].strip()),
            vram_total=int(float(parts[2].strip()) * 1024 * 1024),
            vram_used=int(float(parts[3].strip()) * 1024 * 1024),
            temperature=float(parts[4].strip()),
            available=True,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return None


def _try_rocm_smi() -> Optional[GpuMetrics]:
    """Try to get GPU metrics from AMD via rocm-smi"""
    try:
        result = subprocess.run(
            ["rocm-smi", "--showtemp", "--showuse", "--showmeminfo", "vram", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)

        # Parse first GPU card
        for key, card in data.items():
            if not key.startswith("card"):
                continue
            temp = None
            for tk, tv in card.items():
                if "temperature" in tk.lower() and "edge" in tk.lower():
                    temp = float(tv)
                    break
            # If edge not found, try junction
            if temp is None:
                for tk, tv in card.items():
                    if "temperature" in tk.lower():
                        try:
                            temp = float(tv)
                            break
                        except (ValueError, TypeError):
                            continue

            utilization = None
            for uk, uv in card.items():
                if "gpu use" in uk.lower() or "gpu utilization" in uk.lower():
                    utilization = float(str(uv).replace("%", ""))
                    break

            vram_total = None
            vram_used = None
            for mk, mv in card.items():
                ml = mk.lower()
                if "vram total" in ml:
                    vram_total = int(mv)
                elif "vram used" in ml:
                    vram_used = int(mv)

            return GpuMetrics(
                name=card.get("Card Series", card.get("card_series", "AMD GPU")),
                utilization=utilization,
                vram_total=vram_total,
                vram_used=vram_used,
                temperature=temp,
                available=True,
            )
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def _try_amdgpu_hwmon() -> Optional[GpuMetrics]:
    """Try to get GPU metrics from AMD GPU via hwmon interface (fallback when rocm-smi unavailable)"""
    try:
        hwmon_path = Path("/sys/class/hwmon")
        if not hwmon_path.exists():
            return None

        for hwmon in hwmon_path.iterdir():
            name_file = hwmon / "name"
            if not name_file.exists():
                continue

            name = name_file.read_text().strip()
            if name == "amdgpu":
                # Read GPU model from device info
                gpu_name = "AMD GPU"
                device_path = hwmon / "device"
                if device_path.exists():
                    try:
                        # Try to get model name from device
                        model_file = device_path / "model"
                        if model_file.exists():
                            gpu_name = model_file.read_text().strip()
                        else:
                            # Try vendor/device IDs
                            vendor_file = device_path / "vendor"
                            device_file = device_path / "device"
                            if vendor_file.exists() and device_file.exists():
                                vendor = vendor_file.read_text().strip()
                                device = device_file.read_text().strip()
                                gpu_name = f"AMD GPU ({device})"
                    except:
                        pass

                # Read temperature
                temperature = None
                temp_file = hwmon / "temp1_input"
                if temp_file.exists():
                    try:
                        temp_raw = int(temp_file.read_text().strip())
                        temperature = temp_raw / 1000.0  # Convert from millidegrees
                    except (ValueError, IOError):
                        pass

                # Read frequency (as proxy for utilization if available)
                freq_mhz = None
                freq_file = hwmon / "freq1_input"
                if freq_file.exists():
                    try:
                        freq_raw = int(freq_file.read_text().strip())
                        freq_mhz = freq_raw / 1000000.0  # Convert from Hz to MHz
                    except (ValueError, IOError):
                        pass

                # Note: hwmon doesn't provide VRAM info or utilization percentage
                # We return available=True with basic info
                return GpuMetrics(
                    name=gpu_name,
                    utilization=None,  # Not available via hwmon
                    vram_total=None,   # Not available via hwmon
                    vram_used=None,    # Not available via hwmon
                    temperature=temperature,
                    available=True,
                )

        return None
    except Exception:
        return None
