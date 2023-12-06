#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='todo-yaml',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': ['todo-yaml = todo_yaml.cli:todo_yaml']
    }
)