import io
import os
import re

from setuptools import find_packages, setup

def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', os.linesep)
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)

setup(
    name='mccloud',
    version='0.0.13',
    license='Apache Software License',
    url='http://github.com/kjenney/mccloud',
    author='Ken Jenney',
    author_email='me@kenjenney.com',
    description='Administer AWS',
    long_description=read('README.rst'),
    packages=find_packages(),
    python_requires='>=3',
    install_requires=[
        'Click',
    ],
    entry_points = {
        'console_scripts': ['mccloud = mccloud.cli:entry'],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ]
)
