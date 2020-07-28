#!/usr/bin/python

import re
import sys
import os
import glob

class Node(object):
    def __init__(self, read=None, raw=None, parent=None, name=None, suffix=None, path=None, line=None, includes=True):
        self.raw = raw
        self.parent = parent
        self.content = list()  # children
        self.prefix = ' '*4
        self.section = None  # Section e.g. "VirtualHost" or None
        self.cmd = None  # Command, e.g. "ServerName"
        self.args = None  # Args to section (VirtualHost), e.g. "*:80" or
        self.suffix = None
        self.last_child = None
        self.includes = includes

        self.path = path  # Filename
        self.line = line  # line in file

        if self.raw:
            match = re.search('(#.*)$', self.raw)
            if match:
                self.suffix = match.group(0)
            else:
                self.suffix = ''

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
            m = re.match('[ \t]*<([^ >]+)([^>]*)', self.raw)
            self.section = m.group(1)
            self.args = m.group(2).strip()
        elif self.is_close():
            m = re.match('[ \t]*<(/[^ >]+)([^>]*)', self.raw)
            self.section = m.group(1)
        elif self.raw:
            cmdline = self.raw.split('#')[0].strip()

            if cmdline:
                m = re.match('[ \t]*([^ \t]+)[ \t]*([^#]*)', cmdline)
                if m is None:
                    print("Cannot parse", repr(cmdline))
                    assert(False)
                else:
                    # parsed well
                    self.cmd = m.group(1)
                    self.args = m.group(2).strip()

        if read:
            self.read_file(read)

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

        if isinstance(child, str):
            child = Node(raw=child)
        self.content.append(child)
        self.last_child = child

    def insert(self, child, after=None):
        if not self.content:
            self.add(child)
            return

        if isinstance(child, str):
            child = Node(raw=child)

        if self.content[-1].is_close():
            idx = len(self.content)-1
        else:
            idx = len(self.content)

        if after:
            for i, c in enumerate(self.content):
                if c.name.lower() == after.lower():
                    idx = i+1
        self.content.insert(idx, child)

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

        self.content = [c for c in self.content if ff(regex, c)]


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

    def first(self, name, recursive=False):
        """ Wrapper for children to get only first element or None
        :param name: name of element, e.g. ServerName or SSLEngine
        :param recursive:
        :return: Element or None
        """
        try:
            return next(self.children(name, recursive=recursive))
        except StopIteration:
            return None

    def extend(self, n):
        # for c in n.content:
        #     self.content.append(c)
        self.content.extend(n.content)

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
                node = Node(raw=l, parent = parent, path = filename, line = line)

                if node.is_open():
                    parent.add(node)
                    parent = node
                elif node.is_close():
                    parent.add(node)
                    parent = parent.parent
                else:
                    parent.add(node)

                if self.includes and node.name.lower() in ['include', 'includeoptional']:
                    basedir = os.path.dirname(filename)
                    include_files = glob.glob(os.path.join(basedir, node.args))
                    for path in include_files:
                        sub_node = Node(path)
                        self.extend(sub_node)
                        #self.content.extend(sub_node.content)


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
        # Print line itself

        if self.cmd:
            fh.write("{}{} {} {}\n".format(self.prefix*depth, self.cmd, self.args, self.suffix))
        elif self.section:
            # last section element should have depth-1
            if self.section.startswith('/'):
                line_depth = depth-1
            else:
                line_depth = depth

            if self.args:
                fh.write("{}<{} {}> {}\n".format(self.prefix*line_depth, self.section, self.args, self.suffix))
            else:
                fh.write("{}<{}> {}\n".format(self.prefix*line_depth, self.section, self.suffix))

            if self.children:
                for d in self.content:
                    d.dump(fh, depth+1)
        else:
            # neither cmd, nor section
            if self.suffix:
                print(self.prefix*depth + self.suffix)
            # only root node has cmd=None, section=None but has children
            if self.children:
                for d in self.content:
                    d.dump(fh, depth)
        return

    def __str__(self):
        if self.name is not None:
            return self.name
        else:
            return self.raw

    def delete(self):
        """ Delete myself from parent content """
        self.parent.content.remove(self)

