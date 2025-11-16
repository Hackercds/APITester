#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API自动化测试框架主包
"""

# 版本信息
__version__ = "1.0.1"
__author__ = "API测试团队"
__description__ = "一个功能强大的API自动化测试框架"

# 从主模块导入核心类和函数
from api_auto_framework import (
    ApiTestFramework, 
    ApiAutoFrameworkError,
    RequestError,
    AssertionFailedError,
    ExtractionError,
    AuthenticationError,
    main
)

# 从工具模块导入常用类
from utils.requestutil import RequestManager
from utils.randomutil import DataGenerator
from utils.errorutil import ErrorReporter
from utils.assertutil import AssertionManager
from utils.extractutil import ExtractionManager
from utils.logutil import LogUtil
from utils.configutil import ConfigUtil
from utils.authutil import AuthManager
from utils.modelutils import ModelAPI, OpenAIAPI, AzureOpenAIAPI, CustomModelAPI

__all__ = [
    'ApiTestFramework', 
    'ApiAutoFrameworkError',
    'RequestError',
    'AssertionFailedError',
    'ExtractionError',
    'AuthenticationError',
    'main',
    'RequestManager',
    'DataGenerator',
    'ErrorReporter',
    'AssertionManager',
    'ExtractionManager',
    'LogUtil',
    'ConfigUtil',
    'AuthManager',
    'ModelAPI',
    'OpenAIAPI',
    'AzureOpenAIAPI',
    'CustomModelAPI'
]