# Variables
IMAGE_TAG ?= v1.0.1
IMAGE_NAME ?= mayinuddinmunna/flask-app
KUBE_NAMESPACE ?= default

# Targets
all: build push deploy

build:
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@echo "Built $(IMAGE_NAME):$(IMAGE_TAG)"

push:
	docker push $(IMAGE_NAME):$(IMAGE_TAG)

deploy:
	kubectl apply -f deployment.yaml -f service.yaml --namespace $(KUBE_NAMESPACE)
	@echo "Deployed $(IMAGE_NAME):$(IMAGE_TAG) to namespace $(KUBE_NAMESPACE)"

clean:
	kubectl delete -f deployment.yaml -f service.yaml --namespace $(KUBE_NAMESPACE) || true

.PHONY: all build push deploy clean