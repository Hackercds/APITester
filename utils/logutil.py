
"""
日志工具模块 - 增强版
支持区分用户日志和框架日志，提供彩色输出和日志分类功能
"""
import logging
import os
import time
import sys
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class ColoredFormatter(logging.Formatter):
    """
    彩色日志格式化器
    """
    # 颜色代码
    COLORS = {
        'DEBUG': '\033[38;5;240m',  # 灰色
        'INFO': '\033[38;5;34m',    # 绿色
        'WARNING': '\033[38;5;220m', # 黄色
        'ERROR': '\033[38;5;196m',  # 红色
        'CRITICAL': '\033[38;5;160m\033[48;5;231m', # 深红底白字
        'RESET': '\033[0m',        # 重置
        'USER': '\033[38;5;33m',    # 蓝色（用户日志）
        'FRAMEWORK': '\033[38;5;99m' # 紫色（框架日志）
    }
    
    def __init__(self, fmt=None, datefmt=None, use_color=True):
        super().__init__(fmt, datefmt)
        self.use_color = use_color and sys.stdout.isatty()  # 仅在终端时使用颜色
    
    def format(self, record):
        # 调用父类格式化方法
        formatted = super().format(record)
        
        # 添加颜色
        if self.use_color:
            level_name = record.levelname
            log_type = 'USER' if getattr(record, 'log_type', 'user') == 'user' else 'FRAMEWORK'
            
            # 添加颜色前缀
            color_prefix = self.COLORS.get(level_name, '') + self.COLORS.get(log_type, '')
            color_suffix = self.COLORS['RESET']
            
            return f"{color_prefix}{formatted}{color_suffix}"
        
        return formatted


