"""System health monitoring service for diagnosing hardware/driver issues"""
import subprocess
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class GpuHealthStatus(BaseModel):
    detected: bool
    name: Optional[str] = None
    driver_status: str  # "ok", "error", "not_found"
    driver_error: Optional[str] = None
    temperature: Optional[float] = None
    power_draw: Optional[float] = None


class PowerSourceHealth(BaseModel):
    source: str
    available: bool
    error: Optional[str] = None


class SystemHealthStatus(BaseModel):
    timestamp: str
    gpu_status: list[GpuHealthStatus]
    power_sources: list[PowerSourceHealth]
    recommendations: list[str]


def check_nvidia_gpu_health() -> GpuHealthStatus:
    """Check NVIDIA GPU driver health"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 3:
                return GpuHealthStatus(
                    detected=True,
                    name=parts[0].strip(),
                    driver_status="ok",
                    temperature=float(parts[1].strip()) if parts[1].strip() else None,
                    power_draw=float(parts[2].strip()) if parts[2].strip() else None,
                )
            return GpuHealthStatus(detected=True, driver_status="ok")

        # Check for specific errors
        stderr = result.stderr.lower()
        stdout = result.stdout.lower()
        error_msg = ""

        if "driver/library version mismatch" in stdout or "driver/library version mismatch" in stderr:
            error_msg = "Driver/library version mismatch. NVIDIA driver needs restart."
        elif "failed to initialize nvml" in stdout or "failed to initialize nvml" in stderr:
            error_msg = "NVML initialization failed. Driver may need reload."
        elif result.returncode == 18:
            error_msg = "NVIDIA driver error (code 18). Try: sudo rmmod nvidia_uvm nvidia && sudo modprobe nvidia"
        else:
            error_msg = f"nvidia-smi error (code {result.returncode})"

        return GpuHealthStatus(
            detected=True,  # GPU exists but driver has issues
            driver_status="error",
            driver_error=error_msg,
        )

    except FileNotFoundError:
        return GpuHealthStatus(detected=False, driver_status="not_found")
    except subprocess.TimeoutExpired:
        return GpuHealthStatus(
            detected=True,
            driver_status="error",
            driver_error="nvidia-smi timeout - driver may be unresponsive",
        )


def check_amd_gpu_health() -> list[GpuHealthStatus]:
    """Check AMD GPU health via hwmon interface"""
    gpus = []
    hwmon_path = Path("/sys/class/hwmon")

    if not hwmon_path.exists():
        return gpus

    for hwmon in hwmon_path.iterdir():
        name_file = hwmon / "name"
        if not name_file.exists():
            continue

        name = name_file.read_text().strip()
        if name != "amdgpu":
            continue

        gpu_name = "AMD GPU"
        temperature = None
        power_draw = None

        # Try to get GPU name
        device_path = hwmon / "device"
        if device_path.exists():
            try:
                model_file = device_path / "model"
                if model_file.exists():
                    gpu_name = model_file.read_text().strip()
            except:
                pass

        # Read temperature
        temp_file = hwmon / "temp1_input"
        if temp_file.exists():
            try:
                temp_raw = int(temp_file.read_text().strip())
                temperature = temp_raw / 1000.0
            except (ValueError, IOError):
                pass

        # Read power
        power_file = hwmon / "power1_input"
        if power_file.exists():
            try:
                power_raw = int(power_file.read_text().strip())
                power_draw = power_raw / 1_000_000.0  # Convert from microwatts
            except (ValueError, IOError):
                pass

        # Check if rocm-smi is available
        rocm_available = False
        try:
            result = subprocess.run(["rocm-smi", "--version"], capture_output=True, timeout=2)
            rocm_available = result.returncode == 0
        except:
            pass

        gpus.append(GpuHealthStatus(
            detected=True,
            name=gpu_name,
            driver_status="ok",
            temperature=temperature,
            power_draw=power_draw,
            driver_error=None if rocm_available else "ROCm not installed. Limited metrics available.",
        ))

    return gpus


def check_power_sources() -> list[PowerSourceHealth]:
    """Check available power monitoring sources"""
    sources = []

    # Check NVIDIA power
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            sources.append(PowerSourceHealth(source="nvidia", available=True))
        else:
            error = "Driver error"
            if "driver/library version mismatch" in result.stdout.lower():
                error = "Driver version mismatch"
            sources.append(PowerSourceHealth(source="nvidia", available=False, error=error))
    except FileNotFoundError:
        sources.append(PowerSourceHealth(source="nvidia", available=False, error="Not installed"))
    except subprocess.TimeoutExpired:
        sources.append(PowerSourceHealth(source="nvidia", available=False, error="Timeout"))

    # Check AMD GPU hwmon
    hwmon_path = Path("/sys/class/hwmon")
    amdgpu_found = False
    if hwmon_path.exists():
        for hwmon in hwmon_path.iterdir():
            name_file = hwmon / "name"
            if name_file.exists() and name_file.read_text().strip() == "amdgpu":
                power_file = hwmon / "power1_input"
                if power_file.exists():
                    amdgpu_found = True
                    sources.append(PowerSourceHealth(source="amdgpu_hwmon", available=True))
                    break
    if not amdgpu_found:
        sources.append(PowerSourceHealth(source="amdgpu_hwmon", available=False, error="No AMD GPU found"))

    # Check ACPI
    acpi_path = Path("/sys/class/power_supply")
    if acpi_path.exists() and any(acpi_path.iterdir()):
        sources.append(PowerSourceHealth(source="acpi", available=True))
    else:
        sources.append(PowerSourceHealth(source="acpi", available=False, error="No ACPI power supply"))

    # Check RAPL
    rapl_path = Path("/sys/class/powercap/intel-rapl")
    if rapl_path.exists():
        sources.append(PowerSourceHealth(source="rapl", available=True))
    else:
        sources.append(PowerSourceHealth(source="rapl", available=False, error="Not available"))

    return sources


def get_system_health() -> SystemHealthStatus:
    """Get comprehensive system health status"""
    gpu_status = []
    recommendations = []

    # Check NVIDIA
    nvidia_status = check_nvidia_gpu_health()
    if nvidia_status.detected or nvidia_status.driver_status != "not_found":
        gpu_status.append(nvidia_status)

    if nvidia_status.driver_status == "error":
        recommendations.append(
            "NVIDIA driver issue detected. Try: sudo rmmod nvidia_uvm nvidia && sudo modprobe nvidia"
        )
        recommendations.append(
            "If reload fails, reboot the system to restore NVIDIA driver functionality."
        )

    # Check AMD
    amd_gpus = check_amd_gpu_health()
    gpu_status.extend(amd_gpus)

    for amd_gpu in amd_gpus:
        if amd_gpu.driver_error and "ROCm" in amd_gpu.driver_error:
            recommendations.append(
                "ROCm not installed. For full AMD GPU metrics, install: sudo apt install rocm-smi"
            )

    # Check power sources
    power_sources = check_power_sources()

    # Generate recommendations based on power sources
    nvidia_power_ok = any(s.source == "nvidia" and s.available for s in power_sources)
    amdgpu_power_ok = any(s.source == "amdgpu_hwmon" and s.available for s in power_sources)

    if not nvidia_power_ok and not amdgpu_power_ok:
        acpi_ok = any(s.source == "acpi" and s.available for s in power_sources)
        if acpi_ok:
            recommendations.append(
                "Using ACPI for power monitoring. GPU power breakdown unavailable."
            )
        else:
            recommendations.append(
                "Limited power monitoring available. Using CPU-based estimation."
            )

    # If no GPUs detected at all
    if not gpu_status:
        recommendations.append("No GPUs detected. Check hardware connections.")

    return SystemHealthStatus(
        timestamp=datetime.utcnow().isoformat(),
        gpu_status=gpu_status,
        power_sources=power_sources,
        recommendations=recommendations,
    )
