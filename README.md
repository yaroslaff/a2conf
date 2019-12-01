a2conf is utility and python module to work with apache2 config files.

For all examples we will use file [example.conf](https://gitlab.com/yaroslaff/a2conf/raw/master/examples/example.conf)
which is available `examples/example.conf`. Use `export PYTHONPATH=.` to use module if it's not installed.

# a2conf.py utility
## Examples
Just smart grep
~~~shell
$ bin/a2conf examples/example.conf --cmd ServerName ServerAlias
ServerName example.com
ServerAlias www.example.com example.com 1.example.com 2.example.com
ServerName example.com
ServerAlias www.example.com 1.example.com 2.example.com secure.example.com

$ bin/a2conf examples/example.conf --cmd SSLCertificateFile
SSLCertificateFile /etc/letsencrypt/live/example.com/fullchain.pem
~~~

Only arguments:
~~~shell
# All arguments (including duplicates)
$ bin/a2conf examples/example.conf --cmd ServerName ServerAlias --args
example.com www.example.com example.com 1.example.com 2.example.com example.com www.example.com 1.example.com 2.example.com secure.example.com

# Only unique arguments
$ bin/a2conf examples/example.conf --cmd ServerName ServerAlias --uargs
secure.example.com 1.example.com www.example.com example.com 2.example.com
~~~

Filtering:
~~~shell
# Only SSL hosts. Note: secure.example.com listed
$ bin/a2conf examples/example.conf --cmd ServerName ServerAlias --uargs --filter sslengine on
1.example.com example.com secure.example.com 2.example.com www.example.com

# Inverted filtering, hosts without SSLEngine on. Note: secure.example.com not listed
$ bin/a2conf examples/example.conf --cmd ServerName ServerAlias --uargs --filter sslengine on --neg
example.com 2.example.com 1.example.com www.example.com
~~~

Per-vhost info:
~~~shell
# show documentroot for virtualhosts
$ bin/a2conf examples/example.conf  --cmd servername serveralias --uargs --vhost '{vhostargs} {servername} {documentroot}'
*:80 example.com /var/www/example
*:443 example.com /var/www/example

# ... only for virtualhosts with SSLEngine On
$ bin/a2conf examples/example.conf  --cmd servername serveralias --uargs --vhost '{vhostargs} {servername} {documentroot}' --filter sslengine on
*:443 example.com /var/www/example

# What certfile we use for secure.example.com ?
$ bin/a2conf examples/example.conf --vhost '{servername} {sslcertificatefile}' --filter ServerName,ServerAlias secure.example.com
example.com /etc/letsencrypt/live/example.com/fullchain.pem

# What certfile we use for 1.example.com (more good-style error-prone approach) ?
$ bin/a2conf examples/example.conf --vhost '{servername} {sslcertificatefile}' --filter ServerName,ServerAlias 1.example.com  --undef _skip
example.com /etc/letsencrypt/live/example.com/fullchain.pem
~~~
You can get list of all available tokens for `--vhost` option in verbose mode (`-v` option).

# Node class

## Properties and methods

`raw` - text line as-is, with all spaces, tabs and with comments

`cmd` - cmd ('ServerName') without args or None (if section)

`section` - section (e.g. 'VirtualHost')

`args` - one text line args to cmd or section. for vhost args could be '*:80', for ServerAlias: 'example.com example.org'

`name` - name of node. cmd if node has cmd, or section name (in brackets) if this is section. e.g. 'ServerName' or
'<VirtualHost>'

`content` - list of child nodes (possible empty). For container sections (VirtualHost) attribute `content` is list
 of children. For usual commands (e.g. ServerName) - empty list.


### Methods

`__init__(self, read=filename, raw=None, parent=None, name=None, path=None, line=None, includes=True)` - In most cases you should not need to use
any parameters here except `includes` and `read`. `read` is apache config filename to read. Use `includes=False` if you want `read_file` method to ignore `Include*` directives.

`children(name=None, recursive=None)` - Main query method, returns generator for all children  nodes (e.g. for VirtualHost node). Generator is empty if no
children. If name specified, generator will return only nodes with this name (e.g. 'servername' or '<VirtualHost>'). If recursive is On,
generator will return nested nodes too (e.g. what is inside `<IfModule>` or `<Directory>` settings). To get just one first element use
`next(node.children('ServerName'))`. It will raise `StopIteration` if node has no such children elements.

`first(name, recursive=None)` - wrapper for `children()`. Returns only first element or `None`. Not raising exceptions.

`read_file(filename)` - Reads apache config. Called automatically from `__init__` if you specified `read` argument.

`dump(fh=sys.stdout, depth=0)` - dump loaded config in unified format (indented). if fh not specified, just dumps to stdout()

`write_file(filename)` - opens file for writing and dump() to this file.

## Examples

### Just dump apache config
`examples/ex1_dump.py` just loads config and dumps its structure (without comments) as JSON:
~~~python
#!/usr/bin/env python3
import sys
import a2conf
import json

root = a2conf.Node(sys.argv[1])

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
~~~

Output:
~~~
$ examples/ex1_dump.py examples/example.conf
{
    "VirtualHost *:80": {
        "DocumentRoot": "/var/www/example",
        "ServerName": "example.com",
        "ServerAlias": "www.example.com example.com 1.example.com 2.example.com",
        "DirectoryIndex": "index.html index.htm default.htm index.php",
        "Options": "-Indexes +FollowSymLinks"
    },
    "VirtualHost *:443": {
        "DocumentRoot": "/var/www/example",
        "ServerName": "example.com",
        "ServerAlias": "www.example.com 1.example.com 2.example.com secure.example.com",
        "DirectoryIndex": "index.html index.htm default.htm index.php",
        "Options": "-Indexes +FollowSymLinks",
        "SSLEngine": "On",
        "SSLCertificateFile": "/etc/letsencrypt/live/example.com/fullchain.pem",
        "SSLCertificateKeyFile": "/etc/letsencrypt/live/example.com/privkey.pem",
        "SSLCertificateChainFile": "/etc/letsencrypt/live/example.com/chain.pem"
    }
}
~~~
Note - this is short example just for demo, it's not very good for production: if virtualhost has more then one directive
(e.g. `ServerAlias`, `RewriteRule`, `RewriteCond`), only last one will be used.


### Query
`examples/ex2_query.py` print all SSL sites from config:
```python
#!/usr/bin/env python3
import sys
import a2conf
root = a2conf.Node(sys.argv[1])

for vhost in root.children('<VirtualHost>'):
    servername = vhost.first('servername').args # One query method, via first(). Not much fail-safe but short.

    try:
        ssl_option = next(vhost.children('sslengine')).args # Other query method, via children()
        if ssl_option.lower() == 'on':
            print("{} has SSL enabled".format(servername))
    except StopIteration:
        # No SSL Engine directive in this vhost
        continue
```

Output:
```
$ examples/ex2_query.py examples/example.conf
example.com has SSL enabled
```

### Replace and delete
`examples/ex3_replace_delete.py` disables SSLEngine directive:
~~~python
#!/usr/bin/env python3
import sys
import a2conf
root = a2conf.Node(sys.argv[1])

for vhost in root.children('<VirtualHost>'):
    if vhost.first('sslengine'):
        vhost.delete() # Delete SSL vhost
    else:
        # Modify DocumentRoot
        vhost.first('DocumentRoot').args = '/var/www/example2'
        vhost.first('DocumentRoot').suffix = '# New DocumentRoot!'
        # Delete ServerAlias
        vhost.first('ServerAlias').delete()

root.dump()
~~~

Output:
~~~shell
$ examples/ex3_replace_delete.py examples/example.conf
#
# Example config file for a2conf
#
<VirtualHost *:80>
    # Non-ssl site
    DocumentRoot /var/www/example2 # New DocumentRoot!
    ServerName example.com # .... OUR TEST SITE ....
    DirectoryIndex index.html index.htm default.htm index.php
    Options -Indexes +FollowSymLinks
</VirtualHost>
~~~
