#!/usr/bin/env python3
import sys
import a2conf
root = a2conf.Node(sys.argv[1])

for vhost in root.children('<VirtualHost>'):
    servername = vhost.first('servername').args # One query method, via first(). Not much fail-safe but short.

    try:
        ssl_option = next(vhost.children('sslengine')).args # Other query method, via children()
        if ssl_option.lower() == 'on':
            print("{} has SSL enabled".format(servername))
    except StopIteration:
        # No SSL Engine directive in this vhost
        continue