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
    ip = requests.get('http://ifconfig.me/')
    return ['127.0.0.1', ip.text]


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
            report.problem('URL {} got status code {}. Maybe Alias or RewriteRule working?'.format(
                test_url, r.status_code))
        else:
            if r.text == test_data:
                report.info("Simulated check match root: {} url: {}".format(droot, test_url))
                success = True
            else:
                report.problem("Simulated check fails root: {} url: {}".format(droot, test_url))

    os.unlink(test_file)
    return success


def process_file(path, local_ip_list, args):
    log.debug("processing " + path)
    root = a2conf.Node(name='#root')
    root.read_file(path)

    lc = None

    # alias checks
    for alias in root.children('Alias'):
        aliasfrom = alias.args.split(' ')[0]
        if '/.well-known/acme-challenge/'.startswith(aliasfrom):
            print("WARNING alias used:", alias, alias.args)
            print("Consider using --altroot option")


    for vhost in root.children('<VirtualHost>'):
        try:
            servername = next(vhost.children('servername')).args
        except StopIteration:
            report = Report(path)
            report.problem('Cannot get ServerName in {}:{}'.format(vhost.path, vhost.line))
            continue

        report = Report(servername)
        report.info("Apache config file: {} line: {}".format(vhost.path, vhost.line))

        # try:
        #    sslengine = next(vhost.children('sslengine'))
        #except StopIteration:
        #    continue

        # if sslengine.args != 'on':
        #    log.debug("Skip {} because sslengine args are: {}".format(vhost, repr(sslengine.args)))
        #    continue

        #
        # DNS names check
        #
        servername = next(vhost.children('servername')).args
        all_names = [ servername.lower() ]
        for aliascmd in vhost.children('serveralias'):
            for alias in aliascmd.args.split(' '):
                all_names.append(alias.lower())
        names_ok = 0
        names_failed = 0
        for name in all_names:
            ip_list = resolve(name)
            # log.debug("    {} resolved to: {}".format(name, ip_list))
            non_local = 0  # failed ips

            for ip in ip_list:
                if ip not in local_ip_list:
                    non_local += 1
                    report.problem("DNS {} is {} (not local)".format(name, ip))
                else:
                    report.info("DNS {} is {} (local)".format(name, ip))

            if non_local:
                names_failed += 1
            else:
                names_ok += 1

        #
        # DocumentRoot check
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
        # certfile check
        #

        certfile_node = vhost.first('SSLCertificateFile')
        if certfile_node:
            certfile = certfile_node.args
            report.info('Certfile: ' + certfile)
            if not os.path.isfile(certfile):
                report.problem("Missing certfile: " + certfile)

            if not certfile.startswith(args.ledir):
                report.problem('Certfile {} not in LetsEncrypt dir {}'.format(certfile, args.ledir))
        else:
            certfile = None

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

        if certfile:
            ledir_path_size = len(list(filter(None, args.ledir.split('/'))))
            cert_relpath = list(filter(None, certfile.split('/')))[ledir_path_size:]
            cert_name = cert_relpath[1]
            report.info("Certificate name: " + cert_name)

            leconf = os.path.join(args.ledir, 'renewal', cert_name + '.conf')
            report.info("LetsEncrypt conf file: " + leconf)
            if os.path.exists(leconf):
                lc = LetsEncryptCertificateConfig(leconf)
            else:
                report.problem("Missing LetsEncrypt conf file " + leconf)

            if lc:
                for domain in lc.domains:
                    if domain.lower() in all_names:
                        report.info('domain {} listed'.format(domain))
                        ddroot = lc.get_droot(domain)
                        if ddroot == droot:
                            report.info('Domain name {} has valid document root'.format(domain))
                        else:
                            report.problem('DocRoot mismatch for {}. Apache: {} LetsEncrypt: {}'.format(domain, droot, ddroot))

                        simulate_check(domain.lower(), ddroot, report)

                    else:
                        report.problem('domain {} (from LetsEncrypt config) not found among this VirtualHost names'.format(domain))
            else:
                report.problem("skipped domain/docroot checks because no letsencrypt config")

        #
        # Final check with requests
        #
        if droot is not None and os.path.isdir(droot):
            simulate_check(servername, droot, report)

        if args.altroot:
            simulate_check(servername, args.altroot, report)


        else:
            report.problem("skipped HTTP test because document root not exists")
        #
        # Final debug
        #
        if report.has_problems() or not args.quiet:
            report.report()


def main():
    global log

    def_file = '/etc/apache2/apache2.conf'
    def_ledir = '/etc/letsencrypt/'

    parser = argparse.ArgumentParser(description='Apache2 / Certbot misconfiguration diagnostic')

    parser.add_argument(dest='file', nargs='?', default=def_file, metavar='PATH',
                        help='Config file(s) path (def: {}). Either filename or directory'.format(def_file))
    parser.add_argument('-v', '--verbose', action='store_true',
                        default=False, help='verbose mode')
    parser.add_argument('-q', '--quiet', action='store_true',
                        default=False, help='quiet mode, suppress output for sites without problems')
    parser.add_argument('-i', '--ip', nargs='*',
                        help='Default addresses. Autodetect if not specified')
    parser.add_argument('--ledir', default=def_ledir, metavar='LETSENCRYPT_DIR_PATH',
                        help='Lets Encrypt directory def: {}'.format(def_ledir))
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

    if os.path.isdir(args.file):
        for f in os.listdir(args.file):
            path = os.path.join(args.file, f)
            if not (os.path.isfile(path) or os.path.islink(path)):
                continue
            process_file(path, local_ip_list, args)
    else:
        process_file(args.file, local_ip_list, args)


main()
