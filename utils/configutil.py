#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理工具模块
提供灵活的配置管理功能，支持多环境配置、配置文件加载、环境变量覆盖等
"""

import os
import json
import yaml
import logging
import copy
from typing import Any, Dict, List, Optional, Union, Tuple
import re

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """
    配置错误异常
    """
    pass


class ConfigManager:
    """
    配置管理器
    负责加载、管理和提供配置信息
    """
    
    def __init__(self):
        """
        初始化配置管理器
        """
        # 默认配置
        self._default_config = {}
        # 环境配置
        self._env_configs = {}
        # 当前活动配置
        self._active_config = {}
        # 当前环境
        self._current_env = 'default'
        # 配置文件路径
        self._config_paths = []
        # 环境变量前缀
        self._env_var_prefix = 'API_TEST_'
    
    def load_default_config(self, config: Dict[str, Any]) -> None:
        """
        加载默认配置
        
        Args:
            config: 默认配置字典
        """
        self._default_config = copy.deepcopy(config)
        self._merge_configs()
    
    def load_env_config(self, env: str, config: Dict[str, Any]) -> None:
        """
        加载特定环境的配置
        
        Args:
            env: 环境名称
            config: 环境配置字典
        """
        self._env_configs[env] = copy.deepcopy(config)
        
        # 如果当前环境是加载的环境，重新合并配置
        if env == self._current_env and env != 'default':
            self._merge_configs()
    
    def set_current_env(self, env: str) -> None:
        """
        设置当前环境
        
        Args:
            env: 环境名称
        """
        self._current_env = env
        self._merge_configs()
        logger.info(f"当前环境已切换为: {env}")
    
    def get_current_env(self) -> str:
        """
        获取当前环境
        
        Returns:
            当前环境名称
        """
        return self._current_env
    
    def _merge_configs(self) -> None:
        """
        合并配置：默认配置 + 环境配置 + 环境变量覆盖
        """
        # 从默认配置开始
        merged_config = copy.deepcopy(self._default_config)
        
        # 如果当前环境不是默认环境，合并环境配置
        if self._current_env != 'default' and self._current_env in self._env_configs:
            merged_config = self._deep_merge(merged_config, self._env_configs[self._current_env])
        
        # 应用环境变量覆盖
        env_overrides = self._load_env_var_overrides()
        if env_overrides:
            merged_config = self._deep_merge(merged_config, env_overrides)
        
        # 更新活动配置
        self._active_config = merged_config
    
    def _deep_merge(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个字典
        
        Args:
            dict1: 第一个字典（基础）
            dict2: 第二个字典（覆盖）
            
        Returns:
            合并后的字典
        """
        result = copy.deepcopy(dict1)
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                result[key] = self._deep_merge(result[key], value)
            else:
                # 直接覆盖
                result[key] = copy.deepcopy(value)
        
        return result
    
    def _load_env_var_overrides(self) -> Dict[str, Any]:
        """
        从环境变量加载配置覆盖
        环境变量格式：API_TEST_{SECTION}_{KEY}=value
        支持嵌套配置，使用下划线分隔：API_TEST_DB_SETTINGS_HOST=localhost
        
        Returns:
            环境变量覆盖配置字典
        """
        overrides = {}
        
        for env_var, value in os.environ.items():
            if not env_var.startswith(self._env_var_prefix):
                continue
            
            # 移除前缀
            config_key = env_var[len(self._env_var_prefix):]
            
            # 解析嵌套键
            key_parts = config_key.lower().split('_')
            current_dict = overrides
            
            # 构建嵌套字典
            for i, part in enumerate(key_parts[:-1]):
                if part not in current_dict:
                    current_dict[part] = {}
                current_dict = current_dict[part]
            
            # 设置最终值，尝试转换类型
            final_key = key_parts[-1]
            current_dict[final_key] = self._convert_env_var_value(value)
        
        return overrides
    
    def _convert_env_var_value(self, value: str) -> Any:
        """
        尝试将环境变量值转换为适当的类型
        
        Args:
            value: 环境变量字符串值
            
        Returns:
            转换后的值
        """
        # 处理布尔值
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        
        # 处理None
        if value.lower() == 'none':
            return None
        
        # 处理数字
        try:
            # 尝试整数
            return int(value)
        except ValueError:
            try:
                # 尝试浮点数
                return float(value)
            except ValueError:
                pass
        
        # 处理JSON字符串
        if (value.startswith('{') and value.endswith('}')) or \
           (value.startswith('[') and value.endswith(']')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # 默认返回字符串
        return value
    
    def load_from_file(self, file_path: str, env: Optional[str] = None) -> None:
        """
        从配置文件加载配置
        支持JSON和YAML格式
        
        Args:
            file_path: 配置文件路径
            env: 环境名称，如果为None则根据文件名自动判断
        """
        if not os.path.exists(file_path):
            raise ConfigError(f"配置文件不存在: {file_path}")
        
        # 记录配置文件路径
        if file_path not in self._config_paths:
            self._config_paths.append(file_path)
        
        # 确定环境
        if env is None:
            # 尝试从文件名提取环境
            file_name = os.path.basename(file_path)
            # 匹配 config.${env}.json 或 config_${env}.yaml 等模式
            match = re.search(r'[._](\w+)[.](json|yaml|yml)$', file_name)
            if match:
                env = match.group(1)
            else:
                env = 'default'
        
        # 加载文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                if file_path.endswith('.json'):
                    config = json.load(f)
                elif file_path.endswith(('.yaml', '.yml')):
                    config = yaml.safe_load(f)
                else:
                    raise ConfigError(f"不支持的配置文件格式: {file_path}")
            except Exception as e:
                raise ConfigError(f"加载配置文件失败 {file_path}: {str(e)}")
        
        # 加载配置
        if env == 'default':
            self.load_default_config(config)
        else:
            self.load_env_config(env, config)
        
        logger.info(f"已从 {file_path} 加载 {env} 环境配置")
    
    def load_from_directory(self, directory: str) -> None:
        """
        从目录加载所有配置文件
        
        Args:
            directory: 配置文件目录
        """
        if not os.path.exists(directory):
            raise ConfigError(f"配置目录不存在: {directory}")
        
        # 获取目录中的所有配置文件
        config_files = []
        for file_name in os.listdir(directory):
            if file_name.endswith(('.json', '.yaml', '.yml')):
                config_files.append(os.path.join(directory, file_name))
        
        # 按优先级排序加载
        # 1. 先加载默认配置 config.json 或 config.yaml
        default_files = [f for f in config_files if os.path.basename(f) in ('config.json', 'config.yaml', 'config.yml')]
        for file_path in default_files:
            self.load_from_file(file_path, 'default')
        
        # 2. 再加载环境特定配置
        env_files = [f for f in config_files if os.path.basename(f) not in ('config.json', 'config.yaml', 'config.yml')]
        for file_path in env_files:
            self.load_from_file(file_path)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        支持点分隔的嵌套键访问，如 'database.host'
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._active_config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        支持点分隔的嵌套键设置
        
        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split('.')
        config = self._active_config
        
        # 导航到目标键的父级
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
    
    def has(self, key: str) -> bool:
        """
        检查配置是否包含指定键
        
        Args:
            key: 配置键
            
        Returns:
            是否包含
        """
        keys = key.split('.')
        value = self._active_config
        
        try:
            for k in keys:
                value = value[k]
            return True
        except (KeyError, TypeError):
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            完整配置字典
        """
        return copy.deepcopy(self._active_config)
    
    def export_config(self, file_path: str) -> None:
        """
        导出当前配置到文件
        
        Args:
            file_path: 输出文件路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            if file_path.endswith('.json'):
                json.dump(self._active_config, f, ensure_ascii=False, indent=2)
            elif file_path.endswith(('.yaml', '.yml')):
                yaml.dump(self._active_config, f, allow_unicode=True, default_flow_style=False)
            else:
                raise ConfigError(f"不支持的导出格式: {file_path}")
        
        logger.info(f"配置已导出到: {file_path}")
    
    def set_env_var_prefix(self, prefix: str) -> None:
        """
        设置环境变量前缀
        
        Args:
            prefix: 环境变量前缀
        """
        self._env_var_prefix = prefix
        # 重新加载环境变量覆盖
        self._merge_configs()
    
    def get_config_paths(self) -> List[str]:
        """
        获取已加载的配置文件路径
        
        Returns:
            配置文件路径列表
        """
        return self._config_paths.copy()
    
    def get_environments(self) -> List[str]:
        """
        获取可用的环境列表
        
        Returns:
            环境名称列表
        """
        envs = ['default']
        envs.extend(list(self._env_configs.keys()))
        return list(set(envs))  # 去重
    
    def resolve_variables(self, value: Any) -> Any:
        """
        解析配置值中的变量引用
        支持 ${key} 格式的变量引用
        
        Args:
            value: 原始值
            
        Returns:
            解析后的值
        """
        if isinstance(value, str):
            # 查找所有 ${key} 格式的变量
            pattern = r'\$\{([^}]+)\}'
            
            def replace_var(match):
                var_key = match.group(1)
                var_value = self.get(var_key)
                if var_value is None:
                    # 如果变量不存在，保留原始字符串
                    return match.group(0)
                return str(var_value)
            
            # 替换所有变量
            result = re.sub(pattern, replace_var, value)
            return result
        elif isinstance(value, dict):
            # 递归解析字典
            return {k: self.resolve_variables(v) for k, v in value.items()}
        elif isinstance(value, list):
            # 递归解析列表
            return [self.resolve_variables(item) for item in value]
        else:
            # 其他类型直接返回
            return value
    
    def validate_config(self, schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证配置是否符合指定的模式
        
        Args:
            schema: 配置模式字典
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        def validate_section(config: Dict[str, Any], schema_section: Dict[str, Any], path: str = ''):
            for key, expected_type in schema_section.items():
                full_path = f"{path}.{key}" if path else key
                
                if key not in config:
                    errors.append(f"缺少必要配置: {full_path}")
                    continue
                
                actual_value = config[key]
                
                # 处理类型验证
                if isinstance(expected_type, type):
                    if not isinstance(actual_value, expected_type):
                        errors.append(f"配置类型错误: {full_path} 应为 {expected_type.__name__}，实际为 {type(actual_value).__name__}")
                elif isinstance(expected_type, dict):
                    if not isinstance(actual_value, dict):
                        errors.append(f"配置类型错误: {full_path} 应为字典，实际为 {type(actual_value).__name__}")
                    else:
                        # 递归验证嵌套配置
                        validate_section(actual_value, expected_type, full_path)
                elif isinstance(expected_type, list):
                    if not isinstance(actual_value, list):
                        errors.append(f"配置类型错误: {full_path} 应为列表，实际为 {type(actual_value).__name__}")
                # 可以扩展支持更多验证规则
        
        # 开始验证
        validate_section(self._active_config, schema)
        
        return len(errors) == 0, errors


class ConfigLoader:
    """
    配置加载器
    提供便捷的配置加载功能
    """
    
    @staticmethod
    def load_config(config_dir: str = 'config', 
                   env: Optional[str] = None,
                   default_env: str = 'default') -> ConfigManager:
        """
        加载配置
        
        Args:
            config_dir: 配置目录
            env: 目标环境，如果为None则尝试从环境变量获取
            default_env: 默认环境
            
        Returns:
            配置管理器实例
        """
        # 创建配置管理器
        config_manager = ConfigManager()
        
        # 确定要使用的环境
        target_env = env
        if target_env is None:
            # 尝试从环境变量获取
            target_env = os.environ.get('API_TEST_ENV', default_env)
        
        # 加载配置文件
        config_path = os.path.abspath(config_dir)
        if os.path.exists(config_path):
            config_manager.load_from_directory(config_path)
        else:
            logger.warning(f"配置目录不存在: {config_path}")
        
        # 设置当前环境
        config_manager.set_current_env(target_env)
        
        return config_manager
    
    @staticmethod
    def create_default_config(config_dir: str = 'config') -> None:
        """
        创建默认配置文件
        
        Args:
            config_dir: 配置目录
        """
        # 创建配置目录
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # 默认配置
        default_config = {
            # HTTP配置
            'http': {
                'timeout': 30,
                'max_retries': 3,
                'retry_delay': 1.0,
                'retry_codes': [500, 502, 503, 504],
                'verify_ssl': True,
                'headers': {
                    'User-Agent': 'API-Test-Framework/1.0'
                }
            },
            # 断言配置
            'assertion': {
                'strict_mode': False,
                'fail_fast': True,
                'timeout': 5
            },
            # 日志配置
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': None
            },
            # 报告配置
            'report': {
                'enabled': True,
                'output_dir': 'reports',
                'format': 'json'
            },
            # 环境配置占位符
            'environments': {
                'base_url': 'http://localhost:8000'
            }
        }
        
        # 创建默认配置文件
        config_file = os.path.join(config_dir, 'config.yaml')
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"已创建默认配置文件: {config_file}")
        
        # 创建示例环境配置
        test_config = copy.deepcopy(default_config)
        test_config['environments']['base_url'] = 'https://test-api.example.com'
        
        test_config_file = os.path.join(config_dir, 'config.test.yaml')
        with open(test_config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"已创建测试环境配置文件: {test_config_file}")


