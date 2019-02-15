DOCKER_REPOSITORY :=

all: image/sself-lb image/sself-certbot

image/%: Dockerfile
	docker build . --target $(notdir $@) --tag $(DOCKER_REPOSITORY)$(notdir $@)

image/nginx-proxy:
image/certbot:
