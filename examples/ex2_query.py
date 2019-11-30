#!/usr/bin/env python3
import sys
import a2conf
root = a2conf.Node(name='#root')
root.read_file(sys.argv[1])
for vhost in root.children(cmd = '<VirtualHost>'):
    servername = next(vhost.children('servername')).args
    try:
        ssl_option = next(vhost.children('sslengine')).args
        if ssl_option.lower() == 'on':
            print("{} has SSL enabled".format(servername))
    except StopIteration:
        # No SSL Engine directive in this vhost
        continue