#!/usr/bin/env python3
import sys
import os
import a2conf

try:
    config = sys.argv[1]
except IndexError:
    config = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'example.conf')

root = a2conf.Node(config)

for vhost in root.children('<VirtualHost>'):
    if vhost.first('sslengine'):
        vhost.delete() # Delete SSL vhost
    else:
        # Modify DocumentRoot
        vhost.first('DocumentRoot').args = '/var/www/example2'
        vhost.first('DocumentRoot').suffix = '# New DocumentRoot!'
        # Delete ServerAlias
        vhost.first('ServerAlias').delete()

root.dump()