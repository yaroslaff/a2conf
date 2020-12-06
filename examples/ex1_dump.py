#!/usr/bin/env python3
import sys
import a2conf
import json
import os

try:
    config = sys.argv[1]
except IndexError:
    config = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'example.conf')

root = a2conf.Node(config)

def section_dump(node):
    data = dict()

    for ch in node.children():
        if ch.section and not ch.section.startswith('/'):
            if ch.args:
                key = ch.section + ' ' + ch.args
            else:
                key = ch.section
            data[key] = section_dump(ch)
        elif ch.cmd:
            data[ch.cmd] = ch.args
    return data

data = section_dump(root)
print(json.dumps(data, indent=4))