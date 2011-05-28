from setuptools import setup, find_packages

import os
here = os.path.abspath(os.path.dirname(__file__))
README = file(os.path.join(here, 'README.rst')).read()

setup(
    name='sendlib',
    version='0.2',
    description='sendlib  is a lightweight message serialization library which aims to be memory efficient',
    long_description=README,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'
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
)

