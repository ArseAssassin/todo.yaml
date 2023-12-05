try:
    from setuptools import setup
except:
    from distutils.core import setup

config = {
    'description': 'todo.yaml is a CLI for managing task lists in YAML',
    'author': 'Tuomas Kanerva',
    'url': 'No URL',
    'download_url': 'Just local',
    'author_email': 'tuomas@kanerva.info',
    'version': '1.0',
    'install_requires': [],
    'packages': ['todo_yaml'],
    'scripts': ['bin/todo-yaml'],
    'name': 'todo_yaml'
}

setup(**config)
