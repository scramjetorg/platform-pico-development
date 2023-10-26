echo "Starting sth"
screen -d -m -S sthrpi bash -c "DEVELOPMENT=1 sth --runtime-adapter process -S ./sth-rpi4/sth-rpi4-config.json -E -D ./sth-rpi4/sequences"
sleep 4
echo "Starting to send throughput to topic"
screen -d -m -S throughput bash -c "cat /dev/urandom | pv -q -L 2M | si topic send -t "application/octet-stream" throughput"
