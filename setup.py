from setuptools import setup
from distutils.cmd import Command
import subprocess
import shutil
import os

from sendlib import __version__

class doc(Command):
    description = 'generate documentation'
    user_options = []
    boolean_options = []

    def initialize_options(self): pass
    def finalize_options(self): pass

    def run(self):
        path = 'doc/_build/%s' % __version__
        shutil.rmtree(path, ignore_errors=True)
        os.makedirs(path)
        subprocess.call(['sphinx-build', '-E', '-b', 'html', 'doc', path])

setup(
    name='sendlib',
    version=__version__,
    description='sendlib  is a lightweight message serialization library which aims to be memory efficient',
    long_description=file('README.rst').read(),
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: BSD License',
        'Development Status :: 4 - Beta',
    ],
    author='Daniel Crosta',
    author_email='dcrosta@late.am',
    url='http://github.com/dcrosta/sendlib',
    keywords='message serialization',
    py_modules=['sendlib'],
    zip_safe=True,
    test_suite='test',
    cmdclass={"doc": doc},
)

