#!/usr/bin/env python3

import a2conf
import argparse
import socket
import os
import okerrupdate

project = okerrupdate.OkerrProject()


def process_file(path, args):
    root = a2conf.Node(name='#root')
    root.read_file(path)

    for vhost in root.children('<VirtualHost>'):
        servername = next(vhost.children('servername')).args
        try:
            sslengine = next(vhost.children('sslengine'))
        except StopIteration:
            continue
        if sslengine.args.lower() != 'on':
            continue

        iname = args.prefix + servername
        i = project.indicator(iname,
                              method = 'sslcert|host={}|port=443|days=20'.format(servername),
                              policy = args.policy,
                              desc = args.desc)
        if args.dry:
            print(i,'(dry run)')
        else:
            print(i)

        if not args.dry:
            i.update('OK')


def main():

    def_prefix = socket.gethostname()+':ssl:https:'
    def_dir = '/etc/apache2/sites-enabled/'
    def_policy = 'Daily'
    def_desc = 'Auto-created from a2conf apache2okerr.py'

    parser = argparse.ArgumentParser(description='Bulk-add Apache2 SSL hosts to Okerr monitoring')

    parser.add_argument('-v', dest='verbose', action='store_true',
                        default=False, help='verbose mode')
    parser.add_argument('-d', '--dir', default=def_dir, metavar='DIR_PATH',
                        help='Directory with apache virtual sites. def: {}'.format(def_dir))
    parser.add_argument('-f', '--file', default=None, metavar='PATH',
                        help='One config file path')
    parser.add_argument('--prefix', default=def_prefix, metavar='PATH',
                        help='prefix (def: {})'.format(def_prefix))
    parser.add_argument('--policy', default=def_policy, metavar='Policy',
                        help='okerr policy (def: {})'.format(def_policy))
    parser.add_argument('--desc', default=def_desc, metavar='DESC',
                        help='description (def: {})'.format(def_desc))
    parser.add_argument('--dry', default=False, action='store_true',
                        help='dry run, do not update anything')

    args = parser.parse_args()

    if args.file:
        process_file(args.file, args)
    else:
        for f in os.listdir(args.dir):
            path = os.path.join(args.dir, f)
            if not (os.path.isfile(path) or os.path.islink(path)):
                continue
            process_file(path, args)

main()