minikube start

minikube addons enable registry

docker run -d --rm -it --network=host alpine ash -c "apk add socat && socat TCP-LISTEN:5000,reuseaddr,fork TCP:$(minikube ip):5000"

kubectl port-forward -n openfaas svc/gateway 8080:8080 >/dev/null 2>&1 & disown

