
[[_TOC_]]

# a2conf package content
- `a2conf` - python module to read/write apache2 config files
- `a2conf` - CLI script to query apache2 config (e.g. get DocumentRoot or get all hostnames for specific VirtualHost)
- `a2certbot.py` - CLI script to diagnose problems with Apache2 VirtualHost and LetsEncrypt certificates and make SSL sites easily
- `a2okerr.py` - CLI script to generate indicators for SSL VirtualHosts in [okerr](https://okerr.com/) monitoring system.


# Installation
Usual simple way:
~~~
pip3 install a2conf
~~~

or get sources from git repo:
~~~
git clone https://github.com/yaroslaff/a2conf.git
~~~
If using git sources (without installing), work from root dir of repo and do `export PYTONPATH=.`

# a2conf.Node class

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

`add(child)` - add new child node to content of Node after all other nodes (including possible closing 
Node `</VirtualHost>`). Child could be node or raw config line.

`insert(child, after)` - smarter then `add()`. Add new child node, place it after last node with name `after`. e.g.:
~~~
doc_root = Node(raw='DocumentRoot /var/www/site1')
vhost.insert([doc_root], after=['ServerName','ServerAlias'])
~~~

`child` is list of `Node`s to insert. But a2conf is friendly: if you pass single element, it will be converted to list with this element, and then if any element is string, it will be converted to node. So, this command woks well too:
~~~
vhost.insert('DocumentRoot /var/www/site1', after=['ServerName','ServerAlias'])
~~~

If `after` not specified, or not found, child is inserted before closing tag. If specified, method tries to insert new node
after last found node in `after`. 

In this example, new node will be inserted after `ServerAlias` (if it exists). If not, it will be inserted after `ServerName` (if it exists). And if all commands listed in `after` is not found, node will be inserted as last node, right before closing tag (e.g., right before `</VirtualHost>`).


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

### Add directives inside virtualhost
`examples/ex4_logfiles.py` check files from arguments, for each virtualhost if will add `CustomLog`/`ErrorLog` directives unless it already exists.

~~~python
#!/usr/bin/env python3

import sys
import a2conf

for path in sys.argv[1:]:
    print("FILE", path)
    root = a2conf.Node(path)

    for vhost in root.children('<VirtualHost>'):
        servername_cmd = vhost.first('servername')
        if servername_cmd is None:
            print("{}:{} No servername, skip".format(vhost.path, vhost.line))
            continue
        servername = servername_cmd.args
        print("{}:{} {}".format(vhost.path, vhost.line, servername))

        if vhost.first('CustomLog'):
            print("# has access log")
        else:
            print("# No access log, add")
            access_log_cmd = a2conf.Node(raw="CustomLog ${{APACHE_LOG_DIR}}/{}-access.log combined".format(servername))
            vhost.insert(access_log_cmd, after=['servername','serveralias'])

        if vhost.first('ErrorLog'):
            print("# has error log")
        else:
            print("# No error log, add")
            error_log_cmd = a2conf.Node(raw="ErrorLog ${{APACHE_LOG_DIR}}/{}-error.log".format(servername))
            vhost.insert(error_log_cmd, after=['servername','serveralias','customlog'])
    
    root.write_file(path)
~~~