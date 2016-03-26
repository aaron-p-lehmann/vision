import platform
from setuptools import setup, find_packages

focuslibs = {
    'Windows': ['pypiwin32'],
    'Linux': [],
}

setup(
    name='vision',
    version='0.10.199',
    packages=find_packages(),

    # This requires selenium
    install_requires = [
        'selenium',
        'pillow'] + focuslibs[platform.system()],

    # PyPI data
    author = "Aaron Lehmann",
    author_email = "alehmann@mieweb.com",
    license = "Closed",
    description = "This is a language that allows selenium tests to be written using a subset of English.",
    keywords = "selenium",
    )


