"""
配置管理模块
提供框架配置、路径管理和环境变量支持
"""
import os
import json
import environ
from typing import Dict, Any, Optional


class ConfigManager:
    """
    配置管理器类
    提供统一的配置访问和管理功能
    """
    
    def __init__(self):
        """
        初始化配置管理器
        """
        # 加载环境变量
        self.env = environ.Env()
        environ.Env.read_env()
        
        # 项目根目录
        self.project_root = self._get_project_root()
        
        # 初始化默认配置
        self._init_default_config()
        
        # 加载自定义配置文件
        self._load_custom_config()
    
    def _get_project_root(self) -> str:
        """
        获取项目根目录
        
        Returns:
            项目根目录绝对路径
        """
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def _init_default_config(self) -> None:
        """
        初始化默认配置
        """
        # 路径配置
        self.paths = {
            'log': os.path.join(self.project_root, 'log'),
            'report': os.path.join(self.project_root, 'report'),
            'config': os.path.join(self.project_root, 'config'),
            'testcase': os.path.join(self.project_root, 'testcase'),
            'utils': os.path.join(self.project_root, 'utils'),
            'common': os.path.join(self.project_root, 'common'),
        }
        
        # 数据库配置 - 优先使用环境变量
        self.db_config = {
            'host': self.env('DB_HOST', default='127.0.0.1'),
            'user': self.env('DB_USER', default='root'),
            'password': self.env('DB_PASSWORD', default='123456'),
            'database': self.env('DB_NAME', default='jwtest1'),
            'port': int(self.env('DB_PORT', default='3306')),
            'charset': self.env('DB_CHARSET', default='utf8'),
        }
        
        # 日志配置
        self.log_config = {
            'level': self.env('LOG_LEVEL', default='INFO'),
            'file_level': self.env('LOG_FILE_LEVEL', default='DEBUG'),
            'console_level': self.env('LOG_CONSOLE_LEVEL', default='INFO'),
            'format': "%(asctime)s - %(name)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s",
        }
        
        # API配置
        self.api_config = {
            'base_url': self.env('API_BASE_URL', default=''),
            'timeout': int(self.env('API_TIMEOUT', default='30')),
            'retry_count': int(self.env('API_RETRY_COUNT', default='3')),
            'retry_delay': float(self.env('API_RETRY_DELAY', default='1.0')),
        }
        
        # 测试配置
        self.test_config = {
            'default_project': self.env('DEFAULT_PROJECT', default='okr-api'),
            'max_workers': int(self.env('MAX_WORKERS', default='4')),
        }
    
    def _load_custom_config(self) -> None:
        """
        加载自定义配置文件
        """
        custom_config_path = os.path.join(self.paths['config'], 'custom_config.json')
        if os.path.exists(custom_config_path):
            try:
                with open(custom_config_path, 'r', encoding='utf-8') as f:
                    custom_config = json.load(f)
                    
                # 更新配置
                if 'db_config' in custom_config:
                    self.db_config.update(custom_config['db_config'])
                if 'log_config' in custom_config:
                    self.log_config.update(custom_config['log_config'])
                if 'api_config' in custom_config:
                    self.api_config.update(custom_config['api_config'])
                if 'test_config' in custom_config:
                    self.test_config.update(custom_config['test_config'])
                    
            except Exception as e:
                print(f"加载自定义配置文件失败: {e}")
    
    def get_path(self, path_type: str) -> str:
        """
        获取指定类型的路径
        
        Args:
            path_type: 路径类型 (log, report, config, testcase, utils, common)
            
        Returns:
            对应的路径
        """
        if path_type in self.paths:
            # 确保目录存在
            os.makedirs(self.paths[path_type], exist_ok=True)
            return self.paths[path_type]
        raise ValueError(f"未知的路径类型: {path_type}")
    
    def get_db_config(self) -> Dict[str, Any]:
        """
        获取数据库配置
        
        Returns:
            数据库配置字典
        """
        return self.db_config.copy()
    
    def get_log_config(self) -> Dict[str, Any]:
        """
        获取日志配置
        
        Returns:
            日志配置字典
        """
        return self.log_config.copy()
    
    def get_api_config(self) -> Dict[str, Any]:
        """
        获取API配置
        
        Returns:
            API配置字典
        """
        return self.api_config.copy()
    
    def get_test_config(self) -> Dict[str, Any]:
        """
        获取测试配置
        
        Returns:
            测试配置字典
        """
        return self.test_config.copy()
    
    def set_config(self, config_type: str, key: str, value: Any) -> None:
        """
        动态设置配置
        
        Args:
            config_type: 配置类型 (db_config, log_config, api_config, test_config)
            key: 配置键
            value: 配置值
        """
        if config_type == 'db_config':
            self.db_config[key] = value
        elif config_type == 'log_config':
            self.log_config[key] = value
        elif config_type == 'api_config':
            self.api_config[key] = value
        elif config_type == 'test_config':
            self.test_config[key] = value
        else:
            raise ValueError(f"未知的配置类型: {config_type}")
    
    def save_custom_config(self) -> None:
        """
        保存自定义配置到文件
        """
        custom_config_path = os.path.join(self.paths['config'], 'custom_config.json')
        try:
            custom_config = {
                'db_config': self.db_config,
                'log_config': self.log_config,
                'api_config': self.api_config,
                'test_config': self.test_config,
            }
            
            with open(custom_config_path, 'w', encoding='utf-8') as f:
                json.dump(custom_config, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存自定义配置失败: {e}")


# 创建全局配置管理器实例
config_manager = ConfigManager()


# 向后兼容的路径获取函数
def get_log_path():
    """
    获取日志目录路径（向后兼容）
    
    Returns:
        日志目录路径
    """
    return config_manager.get_path('log')


def get_report_path():
    """
    获取报告目录路径（向后兼容）
    
    Returns:
        报告目录路径
    """
    return config_manager.get_path('report')


def get_config_path():
    """
    获取配置目录路径（向后兼容）
    
    Returns:
        配置目录路径
    """
    return config_manager.get_path('config')


# 数据库配置（向后兼容）
DB_CONFIG = config_manager.get_db_config()


# 动态参数类
class DynamicParam:
    """
    动态参数类
    用于在测试过程中存储和传递动态参数
    """
    def __init__(self):
        self._params = {}
    
    def set(self, key: str, value: Any) -> None:
        """
        设置动态参数
        
        Args:
            key: 参数名
            value: 参数值
        """
        self._params[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取动态参数
        
        Args:
            key: 参数名
            default: 默认值
            
        Returns:
            参数值或默认值
        """
        return self._params.get(key, default)
    
    def has(self, key: str) -> bool:
        """
        检查参数是否存在
        
        Args:
            key: 参数名
            
        Returns:
            是否存在
        """
        return key in self._params
    
    def clear(self, key: Optional[str] = None) -> None:
        """
        清除参数
        
        Args:
            key: 参数名，为None时清除所有参数
        """
        if key is None:
            self._params.clear()
        elif key in self._params:
            del self._params[key]


# 测试代码
if __name__ == '__main__':
    print(f"项目根目录: {config_manager.project_root}")
    print(f"日志目录: {get_log_path()}")
    print(f"报告目录: {get_report_path()}")
    print(f"数据库配置: {config_manager.get_db_config()}")
    print(f"API配置: {config_manager.get_api_config()}")