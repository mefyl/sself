#!/usr/bin/env python3

import collections
import itertools
import os
import os.path
import requests
import subprocess
import sys
import time

class Configuration(collections.Mapping):

  def __init__(self, content):
    '''Load a Sself configuration.

    >>> cfg = Configuration("""
    ... domains:
    ...   www-infinit-sh:
    ...     hosts:
    ...     - infinit.sh.gruntech.org
    ...     port: 8080
    ...   www-mefyl-name:
    ...     hosts:
    ...     - mefyl.name
    ... """) #doctest: +ELLIPSIS
    >>> '{certbot[host]}:{certbot[port]}'.format(**cfg)
    'sself_certbot:80'
    >>> sorted(cfg['hostnames'])
    ['infinit.sh.gruntech.org', 'mefyl.name']
    '''
    import yaml
    self.__yaml = yaml.load(content)
    certbot = self.__yaml.setdefault('certbot', {})
    certbot.setdefault('host', 'sself_certbot')
    certbot.setdefault('port', 80)
    self.__yaml['hostnames'] = list(
      itertools.chain(*(s['hosts'] for s in self.__yaml['domains'].values())))

  def __getitem__(self, attr):
    return self.__yaml[attr]

  def __iter__(self):
    return iter(self.__yaml)

  def __len__(self):
    return len(self.__yaml)

def log(msg, **kwargs):
  print('{}: {}'.format(sys.argv[0], msg), **kwargs)

def run(cmd):
  log('running {}'.format(' '.join(cmd)))
  subprocess.check_call(cmd)

letsencrypt_template = '''\
server {{
  listen 80;
  server_name {hosts};
  access_log /dev/stdout;
  error_log /dev/stdout info;
  location ~ ^/.well-known {{
    proxy_pass http://{certbot[host]}:{certbot[port]};
  }}
  autoindex off;
  location = / {{
    return 301 https://$host$request_uri;
  }}
}}'''

service_template = '''\
server {{
  listen 443 ssl;
  server_name {hostname};
  access_log /dev/stdout;
  error_log /dev/stdout info;
  ssl_certificate /etc/letsencrypt/live/{hostname}/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/{hostname}/privkey.pem;
  location / {{
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto https;
    proxy_pass http://{backend}:{port};
  }}
}}'''

def main():
  with open('/etc/sself.yml') as f:
    cfg = Configuration(f)
  with open('/etc/nginx/conf.d/letsencrypt.conf', 'w') as f:
    print(letsencrypt_template.format(
      hosts = ' '.join(cfg['hostnames']),
      **cfg,
    ), file = f)
  nginx = subprocess.Popen(['nginx', '-g', 'daemon off;'])
  while True:
    for service, c in cfg['domains'].items():
      for h in c['hosts']:
        url = 'http://{}/.well-known'.format(h)
        while True:
          try:
            r = requests.get(url)
            if r.status_code == 200:
              break
          except requests.exceptions.RequestException as e:
            r = e
          log('waiting for {} to be up: {}'.format(url, r))
          time.sleep(5)
        for f in ['fullchain', 'privkey']:
          path = '{}/{}.pem'.format(h, f)
          r = requests.get(
            'http://{certbot[host]}:{certbot[port]}/{path}'.format(
              path = path,
              **cfg))
          if r.status_code != 200:
            raise Exception('unable to fetch {}: {}', path, r.content)
          fullpath = '/etc/letsencrypt/live/{}'.format(path)
          d = os.path.dirname(fullpath)
          if not os.path.exists(d):
            os.makedirs(d)
          with open(fullpath, 'wb') as o:
            o.write(r.content)
        with open('/etc/nginx/conf.d/{}.conf'.format(h), 'w') as f:
          print(service_template.format(
            hostname = h,
            backend = service,
            port = c.get('port', 80)), file = f)
    run(['nginx', '-s', 'reload'])
    try:
      exit(nginx.wait())
    except subprocess.TimeoutExpired:
      log('refreshing certificates')

if __name__ == "__main__":
  try:
    main()
  except Exception as e:
    log('fatal error: {}'.format(e), file = sys.stderr)
    exit(1)
