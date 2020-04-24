import ast
import io
import re

from setuptools import setup

VERSION = '0.1.dev1'
lektor_plugins = [
    'limit-dependencies = lektor_limit_dependencies:LimitDependenciesPlugin',
    ]


with io.open('README.md', 'rt', encoding="utf8") as f:
    readme = f.read()

_description_re = re.compile(r'description\s+=\s+(?P<description>.*)')

with open('lektor_limit_dependencies.py', 'rb') as f:
    description = str(ast.literal_eval(_description_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    author='Jeff Dairiki',
    author_email='dairiki@dairiki.org',
    description=description,
    keywords='Lektor plugin',
    license='BSD',
    long_description=readme,
    long_description_content_type='text/markdown',
    name='lektor-limit-dependencies',
    py_modules=['lektor_limit_dependencies'],
    # url='[link to your repository]',
    version=VERSION,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Framework :: Lektor',
        'Environment :: Plugins',
    ],
    install_requires=[
        'lektorlib',
        ],
    entry_points={
        'lektor.plugins': lektor_plugins,
    }
)
