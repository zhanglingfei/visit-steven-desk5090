# Power Monitoring System - Debug Reference

## Overview
This document summarizes the key issues encountered and fixed during the development of the power monitoring system, serving as a reference for future maintenance.

---

## Issue 1: Fake Energy for Future/Empty Date Ranges

### Problem
Querying date ranges outside the monitoring period returned inflated energy values (e.g., 534 kWh for a 51-day period with only ~1 hour of data).

### Root Cause
The `get_power_history()` function was:
1. Calculating energy from query start to first reading (extrapolation)
2. Extrapolating from last reading to query end
3. Not capping calculations at current time

### Solution
```python
# Only calculate energy for actual data periods
def get_power_history(start_timestamp, end_timestamp):
    # ... get readings ...

    # Sum only stored kWh increments for readings in range
    total_kwh = sum(r[2] for r in readings)

    # Cap at current time
    current_time = time.time()
    effective_end = min(end_timestamp, current_time)

    # Calculate actual data span, not query span
    data_span_start = max(actual_data_start, start_timestamp)
    data_span_end = min(min(actual_data_end, end_timestamp), current_time)
    actual_hours_span = max(0, (data_span_end - data_span_start) / 3600)
```

---

## Issue 2: Timezone Confusion (JST vs UTC)

### Problem
Monitoring appeared to start on "2026-03-26" when it actually started on "2026-03-25 19:40 JST".

### Root Cause
Double timezone conversion:
- Database stores UTC timestamps
- Incorrectly added 9 hours twice when converting to JST

### Solution
```python
# Correct JST conversion
first_utc = datetime.fromtimestamp(min_ts, tz=timezone.utc)
first_jst = first_utc + timedelta(hours=9)  # Single conversion

# NOT: first_jst = first_utc + timedelta(hours=9) + timedelta(hours=9)
```

---

## Issue 3: Frontend Date Parsing Errors

### Problem
Frontend datetime-local input handling caused incorrect timestamps to be sent to API.

### Root Cause
1. `datetime-local` input returns local system time
2. `new Date(string)` treats input as local time on JST systems
3. Double subtraction of timezone offset caused 9-hour errors

### Solution
```typescript
// Correct approach - let browser handle local time
function parseLocalInputToUTC(localString: string): Date {
  // new Date('2026-03-25T17:33') treats as local (JST)
  // Resulting Date object has correct UTC timestamp
  return new Date(localString);
}

// Format for datetime-local input (accounts for local timezone)
function formatDateToInput(date: Date): string {
  const tzOffset = date.getTimezoneOffset() * 60 * 1000;
  const localDate = new Date(date.getTime() - tzOffset);
  return localDate.toISOString().slice(0, 16);
}
```

---

## Issue 4: First Reading kWh Increment Logic

### Problem
When querying from before monitoring start, the first reading's `kWh_increment` (energy from previous reading) was incorrectly included.

### Root Cause
Each reading's `kWh_increment` represents energy from the **previous** reading to current reading. The first reading in a query range may have its interval partially outside the query range.

### Solution
```python
# Only include first reading's kWh_increment if previous reading is in range
if prev_reading:
    prev_ts = prev_reading[0]
    if prev_ts >= start_timestamp:
        # Previous reading is in range, include first reading's increment
        total_kwh = sum(r[2] for r in readings)
    else:
        # Previous reading is before query start, exclude first reading's increment
        total_kwh = sum(r[2] for r in readings[1:])
else:
    # No previous reading (first ever reading), its kWh_increment is 0 anyway
    total_kwh = sum(r[2] for r in readings)
```

---

## Issue 5: Browser Cache Showing Stale Data

### Problem
After fixing backend, frontend still displayed old incorrect values.

### Root Cause
React state not cleared between queries; browser cached API responses.

### Solution
```typescript
const handleQuery = async () => {
  setLoading(true);
  setError(null);
  setResult(null);        // Clear previous result
  setChartData([]);       // Clear previous chart
  // ... perform query ...
};
```

Also: Force browser refresh (Ctrl+F5) after backend changes.

---

## Key Design Principles

### 1. Store Only Actual Measurements
- Never extrapolate or estimate energy
- Each `kWh_increment` represents measured energy between two readings
- Sum only actual stored increments

### 2. Timezone Handling
- Database: Always store UTC timestamps
- Backend: Use timezone-aware datetime objects
- Frontend: Let browser handle local time; send ISO strings to API
- Display: Convert to JST for Japanese users

### 3. Query Range vs Data Range
- `hours_span` should reflect actual data coverage, not query range
- Cap all calculations at current time
- Return 0 kWh for periods with no data

### 4. First/Last Interval Handling
- First reading's `kWh_increment` represents interval BEFORE the reading
- Only include if that interval falls within query range
- Never extrapolate beyond available data

---

## Testing Checklist

- [ ] Query before monitoring start → Returns 0 kWh
- [ ] Query after monitoring end → Returns 0 kWh
- [ ] Query spanning monitoring period → Returns correct partial sum
- [ ] Query exact monitoring period → Returns total kWh
- [ ] Future dates → Rejected with error
- [ ] Timezone conversion → JST displays correctly
- [ ] Browser refresh → Shows updated data

---

## Common Pitfalls

1. **Double timezone conversion**: Adding/subtracting offset twice
2. **Naive vs Aware datetime**: Mixing timezone-aware and naive datetime objects
3. **Extrapolation**: Calculating energy for periods without measurements
4. **Cache issues**: Not clearing state or browser cache after fixes
5. **Interval semantics**: Forgetting that `kWh_increment` belongs to interval BEFORE timestamp

---

## File Locations

- Backend logic: `backend/app/services/power_service.py`
- API endpoints: `backend/app/routers/power.py`
- Frontend page: `frontend/src/pages/PowerHistoryPage.tsx`
- Database: `backend/power_logs.db` (SQLite)

---

## Related Documentation

- `POWER_MONITORING.md` - Technical documentation
- `backend/app/models/power.py` - Data models
- `frontend/src/types/power.ts` - TypeScript types
