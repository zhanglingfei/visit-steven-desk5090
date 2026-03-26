import sqlite3
import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
import threading

from app.models.power import PowerReading, PowerHistoryResponse

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "power_logs.db"

# Lock for thread-safe database operations
db_lock = threading.Lock()

# In-memory cache for accumulated kWh (since first reading)
_power_cache = {
    "first_reading_time": None,
    "total_kwh": 0.0,
    "last_reading": None,
    "last_watts": 0.0,
}


def init_database():
    """Initialize SQLite database with optimized schema for time-series data"""
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Main readings table with time-series optimizations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS power_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                watts REAL NOT NULL,
                voltage REAL,
                current REAL,
                source TEXT NOT NULL,
                kwh_increment REAL NOT NULL DEFAULT 0,
                UNIQUE(timestamp)
            )
        """)

        # Indexes for efficient time-range queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON power_readings(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp_desc ON power_readings(timestamp DESC)
        """)

        # Hourly aggregated table for fast historical queries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS power_hourly (
                hour_timestamp INTEGER PRIMARY KEY,
                avg_watts REAL NOT NULL,
                max_watts REAL NOT NULL,
                min_watts REAL NOT NULL,
                total_kwh REAL NOT NULL,
                readings_count INTEGER NOT NULL
            )
        """)

        # Daily aggregated table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS power_daily (
                date TEXT PRIMARY KEY,
                total_kwh REAL NOT NULL,
                avg_watts REAL NOT NULL,
                max_watts REAL NOT NULL,
                min_watts REAL NOT NULL
            )
        """)

        # Metadata table for tracking totals
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS power_metadata (
                key TEXT PRIMARY KEY,
                value REAL NOT NULL
            )
        """)

        conn.commit()
        conn.close()


def _get_power_from_acpi() -> Optional[PowerReading]:
    """Try to read power from ACPI power supply interface"""
    try:
        power_supply_path = Path("/sys/class/power_supply")
        if not power_supply_path.exists():
            return None

        # Look for AC adapter or battery with power info
        for supply in power_supply_path.iterdir():
            try:
                # Try reading power_now (microwatts)
                power_now_file = supply / "power_now"
                if power_now_file.exists():
                    power_uw = int(power_now_file.read_text().strip())
                    watts = power_uw / 1_000_000

                    voltage = None
                    current_val = None

                    # Try to get voltage
                    voltage_file = supply / "voltage_now"
                    if voltage_file.exists():
                        voltage = int(voltage_file.read_text().strip()) / 1_000_000

                    # Try to get current
                    current_file = supply / "current_now"
                    if current_file.exists():
                        current_val = int(current_file.read_text().strip()) / 1_000_000

                    source_type = "battery" if "BAT" in supply.name else "ac_adapter"

                    return PowerReading(
                        timestamp=time.time(),
                        watts=watts,
                        voltage=voltage,
                        current=current_val,
                        source=source_type
                    )

                # Try reading from energy rate
                energy_rate_file = supply / "energy_rate"
                if energy_rate_file.exists():
                    watts = float(energy_rate_file.read_text().strip())

                    return PowerReading(
                        timestamp=time.time(),
                        watts=watts,
                        source="battery"
                    )

            except (ValueError, IOError, PermissionError):
                continue

        return None
    except Exception:
        return None


def _get_power_from_nvidia() -> Optional[PowerReading]:
    """Try to read power from NVIDIA GPU via nvidia-smi"""
    try:
        import subprocess

        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None

        watts = float(result.stdout.strip())
        if watts > 0:
            return PowerReading(
                timestamp=time.time(),
                watts=watts,
                source="nvidia"
            )

        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, Exception):
        return None


def _get_power_from_ipmi() -> Optional[PowerReading]:
    """Try to read power via IPMI (for servers)"""
    try:
        import subprocess

        result = subprocess.run(
            ["ipmitool", "sensor", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None

        # Look for power-related sensors
        for line in result.stdout.split("\n"):
            if "watt" in line.lower() or "power" in line.lower():
                parts = line.split("|")
                if len(parts) >= 2:
                    try:
                        watts = float(parts[1].strip())
                        if watts > 0:
                            return PowerReading(
                                timestamp=time.time(),
                                watts=watts,
                                source="ipmi"
                            )
                    except ValueError:
                        continue

        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return None


def _get_power_from_rapl() -> Optional[PowerReading]:
    """Try to read power from Intel RAPL (Running Average Power Limit)"""
    try:
        rapl_path = Path("/sys/class/powercap/intel-rapl")
        if not rapl_path.exists():
            return None

        total_watts = 0.0
        has_reading = False

        for domain in rapl_path.iterdir():
            if not domain.name.startswith("intel-rapl:"):
                continue

            try:
                # Read energy counter (microjoules)
                energy_file = domain / "energy_uj"
                if energy_file.exists():
                    # We need to calculate power from energy difference
                    # For now, read the power limit as approximation
                    constraint_file = domain / "constraint_0_power_limit_uw"
                    if constraint_file.exists():
                        power_uw = int(constraint_file.read_text().strip())
                        total_watts += power_uw / 1_000_000
                        has_reading = True
            except (ValueError, IOError, PermissionError):
                continue

        if has_reading:
            return PowerReading(
                timestamp=time.time(),
                watts=total_watts,
                source="rapl"
            )

        return None
    except Exception:
        return None


def _estimate_power_from_cpu() -> PowerReading:
    """Estimate power based on CPU usage when no direct sensor available"""
    try:
        import psutil

        # Get CPU info
        cpu_percent = psutil.cpu_percent(interval=0)
        cpu_count = psutil.cpu_count()

        # Rough estimation: base 10W + 5W per core at 100% load
        # This is a very rough estimate and varies by CPU
        base_power = 10.0
        max_cpu_power = cpu_count * 5.0
        estimated_watts = base_power + (max_cpu_power * cpu_percent / 100)

        # Add memory power estimate (~3W per 8GB)
        mem = psutil.virtual_memory()
        mem_gb = mem.total / (1024**3)
        estimated_watts += (mem_gb / 8) * 3

        return PowerReading(
            timestamp=time.time(),
            watts=round(estimated_watts, 2),
            source="estimated"
        )
    except Exception:
        return PowerReading(
            timestamp=time.time(),
            watts=50.0,  # Default fallback
            source="estimated"
        )


def _get_total_system_power() -> PowerReading:
    """Calculate total system power by summing all component sources"""
    total_watts = 0.0
    sources = []
    voltage = None
    current = None

    # Try to get GPU power (NVIDIA)
    gpu_reading = _get_power_from_nvidia()
    if gpu_reading:
        total_watts += gpu_reading.watts
        sources.append(f"nvidia({gpu_reading.watts:.1f}W)")

    # Try to get GPU power (AMD via hwmon - more reliable)
    amd_gpu_hwmon = _get_power_from_amdgpu_hwmon()
    if amd_gpu_hwmon:
        total_watts += amd_gpu_hwmon.watts
        sources.append(f"amdgpu({amd_gpu_hwmon.watts:.1f}W)")

    # Try to get GPU power (AMD via rocm-smi)
    amd_gpu = _get_power_from_rocm()
    if amd_gpu:
        total_watts += amd_gpu.watts
        sources.append(f"amd_gpu({amd_gpu.watts:.1f}W)")

    # Try ACPI (often gives total system power on laptops)
    acpi_reading = _get_power_from_acpi()
    if acpi_reading:
        # If ACPI reports battery discharge, that's total system power
        if acpi_reading.source == "battery":
            return acpi_reading
        total_watts += acpi_reading.watts
        sources.append(f"acpi({acpi_reading.watts:.1f}W)")
        voltage = acpi_reading.voltage
        current = acpi_reading.current

    # Try IPMI (servers often have total power here)
    ipmi_reading = _get_power_from_ipmi()
    if ipmi_reading:
        # IPMI usually reports total system power
        return ipmi_reading

    # Try RAPL for CPU power
    rapl_reading = _get_power_from_rapl()
    if rapl_reading:
        total_watts += rapl_reading.watts
        sources.append(f"rapl({rapl_reading.watts:.1f}W)")

    # If we have component readings, sum them up
    if sources:
        # Always add CPU power estimate if we have GPU but no CPU reading
        if gpu_reading or amd_gpu:
            # Estimate CPU power
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=0)
                cpu_count = psutil.cpu_count()
                # Base 10W + 5W per core at 100% load
                cpu_power = 10.0 + (cpu_count * 5.0 * cpu_percent / 100)
                # Add memory power (~3W per 8GB)
                mem = psutil.virtual_memory()
                mem_power = (mem.total / (1024**3) / 8) * 3
                total_cpu_mem = cpu_power + mem_power
                total_watts += total_cpu_mem
                sources.append(f"cpu_mem({total_cpu_mem:.1f}W)")
            except:
                # If estimation fails, add a typical 65W for CPU+RAM
                total_watts += 65.0
                sources.append("cpu_mem(65W)")

        return PowerReading(
            timestamp=time.time(),
            watts=round(total_watts, 2),
            voltage=voltage,
            current=current,
            source="+".join(sources)
        )

    # Fallback: estimate from CPU + add typical GPU idle power if GPU present
    return _estimate_power_with_gpu()


def _get_power_from_amdgpu_hwmon() -> Optional[PowerReading]:
    """Try to read power from AMD GPU via hwmon interface"""
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
                power_file = hwmon / "power1_input"
                if power_file.exists():
                    power_uw = int(power_file.read_text().strip())
                    watts = power_uw / 1_000_000
                    return PowerReading(
                        timestamp=time.time(),
                        watts=watts,
                        source="amdgpu"
                    )

        return None
    except Exception:
        return None


def _get_power_from_rocm() -> Optional[PowerReading]:
    """Try to read power from AMD GPU via rocm-smi"""
    try:
        import subprocess

        result = subprocess.run(
            ["rocm-smi", "--showpower", "--json"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None

        import json
        data = json.loads(result.stdout)

        total_watts = 0.0
        for key, card in data.items():
            if not key.startswith("card"):
                continue
            for pk, pv in card.items():
                if "power" in pk.lower() and "watt" in str(pv).lower():
                    try:
                        watts = float(str(pv).replace("W", "").strip())
                        total_watts += watts
                    except ValueError:
                        continue

        if total_watts > 0:
            return PowerReading(
                timestamp=time.time(),
                watts=total_watts,
                source="amd_gpu"
            )

        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return None


def _estimate_power_with_gpu() -> PowerReading:
    """Estimate power including GPU detection"""
    # Start with CPU estimate
    cpu_estimate = _estimate_power_from_cpu()
    total_watts = cpu_estimate.watts

    # Check for NVIDIA GPU and add typical power
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            # GPU detected - add minimum 50W (idle) to 350W (high-end gaming)
            # This is a rough estimate until nvidia-smi gives actual power
            total_watts += 50.0
            source = "estimated_cpu+gpu_idle"
        else:
            source = "estimated_cpu"
    except:
        source = "estimated_cpu"

    return PowerReading(
        timestamp=time.time(),
        watts=round(total_watts, 2),
        source=source
    )


def get_current_power() -> PowerReading:
    """Get current power reading from available sources"""
    return _get_total_system_power()


def log_power_reading(reading: PowerReading) -> float:
    """Log power reading to database and calculate kWh increment using trapezoidal rule"""
    global _power_cache

    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Check if we already have a reading within the last 10 seconds (deduplication)
        # This prevents multiple WebSocket connections from creating duplicate entries
        if _power_cache["last_reading"] is not None:
            time_since_last = reading.timestamp - _power_cache["last_reading"]
            if time_since_last < 10:  # Less than 10 seconds since last reading
                conn.close()
                return _power_cache["total_kwh"]  # Skip this reading

        # Calculate kWh increment since last reading
        kwh_increment = 0.0
        if _power_cache["last_reading"] is not None:
            time_diff_seconds = reading.timestamp - _power_cache["last_reading"]

            # Validate time difference (prevent negative or unrealistic values)
            if time_diff_seconds > 0:
                # Cap at 1 hour to prevent calculation errors from clock changes
                time_diff_seconds = min(time_diff_seconds, 3600)
                time_diff_hours = time_diff_seconds / 3600

                # Trapezoidal rule: average power × time
                avg_watts = (_power_cache["last_watts"] + reading.watts) / 2
                kwh_increment = (avg_watts * time_diff_hours) / 1000

                # Sanity check: max 10 kWh per interval (would require 24000W average)
                kwh_increment = min(kwh_increment, 10.0)

        # Insert reading (ignore if timestamp already exists)
        try:
            cursor.execute("""
                INSERT INTO power_readings (timestamp, watts, voltage, current, source, kwh_increment)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                reading.timestamp,
                reading.watts,
                reading.voltage,
                reading.current,
                reading.source,
                kwh_increment
            ))
        except sqlite3.IntegrityError:
            # Duplicate timestamp, skip
            conn.close()
            return _power_cache["total_kwh"]

        # Update accumulated total
        _power_cache["total_kwh"] += kwh_increment
        _power_cache["last_reading"] = reading.timestamp
        _power_cache["last_watts"] = reading.watts

        if _power_cache["first_reading_time"] is None:
            _power_cache["first_reading_time"] = reading.timestamp
            cursor.execute(
                "INSERT OR REPLACE INTO power_metadata (key, value) VALUES (?, ?)",
                ("first_reading_time", reading.timestamp)
            )

        cursor.execute(
            "INSERT OR REPLACE INTO power_metadata (key, value) VALUES (?, ?)",
            ("total_kwh", _power_cache["total_kwh"])
        )

        conn.commit()
        conn.close()

    return _power_cache["total_kwh"]


