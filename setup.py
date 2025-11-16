#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API自动化测试框架的安装配置文件
"""

import os
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 从requirements.txt中读取依赖项
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = []
    for line in f:
        # 跳过注释和空行
        line = line.strip()
        if line and not line.startswith('#'):
            requirements.append(line)

setuptools.setup(
    name="api-auto-framework",
    version="1.0.1",
    author="Hackercd",
    author_email="hackercd@efoxmail.com",
    description="一个功能强大的API自动化测试框架",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/api-auto-framework",
    packages=['common', 'config', 'testcase', 'utils', 'report', 'tests', 'log'],
    py_modules=['api_auto_framework'],
    data_files=[
        ('config', ['config/*.yaml', 'config/*.json']),
        ('templates', ['templates/*.html', 'templates/*.txt']),
    ],
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3.7',
    # 添加额外的依赖分组
    extras_require={
        'dev': [
            'pytest-cov>=2.12.1',
            'black>=22.0.0',
            'isort>=5.0.0',
            'flake8>=4.0.0',
        ],
        'full': [
            'jsonpath-ng>=1.5.0',
            'websocket-client>=1.2.1',
            'redis>=4.0.0',
            'pandas>=1.3.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'api-test=api_auto_framework:main',
        ],
    },
    keywords=['api', 'automation', 'testing', 'framework', 'http', 'rest', 'async'],
    project_urls={
        'Documentation': 'https://github.com/example/api-auto-framework/wiki',
        'Source': 'https://github.com/example/api-auto-framework',
        'Tracker': 'https://github.com/example/api-auto-framework/issues',
    },
    zip_safe=False,
)