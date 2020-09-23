#!/usr/bin/python3

from a2conf import Node
import argparse
import sys
import os


#
# subroutines
#
def get_all_hostnames(vhost):
    names = list()
    try:
        servername = next(vhost.children('ServerName')).args
        names.append(servername)
    except StopIteration:
        pass

    for alias in vhost.children('ServerAlias'):
        names.extend(alias.args.split(' '))
    return names

def get_vhost_by_host(root, host, arg=None):
    for vhost in root.children('<VirtualHost>'):
        if arg and not arg in vhost.args:
            continue
        if host in get_all_hostnames(vhost):
            return vhost
    

#
# methods
#

def list_vhosts(apacheconf):
    root = Node(apacheconf)
    for vhost in root.children('<VirtualHost>'):

        hostnames = get_all_hostnames(vhost)

        docroot = vhost.first('DocumentRoot').args 
        print(vhost.path+':'+str(vhost.line), vhost.args, docroot, ' '.join(hostnames))

def make_basic(apacheconfig, config,  domainlist, webroot):
    # sanity check 
    if not domainlist:
        print("Specify at least one domain name: -d example.com")
        sys.exit(1)
    if not config:
        print("Specify virtualhostconfig file, e.g. -c /etc/apache2/sites-available/{}.conf".format(domainlist[0]))
        sys.exit(1)
    if not webroot:
        print("Need webroot (DocumentRoot) path, e.g.: -w /var/www/{}".format(domainlist[0]))

    # check maybe it exists
    root = Node(apacheconfig)
    for vhost in root.children('<VirtualHost>'):
        vhnames = get_all_hostnames(vhost)
        for host in domainlist:
            if host in vhnames:
                print("Problem: host {} found in vhost {}:{}".format(host, vhost.path, vhost.line))
                sys.exit(1)

    # Good, now, create it finally!
    if os.path.exists(config):
        root = Node(config)
        root.insert('')
    else:
        root = Node()

    new_vhost=Node(raw='<VirtualHost *:80>')
    new_vhost.insert('ServerName {}'.format(domainlist[0]))
    if len(domainlist) > 1:
        new_vhost.insert('ServerAlias {}'.format(' '.join(domainlist[1:])))
    new_vhost.insert('DocumentRoot {}'.format(webroot))
    new_vhost.insert('</VirtualHost>')

    root.insert(new_vhost, after=vhost)
    root.write_file(config)


def make_convert(apacheconfig, domainlist):
    # sanity check 
    if not domainlist:
        print("Specify at least one domain name: -d example.com")
        sys.exit(1)

    # check maybe SSL host already exists
    root = Node(apacheconfig)
    for vhost in root.children('<VirtualHost>'):
        if not ':443' in vhost.args:
            continue
        vhnames = get_all_hostnames(vhost)
        for host in domainlist:
            if host in vhnames:
                print("Problem: host {} found in vhost {}:{}".format(host, vhost.path, vhost.line))
                sys.exit(1)

    # get proper root node
    # stage 1: start from main config, e.g. /etc/apache2/apache2.conf
    root = Node(apacheconfig)
    root = Node(get_vhost_by_host(root, domainlist[0], ':80').path)
    vhost = get_vhost_by_host(root, domainlist[0], ':80')
    
    # make block and insert it!
    ssl_block = [
        '',
        'SSLEngine On',
        'SSLCertificateFile /etc/letsencrypt/live/{}/fullchain.pem'.format(domainlist[0]),
        'SSLCertificateKeyFile /etc/letsencrypt/live/{}/privkey.pem'.format(domainlist[0]),
        'Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"'
    ]

    vhost.insert(ssl_block, after='DocumentRoot')
    vhost_args = vhost.args

    vhost.args = vhost.args.replace(':80',':443')    
    root.write_file(root.path)

def make_redirect(apacheconfig, domainlist):
    # sanity check 
    if not domainlist:
        print("Specify at least one domain name: -d example.com")
        sys.exit(1)

    # check maybe SSL host already exists
    root = Node(apacheconfig)
    for vhost in root.children('<VirtualHost>'):
        if not ':80' in vhost.args:
            continue
        vhnames = get_all_hostnames(vhost)
        for host in domainlist:
            if host in vhnames:
                print("Problem: host {} found in vhost {}:{}".format(host, vhost.path, vhost.line))
                sys.exit(1)

    # get proper root node
    root = Node(apacheconfig)
    root = Node(get_vhost_by_host(root, domainlist[0], ':443').path)
    vhost = get_vhost_by_host(root, domainlist[0], ':443')
    servername = vhost.first('servername')
    documentroot = vhost.first('documentroot')

    new_vhost=Node(raw='<VirtualHost *:80>')
    new_vhost.insert(servername)
    for alias in vhost.children('serveralias'):
        new_vhost.insert(alias)
    new_vhost.insert(documentroot)
    
    new_vhost.insert('RewriteEngine On')
    new_vhost.insert('RewriteCond %{HTTPS} !=on')
    new_vhost.insert('RewriteCond %{REQUEST_URI} !^/\.well\-known')
    new_vhost.insert('RewriteRule (.*) https://%{SERVER_NAME}$1 [R=301,L]')
    new_vhost.insert('</VirtualHost>')

    root.insert(['', '# auto-generated plain HTTP site for redirect', new_vhost], after=vhost)
    root.write_file(root.path)



def main():

    def_apacheconf = '/etc/apache2/apache2.conf'

    parser = argparse.ArgumentParser(description='Apache2 CLI vhost manager')

    g = parser.add_argument_group('Commands')
    g.add_argument('--list', default=False, action='store_true',
                   help='List VirtualHosts')
    g.add_argument('--basic', default=False, action='store_true',
                   help='Create basic HTTP site (use: -c and --domain, --webroot)')
    g.add_argument('--convert', default=False, action='store_true',
                   help='Convert HTTP --domain site to HTTPS')
    g.add_argument('--redirect', default=False, action='store_true',
                   help='Create HTTP --domain redirect vhost to HTTPS')

    g = parser.add_argument_group('Options')
    g.add_argument('-a', '--apacheconfig', default=def_apacheconf, metavar='CONF',
                   help='Main apache config file. def: {}'.format(None))
    g.add_argument('-c', '--config', default=None, metavar='VHOST_CONF',
                   help='VirtualHost config file.')
    g.add_argument('-w', '--webroot', default=None, metavar='PATH',
                   help='Webroot (DocumentRoot) for new site')
    g.add_argument('-d', '--domain', nargs='*', metavar='DOMAIN', help='hostname/domain(s) for new website')


    args = parser.parse_args()

    if args.list:
        list_vhosts(args.apacheconfig)
    elif args.basic:
        make_basic(args.apacheconfig, args.config,  args.domain, args.webroot)
    elif args.convert:
        make_convert(args.apacheconfig, args.domain)
    elif args.redirect:
        make_redirect(args.apacheconfig, args.domain)

main()