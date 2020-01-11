#!/usr/bin/env python3

import a2conf
import argparse
import logging
import requests
import os
import socket
import random
import string

log = None

class FatalError(Exception):
    pass

class LetsEncryptCertificateConfig:
    def __init__(self, path):
        self.path = path
        self.content = dict()
        self.readfile(path)

    def readfile(self, path):
        self.path = path
        self.content = dict()
        self.content[''] = dict()
        section = ''

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    # skip empty lines
                    continue

                if line.startswith('['):
                    # new section
                    section = line
                    self.content[section] = dict()
                else:
                    k, v = line.split('=')
                    k = k.strip()
                    v = v.strip()
                    self.content[section][k] = v

    @property
    def domains(self):
        try:
            return self.content['[[webroot_map]]'].keys()
        except KeyError:
            print("No [[webroot_map]] in {}".format(self.path))
            raise

    def get_droot(self, domain):
        return self.content['[[webroot_map]]'][domain]

    def dump(self):
        print(self.content)


class Report:
    def __init__(self, name):
        self.name = name
        self._info = list()
        self._problem = list()
        self.prefix = ' ' * 4

    def info(self, msg):
        self._info.append(msg)

    def problem(self, msg):
        self._problem.append(msg)

    def has_problems(self):
        return bool(len(self._problem))

    def report(self):
        if self._problem:
            print("=== {} PROBLEM ===".format(self.name))
        else:
            print("=== {} ===".format(self.name))

        if self._info:
            print("Info:")
            for msg in self._info:
                print(self.prefix + msg)

        if self._problem:
            print("Problems:")
            for msg in self._problem:
                print(self.prefix + msg)

        print("---\n")


def detect_ip():
    url = 'http://ifconfig.me/'
    r = requests.get(url)
    if r.status_code != 200:
        log.error('Failed to get IP from {} ({}), use --ip a.b.c.d'.format(url, r.status_code))

    assert(r.status_code == 200)
    return ['127.0.0.1', r.text]


def resolve(name):
    """
    return list of IPs for hostname or raise error
    :param name:
    :return:
    """
    try:
        data = socket.gethostbyname_ex(name)
        return data[2]
    except socket.gaierror:
        log.warning("WARNING: Cannot resolve {}".format(name))
        return list()

def simulate_check(servername, droot, report):
    success = False
    test_data = ''.join(random.choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(100))
    test_basename = 'certbot_diag_' + ''.join(random.choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(10))
    test_dir = os.path.join(droot, '.well-known', 'acme-challenge')
    test_file = os.path.join(test_dir, test_basename)
    #report.info("Test file path: " + test_file)
    test_url = 'http://' + servername + '/.well-known/acme-challenge/' + test_basename
    #report.info("Test file URL: " + test_url)

    log.debug('create test file ' + test_file)
    os.makedirs(test_dir, exist_ok=True)
    with open(test_file, "w") as f:
        f.write(test_data)

    log.debug('test URL ' + test_url)
    try:
        r = requests.get(test_url, allow_redirects=True)
    except requests.RequestException as e:
        report.problem("URL {} got exception: {}".format(test_url, e))
    else:
        if r.status_code != 200:
            report.problem('URL {} got status code {}. Used DocumentRoot {}. Maybe Alias or RewriteRule working?'.format(
                test_url, r.status_code, droot))
        else:
            if r.text == test_data:
                report.info("Simulated check match root: {} url: {}".format(droot, test_url))
                success = True
            else:
                report.problem("Simulated check fails root: {} url: {}".format(droot, test_url))

    os.unlink(test_file)
    return success


def is_local_ip(hostname, local_ip_list, report):
    iplist = resolve(hostname)
    for ip in iplist:
        if ip in local_ip_list:
            report.info('{} is local {}'.format(hostname, ip))
        else:
            report.problem('{} ({}) not local {}'.format(hostname, ip, local_ip_list))

def get_vhost(domain, apacheconf):
    root = a2conf.Node()
    root.read_file(apacheconf)

    for vhost in root.children('<VirtualHost>'):
        if not '80' in vhost.args:
            # log.debug('Skip vhost {}:{} (no 80 in {})'.format(vhost.path, vhost.line, vhost.args))
            continue
        try:
            servername = next(vhost.children('servername')).args
        except StopIteration:
            # log.debug('Skip vhost {}:{} (no ServerName)'.format(vhost.path, vhost.line))
            continue

        if domain.lower() == servername.lower():
            return vhost

        for alias in vhost.children('serveralias'):
            if domain.lower() in map(str.lower, alias.args.split(' ')):
                return vhost

    return None

