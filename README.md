# a2conf package content
- `a2conf` - python module to read/write apache2 config files
- `a2conf` - CLI script to query apache2 config (e.g. get DocumentRoot or get all hostnames for specific VirtualHost)
- `a2certbot.py` - CLI script to diagnose problems with Apache2 VirtualHost and LetsEncrypt certificates
- `a2okerr.py` - CLI script to generate indicators for SSL VirtualHosts in [okerr](https://okerr.com/) monitoring system.


# Installation
Usual simple way:
~~~
pip3 install a2conf
~~~

or get sources from git repo:
~~~
git clone https://gitlab.com/yaroslaff/a2conf.git
~~~
If using git sources (without installing), work from root dir of repo and do `export PYTONPATH=.`


# CLI utilities
## a2conf.py utility
### Examples

For all examples we will use file 
[examples/example.conf](https://gitlab.com/yaroslaff/a2conf/raw/master/examples/example.conf).
You can omit this parameter to use default `/etc/apache2/apache2.conf`.

Use `export PYTHONPATH=.` to use module if it's not installed.

Most useful examples:
~~~shell
$ bin/a2conf examples/example.conf --dump --vhost secure.example.com 
# examples/example.conf:15
<VirtualHost *:443> 
    # SSL site
    DocumentRoot /var/www/example 
    ServerName example.com # .... OUR TEST SITE ....
    ServerAlias www.example.com 1.example.com 2.example.com secure.example.com 
    DirectoryIndex index.html index.htm default.htm index.php 
    Options -Indexes +FollowSymLinks 
    SSLEngine On # SSL Enabled for this virtual host
    SSLCertificateFile /etc/letsencrypt/live/example.com/fullchain.pem 
    SSLCertificateKeyFile /etc/letsencrypt/live/example.com/privkey.pem 
    SSLCertificateChainFile /etc/letsencrypt/live/example.com/chain.pem 
</VirtualHost> 

# Only specific commands with --vhost filter
$ bin/a2conf examples/example.conf --vhost www.example.com:443 --cmd documentroot sslcertificatefile 
DocumentRoot /var/www/example
SSLCertificateFile /etc/letsencrypt/live/example.com/fullchain.pem

# Same output achieved with other way of filtering (based on SSLEngine directive)
$ bin/a2conf examples/example.conf --filter sslengine on --cmd documentroot sslcertificatefile
DocumentRoot /var/www/example
SSLCertificateFile /etc/letsencrypt/live/example.com/fullchain.pem

# All hostnames configured in this config file
$ bin/a2conf examples/example.conf --cmd servername serveralias --uargs
secure.example.com example.com www.example.com 2.example.com 1.example.com

# per-vhost summary with filtering
$ bin/a2conf examples/example.conf --cmd servername serveralias --vhfmt 'Host: {servername} Root: {documentroot} Cert: {sslcertificatefile}' --filter sslcertificatefile
Host: example.com Root: /var/www/example Cert: /etc/letsencrypt/live/example.com/fullchain.pem
~~~

You can get list of all available tokens for `--vhfmt` option in verbose mode (`-v` option).

## a2certbot.py
a2certbot.py utility used to quickly detect common [LetsEncrypt](https://letsencrypt.org/) configuration errors such as:
- DocumentRoot mismatch between VirtualHost and LetsEncrypt renew config file (e.g. if someone moved site content)
- RewriteRule or Redirect apache directives preventing verification
- DNS record points to other host or not exists at all
- And **ANY OTHER** problem (such as using wrong certificate path in apache or whatever). `a2certbot.py` 
simulates HTTP verification (If LetsEncrypt verification fails, `a2certbot.py` will fail too, and vice versa).

a2certbot.py does not calls LetsEncrypt servers for verification, so if you will use a2certbot.py to verify your 
configuration, you will not hit [failed validation limit](https://letsencrypt.org/docs/rate-limits/) 
(*5 failures per account, per hostname, per hour* at moment) and will not be blacklisted on LetsEncrypt site.

### Requesting new certificate and troubleshooting

Before requesting new certificates:
~~~shell
# Verify configuration for website for which you want to request certificate for first time.
bin/a2certbot.py --prepare -w /var/www/virtual/static.okerr.com/ -d static.okerr.com
=== manual ===
Info:
    (static.okerr.com) is local 37.59.102.26
    (static.okerr.com) Vhost: /etc/apache2/sites-enabled/static.okerr.com.conf:1
    (static.okerr.com) DocumentRoot: /var/www/virtual/static.okerr.com/
    (static.okerr.com) DocumentRoot /var/www/virtual/static.okerr.com/ matches LetsEncrypt and Apache
    (static.okerr.com) Simulated check match root: /var/www/virtual/static.okerr.com/
---

# You can verify all hostnames for site
bin/a2certbot.py --prepare -w /var/www/virtual/static.okerr.com/ -d static.okerr.com -d static2.okerr.com

# ... and finally simple main all-in-one command, it guesses aliases and root (command below does same as command above):
bin/a2certbot.py --prepare -d static.okerr.com --aliases
~~~

a2certbot.py can generate letsencrypt certificates in simple way (automatically detecting all aliases and 
DocumentRoot, but you can use -d instead of --aliases):
~~~
root@bravo:/home/xenon# a2certbot.py --create -d static.okerr.com --aliases
Create cert for static.okerr.com
RUNNING: certbot certonly --webroot -w /var/www/virtual/static.okerr.com/ -d static.okerr.com -d static2.okerr.com
Saving debug log to /var/log/letsencrypt/letsencrypt.log
Plugins selected: Authenticator webroot, Installer None
Obtaining a new certificate
Performing the following challenges:
http-01 challenge for static2.okerr.com
Using the webroot path /var/www/virtual/static.okerr.com for all unmatched domains.
Waiting for verification...
Cleaning up challenges

IMPORTANT NOTES:
 - Congratulations! Your certificate and chain have been saved at:
...
~~~

### Troubleshooting renew certificates

If `certbot renew` fails:
~~~shell
# Check (verify) ALL existing LetsEncrypt certificates (to check why 'certbot renew' may fail ):
root@bravo:/home/xenon# a2certbot.py 
=== /etc/letsencrypt/renewal/bravo.okerr.com.conf PROBLEM ===
Info:
    (bravo.okerr.com) Vhost: /etc/apache2/sites-enabled/okerr.conf:17
    LetsEncrypt conf file: /etc/letsencrypt/renewal/bravo.okerr.com.conf
    bravo.okerr.com is local 37.59.102.26
Problems:
    No DocumentRoot in vhost at /etc/apache2/sites-enabled/okerr.conf:17
---

# Verify only one certificate 
root@bravo:/home/xenon# a2certbot.py --host bravo.okerr.com
=== /etc/letsencrypt/renewal/bravo.okerr.com.conf PROBLEM ===
Info:
    (bravo.okerr.com) Vhost: /etc/apache2/sites-enabled/okerr.conf:17
    LetsEncrypt conf file: /etc/letsencrypt/renewal/bravo.okerr.com.conf
    bravo.okerr.com is local 37.59.102.26
Problems:
    No DocumentRoot in vhost at /etc/apache2/sites-enabled/okerr.conf:17
---
~~~


### a2certbot.py warnings (false positives)
a2certbot.py expects that requests to .well-known directory of HTTP (port 80) virtualhost must not be redirected.
If you have redirection like this: `Redirect 301 / https://example.com/` it will report problem:
~~~
Problems:
    Requests will be redirected: Redirect 301 / https://www.example.com/
~~~

Actually, this could be OK (false positive) and real verification from `certbot renew` may pass (if https 
site has same  DocumentRoot). To see if this is real problem or not see result for 'Simulated check'. 
If simulated check matches - website will pass certbot verification. 

To avoid such false positive, do not use such 'blind' redirection, better use this:
~~~
      RewriteCond %{REQUEST_URI} !^/\.well\-known        
      RewriteRule (.*) https://%{SERVER_NAME}$1 [R=301,L]
~~~
This code in `<VirtuaHost *:80>` context will redirect all requests to HTTPS site EXCEPT LetsEncrypt verification 
requests.

## a2okerr.py
a2okerr.py is useful only if you are using [okerr](https://okerr.com/): free and open source hybrid (host/network) monitoring system. 

[Okerr](https://okerr.com/) is like [nagios](https://www.nagios.org/) or [zabbix](https://www.zabbix.com/), but can perform network checks 
from remote locations, has tiny and optional local client  which can run from cron, has powerful logical
indicators (notify me only if more then 2 servers are dead, notify me if any problem is not fixed for more then 30 minutes, ...), 
public status pages (like https://status.io/ but free), fault-tolerant sites 
(okerr will redirect dynamic DNS record to backup server if main server is dead, and point it back to main server
 when it's OK), supports [Telegram](https://telegram.org/) and has many other nice features. 
 
You can use it as free service (like wordpress or gmail) or you can install okerr server on your own linux machine 
from  [okerr git repository](https://gitlab.com/yaroslaff/okerr-dev/).

You will need to install small [okerrupdate](https://gitlab.com/yaroslaff/okerrupdate) package to use a2okerr.py: `pip3 install okerrupdate`.

a2okerr.py discovers all https sites from apache config and creates SSL-indicator in your okerr project 
for each website. You will get alert message to email and/or telegram if any of your https sites has any problem 
(certificate is not updated in time for any reason and will expire soon or already expired. 
Website unavailable for any reason). If you have linux server or website - you need okerr.

~~~shell
# Create indicator for all local https websites. If indicator already exists, HTTP error 400 will be received - this is OK.
a2okerr.py

# alter prefix, policy and description
a2okerr.py --prefix my:prefix: --policy Hourly --desc "I love okerr and a2okerr"

# do not really create indicators, just dry run
a2oker.py --dry
~~~

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
