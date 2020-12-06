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
    servername_cmd = vhost.first('servername')
    if servername_cmd is None:
        print("{}:{} No servername, skip".format(vhost.path, vhost.line))
        continue
    servername = servername_cmd.args
    print("{}:{} {}".format(vhost.path, vhost.line, servername))

    if vhost.first('CustomLog'):
        print("# has access log")
    else:
        print("# No access log, add")
        access_log_cmd = a2conf.Node(raw="CustomLog ${{APACHE_LOG_DIR}}/{}-access.log combined".format(servername))
        vhost.insert(access_log_cmd, after=['servername','serveralias'])

    if vhost.first('ErrorLog'):
        print("# has error log")
    else:
        print("# No error log, add")
        error_log_cmd = a2conf.Node(raw="ErrorLog ${{APACHE_LOG_DIR}}/{}-error.log".format(servername))
        vhost.insert(error_log_cmd, after=['servername','serveralias','customlog'])

    root.dump()
    # root.write_file(path)