def process_file(leconf, local_ip_list, args):
    log.debug("processing " + leconf)
    report = Report(os.path.basename(leconf))

    try:
        report.info("LetsEncrypt conf file: " + leconf)
        if os.path.exists(leconf):
            lc = LetsEncryptCertificateConfig(leconf)
        else:
            report.problem("Missing LetsEncrypt conf file " + leconf)
            raise FatalError

        # Local IP check
        for domain in lc.domains:
            log.debug("check domain {} from {}".format(domain, leconf))
            le_droot = lc.get_droot(domain)

            is_local_ip(domain, local_ip_list, report)
            vhost = get_vhost(domain, args.apacheconf)

            if not vhost:
                report.problem('Not found domain {} in {}'.format(domain, args.apacheconf))
                continue

            #
            # DocumentRoot exists?
            #
            droot = None
            try:
                droot = next(vhost.children('DocumentRoot')).args
            except StopIteration:
                report.problem("No DocumentRoot!")
            else:
                if droot is not None and os.path.isdir(droot):
                    report.info("DocumentRoot: {}".format(droot))
                else:
                    report.problem("DocumentRoot dir not exists: {} (problem!)".format(droot))

            #
            # Redirect check
            #
            try:
                r = next(vhost.children('Redirect'))
                rpath = r.args.split(' ')[1]
                if rpath in ['/', '.well-known']:
                    report.problem('Requests will be redirected: {} {}'.format(r, r.args))
            except StopIteration:
                # No redirect, very good!
                pass

            #
            # DocumentRoot matches?
            #

            if not args.altroot:
                # No altroot, simple check
                if os.path.realpath(le_droot) == os.path.realpath(droot):
                    report.info('DocumentRoot {} matches LetsEncrypt and Apache'.format(droot))
                else:
                    report.problem(
                        'DocRoot mismatch for {}. Apache: {} LetsEncrypt: {}'.format(domain, droot, le_droot))
                simulate_check(domain.lower(), droot, report)
            else:
                # AltRoot
                if os.path.realpath(le_droot) == os.path.realpath(args.altroot):
                    report.info('Domain name {} le root {} matches --altroot'.format(domain, le_droot))
                    simulate_check(domain.lower(), le_droot, report)
                elif os.path.realpath(le_droot) == os.path.realpath(droot):
                    report.info('Domain name {} le root {} matches DocumentRoot'.format(domain, le_droot))
                    simulate_check(domain.lower(), droot, report)
                else:
                    report.problem(
                        'DocRoot mismatch for {}. AltRoot: {} LetsEncrypt: {} Apache: {}'.format(
                            domain, args.altroot, le_droot, droot))

    except FatalError:
        pass
    # END OF FINISHED PART
    #
    # Final debug
    #
    if report.has_problems() or not args.quiet:
        report.report()

    return

def main():
    global log

    def_file = '/etc/apache2/apache2.conf'
    def_lepath = '/etc/letsencrypt/renewal/'

    parser = argparse.ArgumentParser(description='Apache2 / Certbot misconfiguration diagnostic')

    parser.add_argument(default=def_lepath, nargs='?', dest='lepath', metavar='LETSENCRYPT_DIR_PATH',
                        help='Lets Encrypt directory def: {}'.format(def_lepath))
    parser.add_argument('-a', '--apacheconf', dest='apacheconf', nargs='?', default=def_file, metavar='PATH',
                        help='Config file path (def: {})'.format(def_file))
    parser.add_argument('-v', '--verbose', action='store_true',
                        default=False, help='verbose mode')
    parser.add_argument('-q', '--quiet', action='store_true',
                        default=False, help='quiet mode, suppress output for sites without problems')
    parser.add_argument('-i', '--ip', nargs='*',
                        help='Default addresses. Autodetect if not specified')
    parser.add_argument('--altroot', default=None, metavar='DocumentRoot',
                        help='Try also other root (in case if Alias used). def: {}'.format(None))

    args = parser.parse_args()

    logging.basicConfig(
        # format='%(asctime)s %(message)s',
        format='%(message)s',
        # datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO)

    log = logging.getLogger('diag')

    if args.verbose:
        log.setLevel(logging.DEBUG)
        log.debug('Verbose mode')

    if args.ip:
        local_ip_list = args.ip
    else:
        log.debug("Autodetect IP")
        local_ip_list = detect_ip()
    log.debug("my IP list: {}".format(local_ip_list))

    if os.path.isdir(args.lepath):
        for f in os.listdir(args.lepath):
            path = os.path.join(args.lepath, f)
            if not (os.path.isfile(path) or os.path.islink(path)):
                continue
            process_file(path, local_ip_list, args)
    else:
        process_file(args.lepath, local_ip_list, args)


main()
