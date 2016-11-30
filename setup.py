import platform
from setuptools import setup, find_packages

reqs = {
    'Windows': ['pypiwin32', 'pyreadline'],
    'Darwin': ['gnureadline']
}

setup(
    name='vision',
    version='0.10.567',
    packages=find_packages(),

    # This requires selenium
    install_requires = [
        'selenium',
        'pillow'] + reqs.get(platform.system(), []),

    # PyPI data
    author = "Aaron Lehmann",
    author_email = "aaron.p.lehmann@gmail.com",
    license = "MIT License <https://opensource.org/licenses/MIT>",
    description = "This is a language that allows selenium tests to be written using a subset of English.",
    keywords = "selenium",

    # Entry points
    entry_points = {
        'console_scripts': [
        'vision = vision.visionconsole:main']
    }
)
