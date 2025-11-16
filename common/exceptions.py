"""
自定义异常类
"""


class ApiAutoFrameworkError(Exception):
    """框架基础异常类"""
    pass


class ConfigError(ApiAutoFrameworkError):
    """配置错误异常"""
    pass


class DataSourceError(ApiAutoFrameworkError):
    """数据源错误异常"""
    pass


class HttpError(ApiAutoFrameworkError):
    """HTTP请求错误异常"""
    pass


class ValidationError(ApiAutoFrameworkError):
    """验证错误异常"""
    pass


class TestCaseError(ApiAutoFrameworkError):
    """测试用例错误异常"""
    pass


class ParameterError(ApiAutoFrameworkError):
    """参数错误异常"""
    pass