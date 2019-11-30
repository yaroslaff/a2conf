import a2conf
import pytest
from tempfile import mkdtemp
import os

confdir = None
files = dict()

examples = {
'c1': """<VirtualHost *:80  *:443>
    ServerAdmin postmaster@example.com
    ServerName example.com
    ServerAlias www.example.com example.example.com
    ServerAlias x.example.com
    DocumentRoot /usr/local/apache/htdocs/example.com
    
    Command1 first
    Command1 second
    
    <IfModule mod_ssl.c>
        Command1 nested
        SSLEngine on
        SSLCertificateFile /etc/letsencrypt/live/example.com/fullchain.pem
        SSLCertificateKeyFile /etc/letsencrypt/live/example.com/privkey.pem
        SSLCertificateChainFile /etc/letsencrypt/live/example.com/chain.pem
    </IfModule mod_ssl.c>
</VirtualHost>
"""
}



def setup_module(module):
    global confdir
    global files
    confdir = mkdtemp(prefix='a2conf-test-', dir='/tmp')
    print("confdir:", confdir)

    for codename, content in examples.items():
        files[codename] = os.path.join(confdir, codename+'.conf')

        with open(files[codename], "w") as f:
            f.write(content)


def teardown_module(module):
    print("TEARDOWN", confdir)
    for codename, path in files.items():
        os.unlink(path)

    os.rmdir(confdir)


class TestClass:
    def test_children(self):
        print(123)
        assert(1==1)
        root = a2conf.Node(name='#root')
        root.read_file(files['c1'])
        assert(len(list(root.children('<VirtualHost>'))) == 1)

        vh = list(root.children('<VirtualHost>'))[0]

        assert(len(list(vh.children('ServerAlias'))) == 2)

        assert(len(list(vh.children('serveralias'))) == 2)
        assert(len(list(vh.children('SERVERALIAS'))) == 2)


        aliases = list()
        for alias_node in vh.children('ServerAlias'):
            for alias in alias_node.args.split(' '):
                aliases.append(alias)
        assert(len(aliases) == 3)

        # should not found because not recursive
        assert(len(list(vh.children('sslengine', recursive=False))) == 0)

        # should not found because not recursive
        assert(len(list(vh.children('sslengine', recursive=True ))) == 1)
