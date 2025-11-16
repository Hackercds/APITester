#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API自动化测试框架主包
"""

# 版本信息
__version__ = "1.0.1"
__author__ = "Hackercd"
__description__ = "一个功能强大的API自动化测试框架"

# 核心类和函数定义
class ApiTestFramework:
    """API测试框架主类"""
    pass

class ApiAutoFrameworkError(Exception):
    """框架基础异常类"""
    pass

class RequestError(ApiAutoFrameworkError):
    """请求异常类"""
    pass

class AssertionFailedError(ApiAutoFrameworkError):
    """断言失败异常类"""
    pass

class ExtractionError(ApiAutoFrameworkError):
    """数据提取异常类"""
    pass

class AuthenticationError(ApiAutoFrameworkError):
    """认证异常类"""
    pass

def main():
    """框架主入口函数"""
    pass

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