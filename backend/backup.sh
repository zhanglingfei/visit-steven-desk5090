#!/bin/bash
# Backup script for visit-steven-desk5090 data
# Run daily via cron

BACKUP_DIR="/home/steven-desk5090/visit-steven-desk5090/backups"
DATA_DIR="/home/steven-desk5090/visit-steven-desk5090/backend"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup filename
BACKUP_FILE="$BACKUP_DIR/backup_${DATE}.tar.gz"

# Create backup
tar -czf "$BACKUP_FILE" \
    -C "$DATA_DIR" \
    power_logs.db \
    security.db \
    users.json \
    logs/ \
    2>/dev/null

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "[$(date)] Backup created: $BACKUP_FILE"
    echo "Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
else
    echo "[$(date)] Backup FAILED"
    exit 1
fi

# Clean up old backups (keep last 30 days)
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# List recent backups
echo "Recent backups:"
ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -5
