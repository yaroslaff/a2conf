#!/usr/bin/python

import re
import sys
import os
import glob

class Node(object):
    def __init__(self, raw=None, parent=None, name=None, path=None, line=None, includes=True):
        self.raw = raw
        self.parent = parent
        self.content = list() # children
        self.prefix = ' '*4
        self.section = None # Section e.g. "VirtualHost" or None
        self.cmd = None # Command, e.g. "ServerName"
        self.args = None # Args to section (VirtualHost), e.g. "*:80" or
        self.includes = includes

        self.path = path # Filename
        self.line = line # line in file


        if name:
            self.name = name
        else:
            if self.raw:
                # guess name, ServerName or <VirtualHost>
                self.name = self.raw.strip().split(' ')[0]
                if self.name.startswith('<') and not self.name.endswith('>'):
                    self.name += '>'
            else:
                self.name = '#root'

        if self.is_open():
            m = re.match('[ \t]*<([^ >]+)([^>]+)', self.raw)
            self.section = m.group(1)
            self.args = m.group(2).strip()
        elif self.is_close():
            pass
        elif self.raw:
            cmdline = self.raw.split('#')[0]
            if cmdline:
                m = re.match('[ \t]*([^ \t]+)[ \t]*([^#]*)', cmdline)
                if m is None:
                    print("Cannot parse", repr(cmdline))
                    assert(False)
                else:
                    # parsed well
                    self.cmd = m.group(1)
                    self.args = m.group(2).strip()


    def __repr__(self):
        return("<{}>".format(self.name))

    def is_open(self):
        """ Return True if this node opens section, e.g <VirtualHost> or <IfModule>"""
        if self.raw is None:
            return False

        if re.match('^[ \t]*<(?!/)', self.raw):
            return True
        return False

    def is_close(self):
        """ Return True if this node closes section"""
        if self.raw is None:
            return False

        if re.match('[ \t]*</', self.raw):
            return True
        return False

    def add(self, child):
        """ Append child to node """
        if self.content is None:
            self.content = list()
        self.content.append(child)

    def add_raw(self, raw):
        sl = Node(raw, parent=self)
        self.add(sl)

    def get_opentag(self):
        return "<{} {}>".format(self.section, self.args)
        #return self.raw.strip()

    def get_closetag(self):
        return "</{}>".format(self.section)

    def filter(self, regex):

        def ff(regex, c):
            # print "FF", c, c.raw
            if c.section:
                # print "SECTION", c
                c.filter(regex)
            return not re.match(regex, c.raw, re.IGNORECASE)

        self.content = [ c for c in self.content if ff(regex, c) ]


    def children(self, name=None, recursive=False):
        if self.content:
            for c in self.content:
                if name:
                    # filter by cmd/section
                    if c.name.lower() == name.lower():
                        yield c
                else:
                    # print "YIELD", c, repr(c.raw), c.name
                    yield c

                if recursive and c.content:
                    for subc in c.children(name=name, recursive=recursive):
                        yield subc


    def all_nodes(self):
        ret = list()
        ret.append(self)
        for c in self.content:
            if c.is_open():
                ret.extend(c.all_nodes())
        return ret

    def get_node_re(self, regex):
        for c in self.content:
            if re.match(regex, c.raw, re.IGNORECASE):
                return c

    def get_nodes_cmd(self, cmdlist):
        lowlist = list(map(str.lower, cmdlist))
        for c in self.content:
            if c.cmd and c.cmd.lower() in lowlist:
                yield(c)

    def add_prefix(self,prefix, regex):
        n = self.get_node(regex)
        n.raw = prefix + n.raw
        n.name = n.raw


    def extend(self, n):
        for c in n.content:
            self.content.append(c)

    def read_file(self, filename):

        # read file
        root = self
        parent = root

        line = 0

        with open(filename) as fh:
            for l in fh.readlines():
                line += 1
                l = l.strip()
                if not l:
                    continue
                node = Node(l, parent, path = filename, line = line)

                if node.is_open():
                    parent.add(node)
                    parent = node
                elif node.is_close():
                    parent = parent.parent
                    # parent.add(node)
                else:
                    parent.add(node)

                if self.includes and node.name.lower() in ['include', 'includeoptional']:
                    basedir = os.path.dirname(filename)
                    include_files = glob.glob(os.path.join(basedir, node.args))
                    for path in include_files:
                        sub_node = Node('#subnode')
                        sub_node.read_file(path)
                        self.content.extend(sub_node.content)


    def write_file(self, filename):
        if filename != '-':        
            with open(filename, 'w') as fh:
                self.dump(fh)
        else:
            self.dump()


    def vdump(self, depth=0):
        newdepth = depth + 1
        if self.content:
            for d in self.content:
                if d.is_open():
                    print(self.prefix*depth + d.get_opentag())
                    # print "# dump", d.section, "depth", newdepth
                    d.vdump(newdepth)
                    print(self.prefix*depth + d.get_closetag())
                else:
                    print(self.prefix*depth + str(d))
        else:
            # print "NOCONTENT:", self.raw # NOCONTENT
            pass



    def dump(self, fh=sys.stdout, depth=0):
        # print myself first
        newdepth = depth + 1

        if self.content:
            for d in self.content:
                if d.is_open():
                    fh.write('\n')
                    fh.write(self.prefix*depth + d.get_opentag() + '\n')
                    # print "# dump", d.section, "depth", newdepth
                    d.dump(fh, newdepth)
                    fh.write(self.prefix*depth + d.get_closetag() + '\n\n')
                else:
                    args = d.args or ''
                    fh.write(self.prefix*depth + str(d) + ' ' + args + '\n')
        else:
            # print self.raw # NOCONTENT
            pass

    def __str__(self):
        if self.name is not None:
            return self.name
        else:
            return self.raw


