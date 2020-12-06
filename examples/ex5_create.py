#!/usr/bin/python3

from a2conf import Node

root = Node()
vhost = root.insert('<VirtualHost *:80>')
vhost.insert([
    '# This VirtualHost is auto-generated',
    'ServerName example.com', 
    'ServerAlias www.example.com', 
    '', 
    'DocumentRoot /var/www/example.com/'])

root.dump()
# root.write_file('/tmp/example.com.conf')

