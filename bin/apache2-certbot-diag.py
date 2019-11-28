#!/usr/bin/env python3

import a2conf
import argparse
import logging
import requests
import os
import socket
import random
import string

# import apache2conf

class LetsEncryptCertificateConfig():
    def __init__(self, path):
        self.path = path
        self.readfile(path)

    def readfile(self, path):
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
        return self.content['[[webroot_map]]'].keys()

    def get_droot(self, domain):
        return self.content['[[webroot_map]]'][domain]

    def dump(self):
        print(self.content)

class Report():
    def __init__(self, name):
        self.name = name
        self._info = list()
        self._problem = list()
        self.prefix = ' '*4;

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
     return [ '127.0.0.1', ip.text ]


def resolve(name):
    """
    return list of IPs for hostname or raise error
    :param name:
    :return:
    """
    #try:
    data = socket.gethostbyname_ex(name)
    # print(data)
    return data[2]
        #ipx = repr(data[2])
        #return ipx
    #except socket.gaierror:
    #    return list()

def process_file(path, local_ip_list, args):
    log.debug("processing " + path)
    root = a2conf.Node(name='#root')
    root.read_file(path)

    lc = None

    for vhost in root.children(cmd='<VirtualHost>'):
        servername = next(vhost.children('servername')).args
        report = Report(servername)

        problem = False
        try:
            sslengine = next(vhost.children('sslengine'))
        except StopIteration:
            continue

        if sslengine.args != 'on':
            log.debug("Skip {} because sslengine args are: {}".format(vhost, repr(sslengine.args)))
            continue


        #
        # DNS names check
        #
        servername = next(vhost.children('servername')).args
        all_names = [servername]
        for aliascmd in vhost.children('serveralias'):
            for alias in aliascmd.args.split(' '):
                all_names.append(alias)
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
                problem = True
            else:
                names_ok += 1

        #
        # certfile check
        #

        certfile = next(vhost.children('SSLCertificateFile')).args
        report.info('Certfile: ' + certfile)
        if not os.path.isfile(certfile):
            report.problem("Missing certfile: " + certfile)

        if not certfile.startswith(args.ledir):
            report.problem('Certfile {} not in LetsEncrypt dir {}'.format(certfile, args.ledir))

        #
        # DocumentRoot check
        #

        try:
            droot = next(vhost.children('DocumentRoot')).args
        except StopIteration:
            report.problem("No DocumentRoot!")
        else:
            if os.path.isdir(droot):
                report.info("DocumentRoot: {}".format(droot))
            else:
                report.problem("DocumentRoot dir not exists: {} (problem!)".format(droot))

        ledir_path_size = len(list(filter(None, args.ledir.split('/'))))
        cert_relpath = list(filter(None, certfile.split('/')))[ledir_path_size:]
        cert_name = cert_relpath[1]
        report.info("Certificate name: " + cert_name)

        leconf = os.path.join(args.ledir,'renewal', cert_name + '.conf')
        report.info("LetsEncrypt conf file: " + leconf )
        if os.path.exists(leconf):
            lc = LetsEncryptCertificateConfig(leconf)
        else:
            report.problem("Missing LetsEncrypt conf file " + leconf)

        if lc:
            for domain in lc.domains:
                if domain in all_names:
                    report.info('domain {} listed'.format(domain))
                    ddroot = lc.get_droot(domain)
                    if ddroot == droot:
                        report.info('Domain name {} has valid document root'.format(domain))
                    else:
                        report.info('DocRoot mismatch for {}. Site: {} Domain: {}'.format(domain, droot, ddroot))

                else:
                    report.problem('domain {} not in virthost names'.format(domain))
        else:
            report.problem("skipped domain/docroot checks because no letsencrypt config")


        #
        # Final check with requests
        #
        if os.path.isdir(droot):
            test_data = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(100))
            test_basename = 'certbot_diag_' + ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(10))
            test_dir = os.path.join(droot, '.well-known', 'acme-challenge')
            test_file = os.path.join(test_dir, test_basename)
            report.info("Test file path: " + test_file)
            test_url = 'http://'+servername+'/.well-known/acme-challenge/' + test_basename
            report.info("Test file URL: " + test_url)

            log.debug('create test file ' + test_file)
            os.makedirs(test_dir, exist_ok=True)
            with open(test_file, "w") as f:
                f.write(test_data)

            log.debug('test URL '+test_url)
            r = requests.get(test_url, allow_redirects=True)
            if r.status_code != 200:
                report.problem('URL {} got status code {}. Maybe Alias or RewriteRule working?'.format(test_url, r.status_code))

            if r.text == test_data:
                report.info("test data matches")
            else:
                report.problem('test data not matches')

            os.unlink(test_file)
        else:
            report.problem("skipped HTTP test because document root not exists")
        #
        # Final debug
        #
        report.report()

def main():
    global log

    def_dir = '/etc/apache2/sites-enabled/'
    def_ledir = '/etc/letsencrypt/'

    parser = argparse.ArgumentParser(description='Apache2 / Certbot misconfiguration diagnostic')

    parser.add_argument('-v', dest='verbose', action='store_true',
                        default=False, help='verbose mode')
    parser.add_argument('-d', '--dir', default=def_dir, metavar='DIR_PATH',
                        help='Directory with apache virtual sites. def: {}'.format(def_dir))
    parser.add_argument('-f', '--file', default=None, metavar='PATH',
                        help='One config file path')
    parser.add_argument('-i', '--ip', nargs='*',
                        help='Default addresses. Autodetect if not specified')
    parser.add_argument('--ledir', default=def_ledir, metavar='LETSENCRYPT_DIR_PATH',
                        help='Lets Encrypt directory def: {}'.format(def_ledir))

    args = parser.parse_args()

    logging.basicConfig(
        #format='%(asctime)s %(message)s',
        format='%(message)s',
        #datefmt='%Y-%m-%d %H:%M:%S',
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

    if args.file:
        process_file(args.file, local_ip_list, args)
    else:
        for f in os.listdir(args.dir):
            path = os.path.join(args.dir, f)
            if not (os.path.isfile(path) or os.path.islink(path)):
                continue
            process_file(path, local_ip_list, args)


main()
