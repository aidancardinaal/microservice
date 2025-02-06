#!/bin/bash

git pull
cd experiment-consumer && faas-cli up -f experiment-consumer.yml && cd ..

docker build -t queue-controller queue-controller
docker build -t rest-api rest-api

kubectl delete -f infomcec-2024-g8.yml
kubectl apply -f infomcec-2024-g8.yml