def get_total_kwh() -> float:
    """Get total accumulated kWh since first reading - recalculates from DB on first call"""
    global _power_cache

    # Try to load from database if not in cache
    if _power_cache["first_reading_time"] is None:
        with db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

            # Recalculate total_kwh from all readings for accuracy
            cursor.execute("SELECT SUM(kwh_increment) FROM power_readings")
            row = cursor.fetchone()
            if row and row[0] is not None:
                _power_cache["total_kwh"] = row[0]
            else:
                _power_cache["total_kwh"] = 0.0

            # Get the first reading timestamp
            cursor.execute("SELECT MIN(timestamp) FROM power_readings")
            row = cursor.fetchone()
            if row and row[0] is not None:
                _power_cache["first_reading_time"] = row[0]
                # Update metadata to match recalculated values
                cursor.execute(
                    "INSERT OR REPLACE INTO power_metadata (key, value) VALUES (?, ?)",
                    ("first_reading_time", row[0])
                )
                cursor.execute(
                    "INSERT OR REPLACE INTO power_metadata (key, value) VALUES (?, ?)",
                    ("total_kwh", _power_cache["total_kwh"])
                )
                conn.commit()

            conn.close()

    return _power_cache["total_kwh"]


def get_power_history(start_timestamp: float, end_timestamp: float) -> PowerHistoryResponse:
    """Get power statistics for a specific time period with accurate kWh calculation"""
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Get all readings in the time range
        cursor.execute("""
            SELECT timestamp, watts, kwh_increment
            FROM power_readings
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        """, (start_timestamp, end_timestamp))

        readings = cursor.fetchall()

        # Get the reading just before the start time (for accurate first interval calculation)
        cursor.execute("""
            SELECT timestamp, watts
            FROM power_readings
            WHERE timestamp < ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (start_timestamp,))
        prev_reading = cursor.fetchone()

        conn.close()

    if not readings:
        return PowerHistoryResponse(
            start_date=datetime.fromtimestamp(start_timestamp),
            end_date=datetime.fromtimestamp(end_timestamp),
            total_kwh=0.0,
            avg_watts=0.0,
            max_watts=0.0,
            min_watts=0.0,
            readings_count=0,
            hours_span=(end_timestamp - start_timestamp) / 3600
        )

    watts_values = [r[1] for r in readings]

    # Calculate total kWh ONLY from stored kwh_increment values
    # Each kwh_increment represents the energy consumed from the PREVIOUS reading
    # to the CURRENT reading (interval BEFORE the timestamp).
    #
    # For accurate query results:
    # - First reading: only include its kwh_increment if previous reading exists
    #   AND falls within the query range (meaning the entire interval is in range)
    # - Other readings: always include (their intervals are fully in range)
    if prev_reading:
        # Previous reading exists - check if it's within query range
        prev_ts = prev_reading[0]
        if prev_ts >= start_timestamp:
            # Previous reading is in range, so first reading's interval is fully in range
            total_kwh = sum(r[2] for r in readings)
        else:
            # Previous reading is before query start
            # First reading's interval is partially before query start - exclude it
            total_kwh = sum(r[2] for r in readings[1:])
    else:
        # No previous reading (this is the first ever reading)
        # Its kwh_increment is 0 anyway (no interval before it)
        total_kwh = sum(r[2] for r in readings)

    actual_data_start = readings[0][0]
    actual_data_end = readings[-1][0]

    # Cap end timestamp at current time to prevent future date queries from showing inflated data
    current_time = time.time()
    effective_end_timestamp = min(end_timestamp, current_time)

    # Calculate actual hours span based on data coverage within the query range
    # Also cap at current time to prevent future dates from affecting calculations
    data_span_start = max(actual_data_start, start_timestamp)
    data_span_end = min(min(actual_data_end, end_timestamp), current_time)
    actual_hours_span = max(0, (data_span_end - data_span_start) / 3600)

    return PowerHistoryResponse(
        start_date=datetime.fromtimestamp(start_timestamp),
        end_date=datetime.fromtimestamp(end_timestamp),
        total_kwh=round(total_kwh, 6),
        avg_watts=round(sum(watts_values) / len(watts_values), 2),
        max_watts=round(max(watts_values), 2),
        min_watts=round(min(watts_values), 2),
        readings_count=len(readings),
        hours_span=round(actual_hours_span, 2)
    )


def get_recent_readings(hours: int = 24) -> List[Tuple[float, float]]:
    """Get recent power readings for charting"""
    since = time.time() - (hours * 3600)

    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT timestamp, watts
            FROM power_readings
            WHERE timestamp >= ?
            ORDER BY timestamp
        """, (since,))

        readings = cursor.fetchall()
        conn.close()

    return readings


def cleanup_old_data(days_to_keep: int = 90):
    """Remove old detailed readings, keeping only hourly aggregates"""
    cutoff = time.time() - (days_to_keep * 24 * 3600)

    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Delete old readings
        cursor.execute("DELETE FROM power_readings WHERE timestamp < ?", (cutoff,))

        conn.commit()
        conn.close()


# Initialize database on module load
init_database()
