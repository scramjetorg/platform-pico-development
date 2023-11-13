#!/bin/bash

if [ ! -f /tmp/noise.wav ]
then
    echo "[Error] Noise pattern file not found. Copy to: /tmp/noise.wav"
    exit 3
fi

echo "Starting sth"
screen -d -m -S sth bash -c "DEVELOPMENT=1 sth --runtime-adapter process -S ./sth-cloud/sth-cloud-config.json -E -D ./sth-cloud/sequences"
sleep 10
echo "Creating topic"
si topic create -t "application/octet-stream" throughput
sleep 1
echo "Connecting to topic output"
screen -d -m -S topic bash -c "si topic get throughput -t "application/octet-stream""
