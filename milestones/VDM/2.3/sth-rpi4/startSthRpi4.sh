#!/bin/bash

SCRIPT=$(realpath -s "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

timeout 1 bash -c '< /dev/tcp/192.168.0.5/8000'

if [ "$?" -ne 0 ] 
then
    echo "[Error] Pseudo-cloud STH on 192.168.0.5 not responding"
    exit 2
fi

if [ ! -f ~/.si/profiles/cloud.json ]
then
    echo "[Error] Profile 'cloud.json' for si do not exits"
    exit 3
fi

echo "Starting sth"
screen -d -m -S sthrpi bash -c "DEVELOPMENT=1 sth --runtime-adapter process -S ${SCRIPTPATH}/sth-rpi4-config.json -E -D ${SCRIPTPATH}/sequences"
sleep 10

echo "Starting to send throughput to topic"
si c pr use cloud
screen -d -m -S throughput bash -c "cat /dev/urandom | pv -q -L 2M | si topic send -t "application/octet-stream" throughput"
si c pr use default
