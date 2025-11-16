# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='APITesterByHackercd',
    version='1.0.2',
    description='API自动化测试框架',
    author='Hackercd',
    author_email='Hackercd@foxmail.com',
    packages=['APITesterByHackercd'],
    py_modules=['__init__'],
    install_requires=[
        'requests>=2.25.0',
        'pytest>=6.0.0',
        'python-dotenv>=0.19.0',
        'PyYAML>=6.0',
        'loguru>=0.5.3'
    ],
    python_requires='>=3.7',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent'
    ]
)