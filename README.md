a2conf is utility and python module to work with apache2 config files

# Testing environment:
~~~
<VirtualHost *:80>
	DocumentRoot /var/www/example
	ServerName example.com  # .... OUR TEST SITE ....
	ServerAlias www.example.com 1.example.com 2.example.com
	DirectoryIndex index.html index.htm default.htm index.php
	Options -Indexes +FollowSymLinks
</VirtualHost>

<VirtualHost *:443>
	DocumentRoot /var/www/example
	ServerName example.com  # .... OUR TEST SITE ....
	ServerAlias www.example.com 1.example.com 2.example.com secure.example.com
	DirectoryIndex index.html index.htm default.htm index.php
	Options -Indexes +FollowSymLinks

	SSLEngine On
	SSLCertificateFile /etc/letsencrypt/live/example.com/fullchain.pem
    	SSLCertificateKeyFile /etc/letsencrypt/live/example.com/privkey.pem
    	SSLCertificateChainFile /etc/letsencrypt/live/example.com/chain.pem
</VirtualHost>
~~~

# a2conf.py 
## Examples
Just smart grep
~~~
$ ./a2conf.py -i /etc/apache2/sites-enabled/example.conf --cmd ServerName Serveralias
ServerName example.com
ServerAlias www.example.com 1.example.com 2.example.com
ServerName example.com
ServerAlias www.example.com 1.example.com 2.example.com secure.example.com

$ ./a2conf.py -i /etc/apache2/sites-enabled/example.conf --cmd SSLCertificateFile
SSLCertificateFile /etc/letsencrypt/live/example.com/fullchain.pem
~~~

Only arguments (one line, space-separated, non-unique):
~~~
./a2conf.py -i /etc/apache2/sites-enabled/example.conf --cmd ServerName Serveralias --args
example.com www.example.com 1.example.com 2.example.com example.com www.example.com 1.example.com 2.example.com secure.example.com
~~~

Unique arguments:
~~~
$ ./a2conf.py -i /etc/apache2/sites-enabled/example.conf --cmd ServerName Serveralias --uargs
www.example.com secure.example.com 2.example.com example.com 1.example.com
~~~

Filtering sections
~~~
./a2conf.py -i /etc/apache2/sites-enabled/example.conf --cmd servername serveralias --filter sslengine on
ServerName example.com
ServerAlias www.example.com 1.example.com 2.example.com secure.example.com
~~~

Can add `--neg` (`--negative`) to invert filtering

Per-vhost info
~~~
$ bin/a2conf -i /etc/apache2/sites-enabled/example.conf  --cmd servername serveralias --uargs --vhost '{vhostargs} {args}'
*:80 example.com www.example.com example.com 1.example.com 2.example.com
*:443 example.com www.example.com 1.example.com 2.example.com secure.example.com
~~~

You can get list of all available tokens with `-v`.

# Node class

## Properties and methods

**raw** - text line as-is, with all spaces, tabs and with comments

**cmd** - cmd ('ServerName') without args or None (if section)

**section** - section (e.g. 'VirtualHost')

**args** - one text line args to cmd or section. for vhost args could be '*:80', for ServerAlias: 'example.com example.org'

### Structure
For container sections (VirtualHost) attr content is not None. For usual lines (ServerName) content is None

**content** - list of child nodes or None

**children()** - return generator for all children  nodes (e.g. for VirtualHost node). Generator is empty if no
children

## Limitations
Any 'Include*' directives are not supported for now.

## Examples
For example, we will use example config file `examples/example.conf` with two virtual sites, one plain HTTP,
other is HTTPS.


### Just dump apache config
`examples/ex1_dump.py` just loads config and dumps its structure:
~~~
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
~~~

Output:
~~~
xenon@braconnier:~/repo/a2conf$ examples/ex1_dump.py examples/example.conf
   SECTION VirtualHost ARGS *:80 CONTENT 6
     'DocumentRoot' '/var/www/example'
     'ServerName' 'example.com'
     'ServerAlias' 'www.example.com example.com 1.example.com 2.example.com'
     'DirectoryIndex' 'index.html index.htm default.htm index.php'
     'Options' '-Indexes +FollowSymLinks'
   SECTION VirtualHost ARGS *:443 CONTENT 9
     'DocumentRoot' '/var/www/example'
     'ServerName' 'example.com'
     'ServerAlias' 'www.example.com 1.example.com 2.example.com secure.example.com'
     'DirectoryIndex' 'index.html index.htm default.htm index.php'
     'Options' '-Indexes +FollowSymLinks'
     'SSLEngine' 'On'
     'SSLCertificateFile' '/etc/letsencrypt/live/example.com/fullchain.pem'
     'SSLCertificateKeyFile' '/etc/letsencrypt/live/example.com/privkey.pem'
     'SSLCertificateChainFile' '/etc/letsencrypt/live/example.com/chain.pem'
~~~

### Query
`examples/ex2_query.py` print all SSL sites from config:
~~~
#!/usr/bin/env python3
import sys
import a2conf
root = a2conf.Node(name='#root')
root.read_file(sys.argv[1])
for vhost in root.children(cmd = '<VirtualHost>'):
    servername = next(vhost.children('servername')).args
    try:
        ssl_option = next(vhost.children('sslengine')).args
        if ssl_option.lower() == 'on':
            print("{} has SSL enabled".format(servername))
    except StopIteration:
        # No SSL Engine directive in this vhost
        continue
~~~

Output:
~~~
xenon@braconnier:~/repo/a2conf$ examples/ex2_query.py examples/example.conf
example.com has SSL enabled
~~~