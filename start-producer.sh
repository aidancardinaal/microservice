#!/bin/bash

script=$(basename "$0")

docker run \
	--rm \
	-v ./queue-controller/auth:/app/experiment-producer/auth \
	-v ./config.json:/app/experiment-producer/config.json \
	dclandau/cec-experiment-producer \
	--topic group8 \
	--brokers 13.60.146.188:19093 \
	--config-file /app/experiment-producer/config.json

 
