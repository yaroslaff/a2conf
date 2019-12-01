#!/usr/bin/env python3
import sys
import a2conf
root = a2conf.Node(sys.argv[1])

for vhost in root.children('<VirtualHost>'):
    if vhost.first('sslengine') is None:
        vhost.delete()

for alias in root.children('ServerAlias', recursive=True):
    alias.delete()
root.dump()