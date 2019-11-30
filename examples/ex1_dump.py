#!/usr/bin/env python3
import sys
import a2conf
root = a2conf.Node(name='#root')
root.read_file(sys.argv[1])
def recdump(node, prefix=""):
    if node.section:
        print(prefix, "SECTION", node.section, "ARGS", node.args, "CONTENT", len(node.content))
    elif node.cmd:
            print(prefix, repr(node.cmd), repr(node.args))
    for ch in node.children():
        recdump(ch, prefix+"  ")
recdump(root)
