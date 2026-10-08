#!/bin/bash
# AEF HRM — Daily backup to OneDrive
set -euo pipefail

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/tmp/hrm_backup_${DATE}"
LOG=/var/log/hrm_backup.log
RCLONE_REMOTE="onedrive:HRM-Backups"
MEDIA_DIR=/var/www/hrm/media

echo "[$(date)] Starting backup..." >> "$LOG"
mkdir -p "$BACKUP_DIR"

# 1. Database dump
PGPASSWORD="HrmDb2024!" pg_dump -U hrmuser -h localhost hrmdb -Fc \
  -f "$BACKUP_DIR/db_${DATE}.dump" \
  && echo "[$(date)] DB dump OK" >> "$LOG" \
  || { echo "[$(date)] DB dump FAILED" >> "$LOG"; exit 1; }

# 2. Media files archive
tar -czf "$BACKUP_DIR/media_${DATE}.tar.gz" -C /var/www/hrm media \
  && echo "[$(date)] Media archive OK" >> "$LOG" \
  || echo "[$(date)] Media archive FAILED (non-fatal)" >> "$LOG"

# 3. Upload to OneDrive
rclone copy "$BACKUP_DIR" "$RCLONE_REMOTE/${DATE}" \
  --log-level INFO --log-file "$LOG" \
  && echo "[$(date)] Upload to OneDrive OK" >> "$LOG" \
  || { echo "[$(date)] Upload FAILED" >> "$LOG"; exit 1; }

# 4. Clean up temp files
rm -rf "$BACKUP_DIR"
echo "[$(date)] Temp files cleaned" >> "$LOG"

# 5. Remove backups older than 30 days
rclone delete "$RCLONE_REMOTE" --min-age 30d --rmdirs >> "$LOG" 2>&1 || true

echo "[$(date)] Backup complete." >> "$LOG"
