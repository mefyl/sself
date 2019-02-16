DOCKER_REPOSITORY :=
DOCKER_TAG := latest

all: image/lb image/certbot

check:
	python3 -m doctest -v proxy.py

image/%: Dockerfile
	docker build . --target $(notdir $@) --tag $(DOCKER_REPOSITORY)$(notdir $@):$(DOCKER_TAG)

image/nginx-proxy:
image/certbot:

image/ci:
	docker build . -f Dockerfile.ci --tag registry.gitlab.gruntech.org/mefyl/sself/ci
