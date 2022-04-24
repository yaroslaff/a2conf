# a2conf 
a2conf is python3 module which provides easy way to configure apache2. a2conf used by [a2utils](https://github.com/yaroslaff/a2utils) package, so you may use a2utils as examples.

For all examples we will use test config file `examples/example.conf` in source code. Use `export PYTHONPATH=.` to use module if it's not installed.

**Create simple apache config**

see examples/ex5_create.py for full code:
~~~python
vhost = root.insert('<VirtualHost *:80>')
vhost.insert([
        '# This VirtualHost is auto-generated',
        'ServerName example.com', 
        'ServerAlias www.example.com', 
        '', 
        'DocumentRoot /var/www/example.com/'
        ])
~~~

**Read apache config**

list all SSL hosts (see examples/ex2_query.py for full code):
~~~python
root = a2conf.Node(config)
for vhost in root.children('<VirtualHost>'):
    servername = vhost.first('servername').args # First query method, via first(). Not much fail-safe but short.

    try:
        ssl_option = next(vhost.children('sslengine')).args # Second query method, via children()
        if ssl_option.lower() == 'on':
            print("{} has SSL enabled".format(servername))
    except StopIteration:
        # No SSL Engine directive in this vhost
        pass
~~~

**Get VirtualHost**
~~~python
        root = a2conf.Node(config)
        vh1 = root.find_vhost('example.com', '*:80')
        vh2 = root.find_vhost('www.example.com', '*:443')
        vh3 = root.find_vhost('example.example.com')
~~~

## Node class

### Properties

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
Node `</VirtualHost>`). Child is Node type, use `add_raw(line)` to add raw string.

`insert(child, after)` - smarter then `add()`. Add new child node, place it after last node with name `after`. e.g.:
~~~
doc_root = Node(raw='DocumentRoot /var/www/site1')
vhost.insert([doc_root], after=['ServerName','ServerAlias'])
~~~

`child` is list of `Node`s to insert. But a2conf is friendly: if you pass single element, it will be converted to list with this element, and then if any element is string, it will be converted to node. So, this command woks well too:
~~~
vhost.insert('DocumentRoot /var/www/site1', after=['ServerName','ServerAlias'])
~~~

If `after` not specified, or not found, child is appended to end. If specified, method tries to insert new node
after last found node in `after`. 

In this example, new node will be inserted after `ServerAlias` (if it exists). If not, it will be inserted after `ServerName` (if it exists). And if all commands listed in `after` is not found, node will be inserted as last node, right before closing tag (e.g., right before `</VirtualHost>`).

Returns first inserted child. So you may write code like this:
~~~
# Create virtualhost for example.net
vhost = root.insert("<VirtualHost *:80>")
vhost.insert('ServerName example.net')
~~~

`delete()` - removes this Node from parent (e.g. remove vhost from apache config or remove directive from vhost). 
You should not call `delete()` while iterating over `children()` (unless you want to delete just one node). Proper usage:
~~~python
    # Bad way, it will delete only one node:
    for n in vhost.children('Redirect'):
        n.delete() 

    # Proper way
    deleted=list()
    for n in vhost.children('Redirect'):
        deleted.append(n)
    for n in deleted:
        n.delete()
~~~

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
