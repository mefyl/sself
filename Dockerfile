FROM alpine:latest AS base

RUN apk --no-cache add python3
ENV PYTHONUNBUFFERED=1


FROM base AS lb

RUN apk --no-cache add nginx py3-requests py3-yaml
RUN rm /etc/nginx/conf.d/default.conf
RUN mkdir /run/nginx
RUN chown nginx:nginx /run/nginx
ADD proxy.py /root/proxy.py
ENTRYPOINT /root/proxy.py


FROM base AS certbot

RUN apk --no-cache add certbot py3-bottle py3-pip
RUN pip3 install cherrypy
ADD renew /etc/periodic/daily/renew
RUN mkdir -p /var/www/letsencrypt/.well-known
ADD certbot /root/certbot
ENTRYPOINT /root/certbot