class ConfigContext:
    """
    配置上下文管理器
    用于临时修改配置
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化配置上下文管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.original_config = copy.deepcopy(config_manager.get_all())
        self.changes = {}
    
    def __enter__(self):
        """
        进入上下文
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文，恢复原始配置
        """
        # 恢复原始配置
        self.config_manager._active_config = self.original_config
        return False  # 不抑制异常
    
    def set(self, key: str, value: Any) -> 'ConfigContext':
        """
        临时设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            上下文管理器自身，支持链式调用
        """
        self.changes[key] = value
        self.config_manager.set(key, value)
        return self
    
    def set_env(self, env: str) -> 'ConfigContext':
        """
        临时切换环境
        
        Args:
            env: 环境名称
            
        Returns:
            上下文管理器自身，支持链式调用
        """
        self.original_env = self.config_manager.get_current_env()
        self.config_manager.set_current_env(env)
        return self


# 全局配置管理器实例
default_config_manager = ConfigManager()


# 便捷函数
def get_config(key: str, default: Any = None) -> Any:
    """
    便捷函数：从默认配置管理器获取配置
    
    Args:
        key: 配置键
        default: 默认值
        
    Returns:
        配置值
    """
    return default_config_manager.get(key, default)


def set_config(key: str, value: Any) -> None:
    """
    便捷函数：设置默认配置管理器的配置
    
    Args:
        key: 配置键
        value: 配置值
    """
    default_config_manager.set(key, value)


def load_config(config_dir: str = 'config', 
               env: Optional[str] = None) -> ConfigManager:
    """
    便捷函数：加载配置
    
    Args:
        config_dir: 配置目录
        env: 目标环境
        
    Returns:
        配置管理器实例
    """
    global default_config_manager
    default_config_manager = ConfigLoader.load_config(config_dir, env)
    return default_config_manager


def create_config_context() -> ConfigContext:
    """
    便捷函数：创建配置上下文管理器
    
    Returns:
        配置上下文管理器
    """
    return ConfigContext(default_config_manager)


def resolve_config_variables(value: Any) -> Any:
    """
    便捷函数：解析配置变量
    
    Args:
        value: 原始值
        
    Returns:
        解析后的值
    """
    return default_config_manager.resolve_variables(value)


# 示例用法
if __name__ == "__main__":
    print("=== 配置管理工具示例 ===")
    
    # 创建示例配置
    sample_config = {
        'http': {
            'timeout': 30,
            'base_url': 'http://localhost:8000'
        },
        'database': {
            'host': 'localhost',
            'port': 5432
        }
    }
    
    # 示例1: 基本配置加载和获取
    print("\n示例1: 基本配置加载和获取")
    config_manager = ConfigManager()
    config_manager.load_default_config(sample_config)
    
    # 获取配置
    timeout = config_manager.get('http.timeout')
    base_url = config_manager.get('http.base_url')
    print(f"HTTP超时: {timeout}")
    print(f"基础URL: {base_url}")
    
    # 示例2: 环境配置
    print("\n示例2: 环境配置")
    test_env_config = {
        'http': {
            'base_url': 'https://test-api.example.com',
            'timeout': 60
        }
    }
    
    config_manager.load_env_config('test', test_env_config)
    config_manager.set_current_env('test')
    
    # 获取测试环境配置
    test_timeout = config_manager.get('http.timeout')
    test_base_url = config_manager.get('http.base_url')
    print(f"测试环境HTTP超时: {test_timeout}")
    print(f"测试环境基础URL: {test_base_url}")
    
    # 示例3: 配置变量解析
    print("\n示例3: 配置变量解析")
    config_manager.set('api.endpoint', '${http.base_url}/api/v1')
    resolved_endpoint = config_manager.resolve_variables(config_manager.get('api.endpoint'))
    print(f"解析后的API端点: {resolved_endpoint}")
    
    # 示例4: 配置上下文
    print("\n示例4: 配置上下文")
    with ConfigContext(config_manager) as ctx:
        ctx.set('http.timeout', 120)
        print(f"临时超时设置: {config_manager.get('http.timeout')}")
    
    # 上下文退出后恢复原始值
    print(f"恢复后的超时设置: {config_manager.get('http.timeout')}")
    
    print("\n配置管理工具示例完成")