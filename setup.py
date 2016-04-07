import platform
from setuptools import setup, find_packages

focuslibs = {
    'Windows': ['pypiwin32'],
}

setup(
    name='vision',
    version='0.10.212',
    packages=find_packages(),

    # This requires selenium
    install_requires = [
        'selenium',
        'pillow'] + focuslibs.get(platform.system(), []),

    # PyPI data
    author = "Aaron Lehmann",
    author_email = "aaron.p.lehmann@gmail.com",
    license = "MIT License <https://opensource.org/licenses/MIT>",
    description = "This is a language that allows selenium tests to be written using a subset of English.",
    keywords = "selenium",

    # Entry points
    entry_points = {
        'console_scripts': [
        'vision = vision.vision:main']
    }
)
