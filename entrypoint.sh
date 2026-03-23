#!/bin/sh

PUID=${PUID:-1000}
PGID=${PGID:-1000}

if [ -n "$TZ" ]; then
    echo "Using configured timezone from TZ variable: $TZ"
else
    echo "Attempting geo-detection for timezone..."
    TZ=$(curl -s --max-time 3 https://ipapi.co/timezone || echo "Etc/UTC")
    echo "Selected timezone: $TZ"
fi

if [ -f "/usr/share/zoneinfo/$TZ" ]; then
    ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
    echo "$TZ" >/etc/timezone
    echo "Configured timezone: $TZ"
else
    echo "Warning: Invalid timezone '$TZ', falling back to UTC"
    ln -sf /usr/share/zoneinfo/Etc/UTC /etc/localtime
    echo "Etc/UTC" >/etc/timezone
    export TZ="Etc/UTC"
fi

if [ "$(getent group appgroup | cut -d: -f3)" != "$PGID" ]; then
    echo "Updating group appgroup GID to $PGID"
    groupmod -o -g "$PGID" appgroup
fi

if [ "$(id -u appuser)" != "$PUID" ]; then
    echo "Updating user appuser UID to $PUID"
    usermod -o -u "$PUID" -g "$PGID" appuser
fi

if [ ! -d /config ]; then
    echo "Creating /config directory"
    mkdir -p /config
fi

chown -R appuser:appgroup /config
cd /code

if [ "$APP_MODE" = "WEB" ]; then
    if [ "$FLASK_ENV" = "development" ]; then
        echo "Starting Flask in development mode as $PUID:$PGID"
        exec gosu appuser flask --app postarr:app run --host 0.0.0.0 --port=5000 --debug
    else
        gosu appuser python /code/migrate_db.py || {
            echo "Failed to migrate database. Exiting."
            exit 1
        }
        echo "Starting Gunicorn in production mode as $PUID:$PGID"
        exec gosu appuser gunicorn --timeout 1800 -w 1 -c gunicorn.conf.py -b 0.0.0.0:8000 postarr:app

    fi
else
    echo "Running main.py as $PUID:$PGID"
    exec gosu appuser python main.py
fi
