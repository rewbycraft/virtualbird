from setuptools import setup, find_packages

setup(
    name="virtualbird",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'pyroute2',
        'PyYAML'
    ],
    entry_points={
        'console_scripts': ['virtualbird=virtualbird.command_line:main'],
    }
)
