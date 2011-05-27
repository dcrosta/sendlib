from setuptools import setup, find_packages

import os
here = os.path.abspath(os.path.dirname(__file__))
README = file(os.path.join(here, 'README.rst')).read()

setup(
    name='sendlib',
    version='0.1',
    description='sendlib  is a lightweight message serialization library which aims to be memory efficient',
    long_description=README,
    classifiers=[
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: BSD License',
        'Development Status :: 4 - Beta',
    ],
    author='Daniel Crosta',
    author_email='dcrosta@late.am',
    url='http://github.com/dcrosta/sendlib',
    keywords='message serialization',
    modules=['sendlib'],
    zip_safe=True,
    test_suite='tests',
)

