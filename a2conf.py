#!/usr/bin/env python3

import argparse
import apache2conf

parser = argparse.ArgumentParser(description='Apache config parser')
parser.add_argument('-i', '--infile', help='input filename')
parser.add_argument('--cmd', default=list(), nargs='*', help='show all these commands', type=str.lower)
parser.add_argument('--filter', nargs=2, metavar=('Command','Argument'),
                    help='Process only sections with this command/argument', type=str.lower)
parser.add_argument('--args', default=False, action='store_true', help='show only arguments')
parser.add_argument('--uargs', default=False, action='store_true', help='show only unique arguments')

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
            # skip or process?
            if args.filter:
                process = False
                for checknode in vhost.get_nodes_cmd(args.filter[0]):
                    arglist = checknode.args.split(' ')
                    if args.filter[1].lower() in map(str.lower, arglist):
                        process = True

                # filter failed
                if not process:
                    continue

            for cnode in vhost.children():
                if cnode.cmd.lower() in args.cmd:
                    if args.args or args.uargs:
                        # process only args
                        arglist.extend(filter(None, cnode.args.split(" ")))
                    else:
                        print(cnode.cmd, cnode.args)

    if args.args:
        print(' '.join(arglist))

    if args.uargs:
        uargs = set(arglist)
        print(' '.join(uargs))


