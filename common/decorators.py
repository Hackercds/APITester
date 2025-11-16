"""
装饰器模块，提供各种装饰器功能
"""
import functools
import time
from typing import Any, Callable

from utils.logutil import logger


def log_function(func: Callable) -> Callable:
    """
    记录函数执行的日志
    
    Args:
        func: 被装饰的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.info(f"开始执行函数: {func.__name__}")
        logger.debug(f"函数参数: args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {str(e)}")
            raise
    return wrapper


def time_function(func: Callable) -> Callable:
    """
    计算函数执行时间
    
    Args:
        func: 被装饰的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"函数 {func.__name__} 执行时间: {end_time - start_time:.4f} 秒")
        return result
    return wrapper


def retry(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    """
    重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        delay: 重试间隔（秒）
        
    Returns:
        Callable: 装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempts = 0
            last_exception = None
            
            while attempts < max_attempts:
                attempts += 1
                try:
                    if attempts > 1:
                        logger.info(f"第 {attempts} 次重试函数: {func.__name__}")
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"函数 {func.__name__} 第 {attempts} 次执行失败: {str(e)}")
                    if attempts < max_attempts:
                        time.sleep(delay)
            
            logger.error(f"函数 {func.__name__} 在 {max_attempts} 次尝试后失败")
            raise last_exception
        return wrapper
    return decorator


def cache_result(expire: int = 300) -> Callable:
    """
    缓存函数结果
    
    Args:
        expire: 缓存过期时间（秒）
        
    Returns:
        Callable: 装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 创建缓存键
            key = str(args) + str(kwargs)
            
            # 检查缓存是否存在且未过期
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < expire:
                    logger.debug(f"使用缓存结果: {func.__name__}")
                    return result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        return wrapper
    return decorator