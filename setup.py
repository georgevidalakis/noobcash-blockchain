'''Setup script
Usage: pip install .
To install development dependencies too, run: pip install .[dev]
'''
from setuptools import setup, find_packages

setup(
    name='noobcash',
    version='v1.0',
    packages=find_packages(),
    scripts=[],
    url='https://github.com/georgevidalakis/noobcash-blockchain',
    author='Georgios {Vidal, Chochl}akis',
    install_requires=[],
    extras_require={
        'dev': [
            'pylint',
            'git-pylint-commit-hook',
            'flask',
            'ordered_set',
            'urllib3',
            'numpy',
            'pycryptodome',
        ],
    },
)
