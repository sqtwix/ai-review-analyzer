#!/bin/sh
set -eu

# Named volumes can retain root ownership after an upgrade. Fix only the two
# dedicated writable mounts, then permanently drop privileges before .NET starts.
chown -R app:app /app/temp_uploads /home/app/.aspnet/DataProtection-Keys
# A container restart marks interrupted reports as failed in Program.cs, so
# their now-orphaned upload directories are safe to remove before serving.
find /app/temp_uploads -mindepth 1 -maxdepth 1 -exec rm -rf -- {} \;

exec setpriv \
    --reuid=app \
    --regid=app \
    --init-groups \
    --no-new-privs \
    "$@"
