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
    servername = vhost.first('servername').args # First query method, via first(). Not much fail-safe but short.

    try:
        ssl_option = next(vhost.children('sslengine')).args # Second query method, via children()
        if ssl_option.lower() == 'on':
            print("{} has SSL enabled".format(servername))
    except StopIteration:
        # No SSL Engine directive in this vhost
        continue