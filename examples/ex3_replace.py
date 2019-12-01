#!/usr/bin/env python3
import sys
import a2conf
root = a2conf.Node(sys.argv[1])
for ssl in root.children('SSLEngine', recursive=True):
    ssl.args = "Off"
root.dump()