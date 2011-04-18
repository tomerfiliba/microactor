import sys
import os
from distutils.core import setup


# get version and version_string from version.py
version_file = os.path.join(os.path.dirname(__file__), 'microactor', 'version.py')
exec("\n".join(open(version_file).read().splitlines()))

if sys.version_info < (2, 6):
    sys.exit("requires python 2.6 and up")

setup(name = "microactor",
    version = version_string,
)

