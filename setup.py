from setuptools import setup
from di2008 import __version__

# read the long description
with open('readme.md', 'r') as f:
    long_description = f.read()

# read the requirements.txt

setup_attributes = {
    'name': 'di2008',
    'version': __version__,
    'description': 'Object-oriented API for DATAQ DI-2008',
    'long_description': long_description,
    'long_description_content_type': 'text/markdown',
    'url': 'https://github.com/slightlynybbled/di2008',
    'author': 'Jason R. Jones',
    'author_email': 'slightlynybbled@gmail.com',
    'license': 'MIT',
    'packages': ['di2008'],
    'python_requires': '>=3.6.0',
    'install_requires': ['pyserial >= 3.4'],
    'classifiers': [
        'License :: OSI Approved :: MIT License',
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    'zip_safe': False
}

setup(**setup_attributes)
