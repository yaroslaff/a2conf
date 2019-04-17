# Testing environment:
~~~
$ cat /etc/apache2/sites-enabled/example.conf 
<VirtualHost *:80>
	DocumentRoot /var/www/example
	ServerName example.com
	ServerAlias www.example.com 1.example.com 2.example.com
	DirectoryIndex index.html index.htm default.htm index.php
	Options -Indexes +FollowSymLinks
</VirtualHost>
~~~

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
children,

## Examples
Reading
~~~
root.read_file('/etc/apache2/sites-available/example.conf')
def recdump(node, prefix=""):
    if node.section:
        print(prefix, "SECTION", node.section, "ARGS", node.args, "CONTENT", len(node.content))
    else:
        print(prefix, repr(node.cmd), repr(node.args))
    for ch in node.children():
        recdump(ch, prefix+"  ")
recdump(root)
~~~

Output:
~~~
 None None
   SECTION VirtualHost ARGS *:80 CONTENT 5
     'DocumentRoot' '/var/www/example'
     'ServerName' 'example.com'
     'ServerAlias' 'www.example.com 1.example.com 2.example.com'
     'DirectoryIndex' 'index.html index.htm default.htm index.php'
     'Options' '-Indexes +FollowSymLinks'
~~~
