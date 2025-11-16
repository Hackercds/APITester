"""
接口自动化测试框架核心工具模块包
提供全面的API测试支持，包括HTTP请求、断言验证、结果提取、配置管理、鉴权处理等功能
"""

# 从各模块导入核心类和函数

# 日志工具
from .logutil import LogUtil, logger, get_logger

# 数据库操作工具
# 暂时注释，避免数据库连接错误
# from .mysqlutil import DatabaseUtil, get_db_connection, get_db_util

# 测试用例管理
# 暂时注释，避免数据库连接错误
# from .readmysql import RdTestcase, get_test_cases, get_project_config

# HTTP请求工具
from .requestsutil import HttpClient as RequestManager

# 配置管理工具
from .configutil import ConfigManager, default_config_manager as config_manager, get_config, set_config

# 鉴权管理工具
from .authutil import AuthManager, TokenAuth, NoneAuth, BasicAuth, OAuth2Auth, HMACAuth

# 断言验证工具
from .assertutil import AssertionManager, assert_manager, verify_assertions

# 结果提取工具
from .extractutil import ExtractionManager, extraction_manager, extract_json, extract_regex, extract_header, extract_from_response

# 大模型接口工具
from .modelutils import ModelAPI, OpenAIAPI, AzureOpenAIAPI, CustomModelAPI, AsyncModelResponseHandler

# 随机数据生成工具
from .randomutil import RandomGenerator, TextRandomGenerator, DataGenerator

# 错误处理工具
from .errorutil import ApiAutoFrameworkError, ErrorReporter, handle_exception

# 并发控制工具
from .concurrencyutil import ConcurrentExecutor

# 测试用例管理
from .testcasemanager import TestCaseManager, test_case_manager

# 定义公开接口
__all__ = [
    # 日志工具
    'LogUtil',
    'logger',
    'get_logger',
    
    # 数据库工具（已注释，不导入）
    # 'RdTestcase',
    # 'get_test_cases',
    # 'get_project_config',
    
    # HTTP请求工具
    'RequestManager',
    
    # 配置管理工具
    'ConfigManager',
    'config_manager',
    'get_config',
    'set_config',
    
    # 鉴权管理工具
    'AuthManager',
    'TokenAuth',
    'NoneAuth',
    'BasicAuth',
    'OAuth2Auth',
    'HMACAuth',
    
    # 断言验证工具
    'AssertionManager', 
    'assert_manager', 
    'verify_assertions',
    
    # 结果提取工具
    'ExtractionManager',
    'extraction_manager',
    'extract_json',
    'extract_regex',
    'extract_header',
    'extract_from_response',
    
    # 大模型接口工具
    'ModelAPI',
    'OpenAIAPI',
    'AzureOpenAIAPI',
    'CustomModelAPI',
    'AsyncModelResponseHandler',
    
    # 随机数据生成工具
    'RandomGenerator',
    'TextRandomGenerator',
    'DataGenerator',
    
    # 错误处理工具
    'ApiAutoFrameworkError',
    'ErrorReporter',
    'handle_exception',
    
    # 并发控制工具
    'ConcurrentExecutor',
    
    # 测试用例管理
    'TestCaseManager',
    'test_case_manager'
]

# 版本信息
__version__ = '2.0.0'