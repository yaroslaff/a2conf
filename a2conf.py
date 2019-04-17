#!/usr/bin/env python3

import argparse
import apache2conf

parser = argparse.ArgumentParser(description='Apache config parser')
parser.add_argument('-i', '--infile', help='input filename')
parser.add_argument('--cmd', default=list(), nargs='*', help='show all this commands', type=str.lower)
parser.add_argument('--args', default=False, action='store_true', help='show only arguments')

args = parser.parse_args()

if not args.infile:
    print("Need -i <filename>")
    exit()

# read file
root = apache2conf.Node(name='#root')
parent = root

root.read_file(args.infile)

arglist = list()

if args.cmd:
    for vhost in root.all_nodes():
        if vhost.section and vhost.section.lower() == 'virtualhost':
            names = list()
            for cnode in vhost.children():
                if cnode.cmd.lower() in args.cmd:
                    if args.args:
                        # process only args
                        arglist.extend(filter(None, cnode.args.split(" ")))
                    else:
                        print(cnode.cmd, cnode.args)
    if args.args:
        print(' '.join(arglist))

