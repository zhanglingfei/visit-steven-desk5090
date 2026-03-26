#!/bin/bash
# System monitoring watchdog script
# Run this via cron every minute to detect and report issues

LOG_FILE="/var/log/system_watchdog.log"
ALERT_FILE="/tmp/system_alert"

# Ensure log directory exists
touch "$LOG_FILE" 2>/dev/null || LOG_FILE="/tmp/system_watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check NVIDIA GPU
check_nvidia() {
    if command -v nvidia-smi &> /dev/null; then
        if ! nvidia-smi > /dev/null 2>&1; then
            ERROR=$(nvidia-smi 2>&1)
            if echo "$ERROR" | grep -q "Driver/library version mismatch"; then
                log "ALERT: NVIDIA driver version mismatch detected"
                echo "nvidia_driver_mismatch" > "$ALERT_FILE"
                return 1
            elif echo "$ERROR" | grep -q "Failed to initialize NVML"; then
                log "ALERT: NVIDIA NVML initialization failed"
                echo "nvidia_nvml_error" > "$ALERT_FILE"
                return 1
            fi
        fi
    fi
    return 0
}

# Check if backend service is running
check_backend() {
    if ! pgrep -f "uvicorn main:app" > /dev/null; then
        log "ALERT: Backend service not running"
        echo "backend_down" > "$ALERT_FILE"
        return 1
    fi
    return 0
}

# Check disk space
check_disk_space() {
    USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$USAGE" -gt 90 ]; then
        log "ALERT: Disk usage is ${USAGE}%"
        echo "disk_full" > "$ALERT_FILE"
        return 1
    fi
    return 0
}

# Main check
main() {
    ISSUES=0

    check_nvidia || ISSUES=$((ISSUES + 1))
    check_backend || ISSUES=$((ISSUES + 1))
    check_disk_space || ISSUES=$((ISSUES + 1))

    if [ $ISSUES -eq 0 ]; then
        # Clear alert file if all checks pass
        rm -f "$ALERT_FILE"
    fi

    return $ISSUES
}

main
exit $?
