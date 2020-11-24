#!/usr/bin/env python3

import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='a2conf',
    version='0.2.26',
    packages=['a2conf'],
    scripts=[ 'bin/a2conf', 'bin/apache2okerr.py', 'bin/apache2-certbot-diag.py' ],

    # install_requires=[],

    url='https://github.com/yaroslaff/a2conf',
    license='MIT',
    author='Yaroslav Polyakov',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    author_email='yaroslaff@gmail.com',
    description='apache2 configuration file parser and query tool',
    install_requires=['requests'],

    python_requires='>=3',
    classifiers=[
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Pick your license as you wish (should match "license" above)
         'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
#        'Programming Language :: Python :: 3.4',
    ]
)
