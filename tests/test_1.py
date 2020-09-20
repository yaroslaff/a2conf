import a2conf
import pytest
from tempfile import mkdtemp
import os

confdir = None
files = dict()

examples = {
'c1': """
# Test VirtualHost

<VirtualHost *:80  *:443>
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
""",
'include': 'Include {confdir}/c1.conf',
'include_glob': 'Include {confdir}/c*.conf'
}



def setup_module(module):
    global confdir
    global files
    confdir = mkdtemp(prefix='a2conf-test-', dir='/tmp')

    for codename, content in examples.items():
        files[codename] = os.path.join(confdir, codename+'.conf')

        with open(files[codename], "w") as f:
            f.write(content.format(confdir=confdir))


def teardown_module(module):
    for codename, path in files.items():
        os.unlink(path)

    os.rmdir(confdir)


class TestClass:
    def test_children(self):
        root = a2conf.Node(files['c1'])
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

    def test_include(self):
        # with disabled recursion len = 1
        root = a2conf.Node(files['include'], includes=False)
        assert(len(list(root.children(recursive=True))) == 1)

        root = a2conf.Node(files['include'])
        assert(len(list(root.children(recursive=True)))> 1)

    def test_include_glob(self):
        root = a2conf.Node(files['include_glob'])
        assert(len(list(root.children(recursive=True))) > 1)

    def test_replace(self):
        root = a2conf.Node(files['c1'])

        ssl = next(root.children('SSLEngine', recursive=True))
        ssl.args = 'off'

        ssl = next(root.children('SSLEngine', recursive=True))
        assert(ssl.args == 'off')

    def test_first(self):
        root = a2conf.Node(files['c1'])

        name1 = next(root.children('servername', recursive=True))
        name2 = next(root.children('servername', recursive=True))
        name3 = root.first('servername', recursive=True)

        assert(name1 == name2)
        assert(name2 == name3)

    def test_delete(self):
        root = a2conf.Node(files['c1'])

        ssl = root.first('SSLEngine', recursive=True)
        ssl.delete()

        assert(root.first('SSLEngine', recursive=True) is None)

    def test_add_root(self):
        root = a2conf.Node()
        root.add('Cmd1')
        root.add('Cmd2')
        root.insert('Cmd1.5 Option  # in the middle', after=['cmd1'])
        root.insert('Cmd3',)

        assert(root.content[1].name == 'Cmd1.5')
        assert(root.content[3].name == 'Cmd3')

    def test_add_vhost(self):
        root = a2conf.Node(files['c1'])

        vhost = root.first('<VirtualHost>')
        new_node = a2conf.Node(raw='MyTestDirective Option1 Option2')
        vhost.insert(new_node, after=['Serveralias'])
        assert (vhost.first('MyTestDirective') is not None)