class LogUtil:
    """
    日志工具类，提供增强的日志功能
    支持区分用户日志和框架日志，提供日志轮转和彩色输出
    """
    
    # 预定义日志配置
    DEFAULT_CONFIGS = {
        'framework': {
            'name': 'api_auto_framework',
            'level': logging.DEBUG,
            'file_level': logging.DEBUG,
            'console_level': logging.INFO,
            'log_format': "%(asctime)s [FRAMEWORK] - %(name)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s"
        },
        'user': {
            'name': 'api_auto_user',
            'level': logging.INFO,
            'file_level': logging.INFO,
            'console_level': logging.INFO,
            'log_format': "%(asctime)s [USER] - %(name)s - %(levelname)s: %(message)s"
        }
    }
    
    def __init__(self, 
                 logger_name: str = "api_auto",
                 log_dir: str = None,
                 log_type: str = 'framework',
                 max_bytes: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 10,  # 增加备份数量
                 use_rotate_file: bool = True,
                 use_color: bool = True):
        # 移除rotate_when参数，简化配置
        """
        初始化日志配置
        
        Args:
            logger_name: 日志名称前缀
            log_dir: 日志文件目录
            log_type: 日志类型 ('framework' 或 'user')
            max_bytes: 单个日志文件最大字节数（用于大小轮转）
            backup_count: 保留的备份日志数量
            rotate_when: 时间轮转的时间点
            use_rotate_file: 是否使用日志轮转
            use_color: 是否使用彩色输出
        """
        # 根据类型获取配置
        self.log_type = log_type
        config = self.DEFAULT_CONFIGS.get(log_type, self.DEFAULT_CONFIGS['user']).copy()
        config['name'] = f"{logger_name}_{config['name']}"
        
        # 创建logger
        self.logger = logging.getLogger(config['name'])
        self.logger.setLevel(config['level'])
        self.logger.propagate = False  # 防止日志重复
        
        # 清除已存在的handler
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 设置日志格式
        self.use_color = use_color
        self.formatter = self._create_formatter(config['log_format'])
        
        # 初始化日志目录
        self.log_dir = log_dir or self._get_default_log_dir()
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        # 移除rotate_when属性
        self.use_rotate_file = use_rotate_file
        
        # 添加handler
        if self.log_dir:
            self._add_file_handler(config['file_level'])
        self._add_console_handler(config['console_level'])
        
        # 记录初始化信息
        self.debug(f"日志系统初始化完成 - 类型: {log_type}, 名称: {config['name']}")
    
    def _create_formatter(self, log_format: str) -> logging.Formatter:
        """创建日志格式化器"""
        if self.use_color:
            return ColoredFormatter(fmt=log_format, use_color=self.use_color)
        return logging.Formatter(fmt=log_format)
    
    def _get_default_log_dir(self) -> str:
        """获取默认日志目录 - 按日期组织"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        today_date = time.strftime('%Y%m%d', time.localtime())
        return os.path.join(project_root, 'logs', today_date, self.log_type)
    
    def _add_file_handler(self, level: int):
        """添加文件handler - 按会话生成独立日志文件"""
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 生成带时间戳的日志文件名，确保每次运行生成新文件
        timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
        # 添加随机后缀避免并发冲突
        import random
        random_suffix = random.randint(1000, 9999)
        log_filename = f"{self.log_type}_{timestamp}_{random_suffix}.log"
        log_file_path = os.path.join(self.log_dir, log_filename)
        
        # 创建文件handler
        if self.use_rotate_file:
            # 使用TimedRotatingFileHandler进行时间轮转
            # 主要用于同一天内的日志文件过大时的自动分割
            file_handler = TimedRotatingFileHandler(
                log_file_path, 
                when='h',  # 按小时轮转
                interval=6,  # 每6小时生成新文件
                backupCount=self.backup_count,
                encoding='utf-8'
            )
        else:
            # 普通文件handler
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8', mode='a')
        
        file_handler.setLevel(level)
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
        
        # 记录日志文件路径信息
        self.debug(f"日志文件已创建: {log_file_path}")
    
    def _add_console_handler(self, level: int):
        """添加控制台handler"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
    
    def _log_with_type(self, level: str, message: str, extra: Dict[str, Any] = None):
        """带类型的日志记录"""
        if extra is None:
            extra = {}
        extra['log_type'] = self.log_type
        
        if level == 'debug':
            self.logger.debug(message, extra=extra)
        elif level == 'info':
            self.logger.info(message, extra=extra)
        elif level == 'warning':
            self.logger.warning(message, extra=extra)
        elif level == 'error':
            self.logger.error(message, extra=extra)
        elif level == 'critical':
            self.logger.critical(message, extra=extra)
    
    def debug(self, message: str, extra: Dict[str, Any] = None):
        """记录debug级别日志"""
        self._log_with_type('debug', message, extra)
    
    def info(self, message: str, extra: Dict[str, Any] = None):
        """记录info级别日志"""
        self._log_with_type('info', message, extra)
    
    def warning(self, message: str, extra: Dict[str, Any] = None):
        """记录warning级别日志"""
        self._log_with_type('warning', message, extra)
    
    def error(self, message: str, extra: Dict[str, Any] = None):
        """记录error级别日志"""
        self._log_with_type('error', message, extra)
    
    def critical(self, message: str, extra: Dict[str, Any] = None):
        """记录critical级别日志"""
        self._log_with_type('critical', message, extra)
    
    def exception(self, message: str, exc_info: bool = True, extra: Dict[str, Any] = None):
        """记录异常日志"""
        if extra is None:
            extra = {}
        extra['log_type'] = self.log_type
        self.logger.error(message, exc_info=exc_info, extra=extra)
    
    def log_request(self, method: str, url: str, request_time: float, status_code: int):
        """记录请求日志"""
        extra = {
            'request_method': method,
            'request_url': url,
            'request_time': request_time,
            'status_code': status_code
        }
        
        if status_code >= 500:
            self.error(f"请求失败 - {method} {url} - {status_code} - {request_time:.3f}s", extra)
        elif status_code >= 400:
            self.warning(f"请求警告 - {method} {url} - {status_code} - {request_time:.3f}s", extra)
        else:
            self.info(f"请求成功 - {method} {url} - {status_code} - {request_time:.3f}s", extra)
    
    def set_level(self, level: int):
        """设置日志级别"""
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)
    
    def get_logger(self, name: str = None, log_type: str = None) -> 'LogUtil':
        """
        获取或创建新的日志实例
        
        Args:
            name: 日志名称
            log_type: 日志类型
            
        Returns:
            LogUtil实例
        """
        if name:
            return LogUtil(
                logger_name=name,
                log_dir=self.log_dir,
                log_type=log_type or self.log_type,
                max_bytes=self.max_bytes,
                backup_count=self.backup_count,
                use_rotate_file=self.use_rotate_file,
                use_color=self.use_color
            )
        return self


# 创建默认日志工具实例
# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 创建框架日志实例
framework_logger = LogUtil(
    logger_name="api_auto",
    log_type='framework',
    use_color=True,
    use_rotate_file=True
)

# 创建用户日志实例
user_logger = LogUtil(
    logger_name="api_auto",
    log_type='user',
    use_color=True,
    use_rotate_file=True
)

# 为了向后兼容，保留logger变量
logger = framework_logger

# 为了向后兼容，保留log函数
log = framework_logger.logger

def get_logger(name: Optional[str] = None, level: int = logging.INFO, log_type: str = 'framework') -> LogUtil:
    """
    获取或创建日志实例
    
    Args:
        name: 日志名称
        level: 日志级别
        log_type: 日志类型 ('framework' 或 'user')
        
    Returns:
        LogUtil实例
    """
    if name:
        logger_instance = LogUtil(
            logger_name=name,
            log_type=log_type,
            use_color=True,
            use_rotate_file=True
        )
        logger_instance.set_level(level)
        return logger_instance
    
    # 根据类型返回不同的logger
    result = framework_logger if log_type == 'framework' else user_logger
    result.set_level(level)
    return result


if __name__ == '__main__':
    # 测试日志功能
    logger.debug("这是一条debug日志")
    logger.info("这是一条info日志")
    logger.warning("这是一条warning日志")
    logger.error("这是一条error日志")
    
    try:
        1/0
    except Exception:
        logger.exception("发生了异常")