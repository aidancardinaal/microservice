docker run -d --rm -it --network=host alpine ash -c "apk add socat && socat TCP-LISTEN:3003,reuseaddr,fork TCP:$(minikube ip):30003"
docker run -d --rm -it --network=host alpine ash -c "apk add socat && socat TCP-LISTEN:3010,reuseaddr,fork TCP:$(minikube ip):30432"
