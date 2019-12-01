#!/usr/bin/env python3
import sys
import a2conf
root = a2conf.Node(sys.argv[1])

for vhost in root.children('<VirtualHost>'):
    if vhost.first('sslengine'):
        vhost.delete()
    else:
        vhost.first('DocumentRoot').args = '/var/www/example2'
        vhost.first('DocumentRoot').suffix = '# New DocumentRoot!'
        vhost.first('ServerAlias').delete()

root.dump()