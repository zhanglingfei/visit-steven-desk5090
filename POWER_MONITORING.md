# Power Monitoring - Technical Documentation

## Overview
The power monitoring system collects power consumption data every 15 seconds and calculates accumulated energy usage in kWh with high accuracy.

## Data Collection

### Sampling Interval
- **Frequency**: Every 15 seconds (precise clock-aligned intervals)
- **Method**: WebSocket connection with `asyncio` timing
- **Deduplication**: Database UNIQUE constraint on timestamp + 10-second cache dedup

### Power Sources
The system reads from multiple sources (in order of priority):
1. **NVIDIA GPU** (`nvidia-smi`) - Primary discrete GPU power
2. **AMD GPU** (hwmon) - Integrated AMD GPU power
3. **AMD GPU** (rocm-smi) - Alternative AMD reading
4. **ACPI** - Battery/AC adapter power (laptops)
5. **IPMI** - Server power monitoring
6. **RAPL** - Intel CPU power estimation
7. **Estimated** - CPU load-based estimation + RAM (~3W per 8GB)

### Total Power Calculation
```
Total Power = GPU Power + CPU Power + RAM Power + other components
```

## kWh Calculation Method

### Trapezoidal Rule (Numerical Integration)
For each 15-second interval:
```
kWh_increment = (avg_watts × time_diff_hours) / 1000
where:
  avg_watts = (previous_watts + current_watts) / 2
  time_diff_hours = 15 / 3600 = 0.004167 hours
```

### Example Calculation
For 440W average over 15 seconds:
```
kWh = (440 × 0.004167) / 1000 = 0.001833 kWh
```

### Accumulated Total
```
total_kWh = Σ(kWh_increment for all intervals)
```

## Database Schema

### Table: `power_readings`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| timestamp | REAL | Unix timestamp (UNIQUE) |
| watts | REAL | Power reading in watts |
| voltage | REAL | Voltage (if available) |
| current | REAL | Current (if available) |
| source | TEXT | Source of reading (nvidia, amdgpu, etc.) |
| kWh_increment | REAL | Energy consumed since last reading |

### Table: `power_metadata`
| Column | Type | Description |
|--------|------|-------------|
| key | TEXT | 'total_kWh' or 'first_reading_time' |
| value | REAL | Stored value |

## History Query Calculation

When querying a time range, the system:

1. **First Interval**: Calculates from query start time to first reading
   - If previous reading exists: uses average of previous and first reading
   - If no previous: assumes constant power at first reading's value

2. **Middle Intervals**: Sums stored kWh_increment values (accurate)

3. **Last Interval**: Extrapolates from last reading to query end time
   - Assumes constant power at last reading's value

### Example Query
Query: 19:37:00 to 19:42:00 (5 minutes)
- First reading in range: 19:40:05 at 437W
- Energy 19:37:00 to 19:40:05: 185s × 437W = 0.0225 kWh
- Energy from readings: 0.0129 kWh
- Energy 19:41:50 to 19:42:00: 10s × 444W = 0.0012 kWh
- **Total: 0.0366 kWh**

## Accuracy Considerations

### Sources of Error
1. **Sampling Rate**: 15-second intervals miss sub-second power fluctuations
2. **Estimation**: CPU/RAM power is estimated, not measured
3. **Missing Components**: Motherboard, fans, drives not directly measured (~15-30W typical)
4. **Clock Drift**: System clock changes can affect interval calculations

### Error Mitigation
- Trapezoidal rule reduces error vs simple rectangular integration
- Capped interval time (max 1 hour) prevents errors from clock changes
- Database UNIQUE constraint prevents duplicate entries
- Recalculation from database on startup ensures consistency

### Expected Accuracy
- **With nvidia-smi**: ±5% (GPU is dominant power consumer under load)
- **Estimated only**: ±20% (rough estimate for systems without sensors)

## API Endpoints

### GET /api/power/current
Returns current power consumption and accumulated kWh since monitoring started.

### GET /api/power/total-kwh
Returns total accumulated kWh and first reading timestamp.

### GET /api/power/history?start_date=&end_date=
Returns energy statistics for a specific time period with accurate kWh calculation.

### WS /api/ws/power
Real-time power updates every 15 seconds.

## Persistence

### Data Storage
- SQLite database: `backend/power_logs.db`
- Automatic recalculation of total_kWh from database on startup
- Metadata table tracks accumulated totals

### Backup
```bash
cp backend/power_logs.db /backup/location/
```

### Data Retention
- Raw readings: Kept indefinitely (90 days recommended cleanup)
- Hourly aggregates: For fast historical queries
- Daily aggregates: For long-term trend analysis

## Verification

### Manual Verification
```python
# Sum of all kWh increments should equal total
SELECT SUM(kWh_increment) FROM power_readings;

# Verify first reading timestamp
SELECT MIN(timestamp) FROM power_readings;
```

### Expected Values
- 400W system running for 1 hour = 0.4 kWh
- 400W system running for 24 hours = 9.6 kWh
