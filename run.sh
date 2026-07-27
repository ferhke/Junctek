#!/usr/bin/with-contenv bashio

# nginx -g "daemon off;error_log /dev/stdout debug;" &

bashio::log.info "Starting Python"

python3 -m venv /data/venv
source /data/venv/bin/activate

bashio::log.info "Checking prerequisites"
if [ ! -f /data/pip ]; then
    bashio::log.info "Installing prerequisites"

    python3 -m ensurepip --upgrade >/dev/null

    pip install --upgrade bleak requests paho.mqtt colorlog >/dev/null

    echo "pip done" > /data/pip
fi

bashio::log.info "Starting Script..."

exec python3 -u scripts/main.py

bashio::log.info Script finished

