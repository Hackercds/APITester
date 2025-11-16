#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证工具模块，提供各种认证方式的支持
增强的鉴权管理，支持动态参数和灵活的认证策略
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import random
import string
import time
import fnmatch
from urllib.parse import urlparse
from typing import Optional, Union, Dict, Any, Callable, List

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AuthBase:
    """
    认证基类，所有认证策略的父类
    提供统一的认证接口和基本方法
    """
    
    def authenticate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行认证，更新请求数据
        
        Args:
            request_data: 请求数据
            
        Returns:
            更新后的请求数据
        """
        raise NotImplementedError("子类必须实现authenticate方法")
    
    def _resolve_dynamic_value(self, value: Any) -> Any:
        """
        解析动态值
        
        Args:
            value: 可能是固定值或可调用对象
            
        Returns:
            解析后的值
        """
        if callable(value):
            try:
                return value()
            except Exception as e:
                logger.error(f"执行动态值回调时出错: {str(e)}")
                return value
        return value
    
    def _add_auth_info(self, request_data: Dict[str, Any], auth_info: Dict[str, Any]) -> None:
        """
        添加认证信息到请求数据
        
        Args:
            request_data: 请求数据
            auth_info: 认证信息
        """
        if 'auth_info' not in request_data:
            request_data['auth_info'] = {}
        request_data['auth_info'].update(auth_info)


class NoneAuth(AuthBase):
    """
    无认证策略
    """
    
    def authenticate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        无需认证，直接返回请求数据
        
        Args:
            request_data: 请求数据
            
        Returns:
            原始请求数据
        """
        return request_data


class BasicAuth(AuthBase):
    """
    Basic认证策略
    """
    
    def __init__(self, username: Union[str, Callable], password: Union[str, Callable]):
        """
        初始化Basic认证
        
        Args:
            username: 用户名（支持动态获取）
            password: 密码（支持动态获取）
        """
        self.username = username
        self.password = password
    
    def authenticate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Basic认证
        
        Args:
            request_data: 请求数据
            
        Returns:
            更新后的请求数据
        """
        # 解析动态参数
        username = self._resolve_dynamic_value(self.username)
        password = self._resolve_dynamic_value(self.password)
        
        if not username or not password:
            logger.error("Basic认证需要提供有效的username和password")
            return request_data
        
        # 生成Basic认证头
        auth_str = f"{username}:{password}"
        auth_bytes = auth_str.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        headers = request_data.get('headers', {})
        headers['Authorization'] = f"Basic {auth_base64}"
        request_data['headers'] = headers
        
        self._add_auth_info(request_data, {'type': 'basic', 'username': username})
        return request_data


class TokenAuth(AuthBase):
    """
    Token认证策略
    """
    
    def __init__(self, token: Union[str, Callable], token_type: str = 'Bearer'):
        """
        初始化Token认证
        
        Args:
            token: Token值（支持动态获取）
            token_type: Token类型，默认为Bearer
        """
        self.token = token
        self.token_type = token_type
    
    def authenticate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Token认证
        
        Args:
            request_data: 请求数据
            
        Returns:
            更新后的请求数据
        """
        # 解析动态token
        token = self._resolve_dynamic_value(self.token)
        
        if not token:
            logger.error("Token认证需要提供有效的token")
            return request_data
        
        headers = request_data.get('headers', {})
        headers['Authorization'] = f"{self.token_type} {token}"
        request_data['headers'] = headers
        
        self._add_auth_info(request_data, {'type': 'token', 'token_type': self.token_type})
        return request_data


class OAuth2Auth(AuthBase):
    """
    OAuth2认证策略，支持令牌自动刷新
    """
    
    def __init__(self, 
                 token_func: Optional[Callable] = None,
                 token: Optional[Union[str, Callable]] = None,
                 refresh_token_func: Optional[Callable] = None,
                 token_type: str = 'Bearer',
                 refresh_interval: int = 3600,
                 cache_enabled: bool = True):
        """
        初始化OAuth2认证
        
        Args:
            token_func: 获取token的回调函数
            token: 直接提供的token值（支持动态获取）
            refresh_token_func: 刷新token的回调函数
            token_type: Token类型，默认为Bearer
            refresh_interval: token刷新间隔（秒）
            cache_enabled: 是否启用缓存
        """
        self.token_func = token_func
        self.token = token
        self.refresh_token_func = refresh_token_func
        self.token_type = token_type
        self.refresh_interval = refresh_interval
        self.cache_enabled = cache_enabled
        
        # 缓存相关
        self._cached_token = None
        self._cached_token_data = None
        self._token_expiry = 0
    
    def authenticate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行OAuth2认证
        
        Args:
            request_data: 请求数据
            
        Returns:
            更新后的请求数据
        """
        current_time = time.time()
        token = None
        
        # 检查缓存
        if self.cache_enabled and self._cached_token and current_time < self._token_expiry:
            token = self._cached_token
            token_data = self._cached_token_data
        else:
            # 获取新token
            token_data = self._get_token_data()
            if token_data:
                if isinstance(token_data, dict):
                    token = token_data.get('access_token') or token_data.get('token')
                    # 更新缓存
                    if self.cache_enabled:
                        self._cached_token = token
                        self._cached_token_data = token_data
                        expires_in = token_data.get('expires_in', self.refresh_interval)
                        # 提前60秒刷新
                        self._token_expiry = current_time + expires_in - 60
                else:
                    token = token_data
                    # 简单缓存
                    if self.cache_enabled:
                        self._cached_token = token
                        self._cached_token_data = token_data
                        self._token_expiry = current_time + self.refresh_interval - 60
        
        if not token:
            logger.warning("OAuth2认证未获取到有效token")
            return request_data
        
        headers = request_data.get('headers', {})
        headers['Authorization'] = f"{self.token_type} {token}"
        request_data['headers'] = headers
        
        self._add_auth_info(request_data, {'type': 'oauth2', 'token_type': self.token_type})
        return request_data
    
    def _get_token_data(self) -> Any:
        """
        获取token数据
        
        Returns:
            token数据
        """
        # 优先使用token_func
        if self.token_func:
            try:
                return self.token_func()
            except Exception as e:
                logger.error(f"执行token_func时出错: {str(e)}")
        
        # 使用直接提供的token
        if self.token:
            return self._resolve_dynamic_value(self.token)
        
        return None
    
    def force_refresh(self) -> Any:
        """
        强制刷新token
        
        Returns:
            新的token数据
        """
        # 清除缓存
        self._cached_token = None
        self._cached_token_data = None
        self._token_expiry = 0
        
        # 如果有refresh_token_func，使用它
        if self.refresh_token_func:
            try:
                return self.refresh_token_func()
            except Exception as e:
                logger.error(f"执行refresh_token_func时出错: {str(e)}")
        
        # 否则使用常规获取方式
        return self._get_token_data()


class HMACAuth(AuthBase):
    """
    HMAC认证策略
    """
    
    def __init__(self, 
                 secret_key: Union[str, Callable],
                 algorithm: str = 'sha256',
                 nonce_length: Union[int, List[int]] = 8,
                 include_timestamp: bool = True,
                 include_nonce: bool = True,
                 sign_fields: List[str] = None,
                 timestamp_format: str = 'second',
                 timestamp_header: str = 'X-Timestamp',
                 nonce_header: str = 'X-Nonce',
                 signature_header: str = 'X-Signature',
                 file_md5_field: str = 'file_md5'):
        """
        初始化HMAC认证
        
        Args:
            secret_key: 密钥（支持动态获取）
            algorithm: 哈希算法，默认为'sha256'
            nonce_length: nonce长度，可以是单个整数或整数列表
            include_timestamp: 是否包含时间戳，默认为True
            include_nonce: 是否包含nonce，默认为True
            sign_fields: 要包含在签名中的字段列表
            timestamp_format: 时间戳格式，'second'或'millisecond'
            timestamp_header: 时间戳头名称
            nonce_header: nonce头名称
            signature_header: 签名头名称
            file_md5_field: 文件MD5字段名
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.nonce_length = nonce_length
        self.include_timestamp = include_timestamp
        self.include_nonce = include_nonce
        self.sign_fields = sign_fields or ['timestamp', 'body', 'nonce', 'method', 'path']
        self.timestamp_format = timestamp_format
        self.timestamp_header = timestamp_header
        self.nonce_header = nonce_header
        self.signature_header = signature_header
        self.file_md5_field = file_md5_field
        
        # 算法映射
        self.algorithm_map = {
            'sha256': hashlib.sha256,
            'sha1': hashlib.sha1,
            'sha512': hashlib.sha512,
            'md5': hashlib.md5
        }
    
    def authenticate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行HMAC认证
        
        Args:
            request_data: 请求数据
            
        Returns:
            更新后的请求数据
        """
        # 解析动态密钥
        secret_key = self._resolve_dynamic_value(self.secret_key)
        
        if not secret_key:
            logger.error("HMAC认证需要提供有效的secret_key")
            return request_data
        
        # 准备时间戳
        timestamp = self._generate_timestamp() if self.include_timestamp else None
        
        # 准备nonce
        nonce = self._generate_nonce() if self.include_nonce else None
        
        # 获取请求方法和路径
        method = request_data.get('method', 'GET').upper()
        url = request_data.get('url', '')
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # 处理请求体或文件
        body_content = self._get_body_content(request_data)
        
        # 构建签名字符串
        sign_str = self._build_sign_string(timestamp, nonce, method, path, body_content)
        
        # 计算HMAC签名
        signature = self._calculate_hmac(sign_str, secret_key)
        
        # 添加认证头
        self._add_auth_headers(request_data, timestamp, nonce, signature)
        
        # 保存认证信息
        auth_info = {
            'type': 'hmac',
            'algorithm': self.algorithm,
            'sign_str': sign_str,
            'signature': signature,
            'timestamp': timestamp,
            'nonce': nonce
        }
        self._add_auth_info(request_data, auth_info)
        
        return request_data
    
    def _generate_timestamp(self) -> str:
        """
        生成时间戳
        
        Returns:
            时间戳字符串
        """
        if self.timestamp_format == 'millisecond':
            return str(int(time.time() * 1000))
        return str(int(time.time()))
    
    def _generate_nonce(self) -> str:
        """
        生成随机nonce
        
        Returns:
            nonce字符串
        """
        # 支持多种长度的nonce
        if isinstance(self.nonce_length, list):
            selected_length = random.choice(self.nonce_length)
        else:
            selected_length = self.nonce_length
        
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(selected_length))
    
    def _get_body_content(self, request_data: Dict[str, Any]) -> str:
        """
        获取请求体内容
        
        Args:
            request_data: 请求数据
            
        Returns:
            处理后的请求体内容字符串
        """
        # 检查是否有文件上传
        files = request_data.get('files')
        if files:
            file_md5 = self._calculate_file_md5s(files)
            logger.debug(f"文件上传场景，计算的MD5: {file_md5}")
            return file_md5
        
        # JSON数据
        elif 'json_data' in request_data and request_data['json_data'] is not None:
            return json.dumps(request_data['json_data'], sort_keys=True, ensure_ascii=False)
        
        # 表单数据或其他数据
        elif 'data' in request_data and request_data['data'] is not None:
            data = request_data['data']
            if isinstance(data, dict):
                # 排序键以确保一致性
                sorted_items = sorted(data.items())
                return '&'.join([f"{k}={v}" for k, v in sorted_items])
            return str(data)
        
        return ''
    
    def _build_sign_string(self, 
                          timestamp: Optional[str],
                          nonce: Optional[str],
                          method: str,
                          path: str,
                          body_content: str) -> str:
        """
        构建签名字符串
        
        Args:
            timestamp: 时间戳
            nonce: 随机字符串
            method: 请求方法
            path: 请求路径
            body_content: 请求体内容
            
        Returns:
            签名字符串
        """
        sign_parts = []
        
        for field in self.sign_fields:
            if field == 'timestamp' and timestamp:
                sign_parts.append(timestamp)
            elif field == 'nonce' and nonce:
                sign_parts.append(nonce)
            elif field == 'method':
                sign_parts.append(method)
            elif field == 'path':
                sign_parts.append(path)
            elif field == 'body':
                sign_parts.append(body_content)
        
        sign_str = ''.join(sign_parts)
        logger.debug(f"构建的签名字符串: {sign_str}")
        return sign_str
    
    def _calculate_hmac(self, message: str, secret_key: str) -> str:
        """
        计算HMAC签名
        
        Args:
            message: 要签名的消息
            secret_key: 密钥
            
        Returns:
            签名后的字符串
        """
        hash_func = self.algorithm_map.get(self.algorithm.lower())
        if not hash_func:
            logger.error(f"不支持的算法: {self.algorithm}")
            return ''
        
        try:
            h = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hash_func)
            return base64.b64encode(h.digest()).decode('utf-8')
        except Exception as e:
            logger.error(f"计算HMAC时出错: {str(e)}")
            return ''
    
    def _add_auth_headers(self, 
                         request_data: Dict[str, Any],
                         timestamp: Optional[str],
                         nonce: Optional[str],
                         signature: str) -> None:
        """
        添加认证头信息
        
        Args:
            request_data: 请求数据
            timestamp: 时间戳
            nonce: 随机字符串
            signature: 签名
        """
        headers = request_data.get('headers', {})
        
        if timestamp:
            headers[self.timestamp_header] = timestamp
        if nonce:
            headers[self.nonce_header] = nonce
        headers[self.signature_header] = signature
        
        request_data['headers'] = headers
    
    def _calculate_file_md5s(self, files: Any) -> str:
        """
        计算文件的MD5值（支持单个或多个文件）
        
        Args:
            files: 文件对象或文件列表
            
        Returns:
            文件MD5值的字符串表示
        """
        md5s = []
        
        try:
            # 处理不同格式的文件参数
            if isinstance(files, dict):
                # 格式: {'field_name': file_object}
                for field_name, file_item in files.items():
                    file_md5 = self._get_file_md5(file_item)
                    if file_md5:
                        md5s.append(f"{field_name}:{file_md5}")
            elif isinstance(files, list):
                # 格式: [('field_name', file_object), ...]
                for field_name, file_item in files:
                    file_md5 = self._get_file_md5(file_item)
                    if file_md5:
                        md5s.append(f"{field_name}:{file_md5}")
            else:
                # 单个文件对象
                file_md5 = self._get_file_md5(files)
                if file_md5:
                    md5s.append(file_md5)
        except Exception as e:
            logger.error(f"处理文件时出错: {str(e)}")
        
        # 排序并组合
        md5s.sort()
        return '|'.join(md5s)
    
    def _get_file_md5(self, file_item: Any) -> Optional[str]:
        """
        获取单个文件的MD5值
        
        Args:
            file_item: 文件对象、文件路径或元组
            
        Returns:
            文件的MD5值或None
        """
        try:
            # 检查是否为元组格式 ('filename', file_object)
            if isinstance(file_item, tuple) and len(file_item) >= 2:
                file_obj = file_item[1]
            else:
                file_obj = file_item
            
            # 检查是否为文件路径字符串
            if isinstance(file_obj, str):
                if os.path.exists(file_obj):
                    return self._calculate_file_path_md5(file_obj)
                else:
                    logger.warning(f"文件不存在: {file_obj}")
                    return None
            
            # 尝试处理文件对象
            try:
                # 保存当前位置
                current_pos = file_obj.tell()
                # 移动到文件开头
                file_obj.seek(0)
                # 计算MD5
                md5_hash = hashlib.md5()
                while chunk := file_obj.read(8192):
                    md5_hash.update(chunk)
                # 恢复位置
                file_obj.seek(current_pos)
                return md5_hash.hexdigest()
            except Exception:
                # 如果无法操作文件对象，返回随机值
                logger.warning("无法读取文件对象，使用随机值代替")
                return self._generate_nonce(16)
        except Exception as e:
            logger.error(f"计算文件MD5时出错: {str(e)}")
            return None
    
    def _calculate_file_path_md5(self, file_path: str) -> Optional[str]:
        """
        计算文件路径对应的MD5值
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件的MD5值或None
        """
        try:
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算文件 {file_path} 的MD5时出错: {str(e)}")
            return None


class DynamicHMACAuth(HMACAuth):
    """
    动态HMAC认证策略，支持根据路径选择不同的密钥
    """
    
    def __init__(self, 
                 default_secret_key: Union[str, Callable],
                 path_keys: Dict[str, Union[str, Dict[str, Any]]],
                 **kwargs):
        """
        初始化动态HMAC认证
        
        Args:
            default_secret_key: 默认密钥
            path_keys: 路径到密钥的映射
            **kwargs: 其他HMAC认证参数
        """
        super().__init__(default_secret_key, **kwargs)
        self.path_keys = path_keys
        self.default_secret_key = default_secret_key
    
    def authenticate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行动态HMAC认证
        
        Args:
            request_data: 请求数据
            
        Returns:
            更新后的请求数据
        """
        # 获取路径
        url = request_data.get('url', '')
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # 查找路径对应的密钥和配置
        secret_key = self.default_secret_key
        path_config = None
        
        # 精确匹配
        if path in self.path_keys:
            path_config = self.path_keys[path]
            logger.debug(f"路径 {path} 找到精确匹配")
        else:
            # 前缀匹配和通配符匹配
            for pattern, config in self.path_keys.items():
                if path.startswith(pattern) or fnmatch.fnmatch(path, pattern):
                    path_config = config
                    logger.debug(f"路径 {path} 匹配模式 {pattern}")
                    break
        
        # 应用路径特定配置
        temp_config = {}
        if path_config:
            if isinstance(path_config, str):
                secret_key = path_config
            elif isinstance(path_config, dict):
                secret_key = path_config.get('secret_key', self.default_secret_key)
                # 临时保存并应用其他配置
                for key, value in path_config.items():
                    if key != 'secret_key' and hasattr(self, key):
                        temp_config[key] = getattr(self, key)
                        setattr(self, key, value)
        
        # 解析动态密钥
        secret_key = self._resolve_dynamic_value(secret_key)
        self.secret_key = secret_key
        
        # 执行认证
        result = super().authenticate(request_data)
        
        # 恢复原始配置
        for key, value in temp_config.items():
            setattr(self, key, value)
        
        return result


class AuthManager:
    """
    认证管理器，统一管理多种认证方式
    提供更灵活的认证策略选择和动态参数支持
    """
    
    def __init__(self, auth_type: str = 'none', **kwargs):
        """
        初始化认证管理器
        
        Args:
            auth_type: 认证类型，支持以下值：
                - 'none': 无认证
                - 'basic': Basic认证
                - 'token': Token认证
                - 'oauth2': OAuth2认证
                - 'hmac': HMAC认证
                - 'hmac_dynamic': 动态HMAC认证
            **kwargs: 认证参数，根据auth_type不同而变化
        """
        self.auth_type = auth_type
        self.auth_params = kwargs
        self.logger = logging.getLogger(__name__)
        self.auth_cache = {}
        self.auth_expiry = {}
        
        # 创建认证策略
        self.auth_strategy = self._create_auth_strategy()
    
    def _create_auth_strategy(self) -> AuthBase:
        """
        创建认证策略实例
        
        Returns:
            认证策略实例
        """
        auth_strategies = {
            'none': lambda: NoneAuth(),
            'basic': lambda: BasicAuth(
                username=self.auth_params.get('username'),
                password=self.auth_params.get('password')
            ),
            'token': lambda: TokenAuth(
                token=self.auth_params.get('token'),
                token_type=self.auth_params.get('token_type', 'Bearer')
            ),
            'oauth2': lambda: OAuth2Auth(
                token_func=self.auth_params.get('token_func'),
                token=self.auth_params.get('token'),
                refresh_token_func=self.auth_params.get('refresh_token_func'),
                token_type=self.auth_params.get('token_type', 'Bearer'),
                refresh_interval=self.auth_params.get('refresh_interval', 3600),
                cache_enabled=self.auth_params.get('cache_enabled', True)
            ),
            'hmac': lambda: HMACAuth(
                secret_key=self.auth_params.get('secret_key'),
                algorithm=self.auth_params.get('algorithm', 'sha256'),
                nonce_length=self.auth_params.get('nonce_length', 8),
                include_timestamp=self.auth_params.get('include_timestamp', True),
                include_nonce=self.auth_params.get('include_nonce', True),
                sign_fields=self.auth_params.get('sign_fields'),
                timestamp_format=self.auth_params.get('timestamp_format', 'second'),
                timestamp_header=self.auth_params.get('timestamp_header', 'X-Timestamp'),
                nonce_header=self.auth_params.get('nonce_header', 'X-Nonce'),
                signature_header=self.auth_params.get('signature_header', 'X-Signature'),
                file_md5_field=self.auth_params.get('file_md5_field', 'file_md5')
            ),
            'hmac_dynamic': lambda: DynamicHMACAuth(
                default_secret_key=self.auth_params.get('default_secret_key'),
                path_keys=self.auth_params.get('path_keys', {}),
                algorithm=self.auth_params.get('algorithm', 'sha256'),
                nonce_length=self.auth_params.get('nonce_length', 8),
                include_timestamp=self.auth_params.get('include_timestamp', True),
                include_nonce=self.auth_params.get('include_nonce', True),
                sign_fields=self.auth_params.get('sign_fields'),
                timestamp_format=self.auth_params.get('timestamp_format', 'second'),
                timestamp_header=self.auth_params.get('timestamp_header', 'X-Timestamp'),
                nonce_header=self.auth_params.get('nonce_header', 'X-Nonce'),
                signature_header=self.auth_params.get('signature_header', 'X-Signature'),
                file_md5_field=self.auth_params.get('file_md5_field', 'file_md5')
            )
        }
        
        strategy_factory = auth_strategies.get(self.auth_type, auth_strategies['none'])
        return strategy_factory()
    
    def add_auth(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加认证信息到请求数据
        
        Args:
            request_data: 请求数据
            
        Returns:
            更新后的请求数据
        """
        try:
            # 深拷贝请求数据以避免修改原始数据
            import copy
            request_copy = copy.deepcopy(request_data)
            
            # 执行认证
            result = self.auth_strategy.authenticate(request_copy)
            
            # 记录认证类型
            if 'auth_info' not in result:
                result['auth_info'] = {}
            result['auth_info']['auth_type'] = self.auth_type
            
            return result
        except Exception as e:
            self.logger.error(f"添加认证时出错: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return request_data
    
    def clear_cache(self) -> None:
        """
        清除认证缓存
        """
        self.auth_cache.clear()
        self.auth_expiry.clear()
        
        # 如果认证策略有缓存，也清除它
        if hasattr(self.auth_strategy, 'force_refresh'):
            self.auth_strategy.force_refresh()
        
        self.logger.info("认证缓存已清除")
    
    def get_auth_info(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取请求的认证信息（用于调试）
        
        Args:
            request_data: 请求数据
            
        Returns:
            认证信息字典
        """
        return request_data.get('auth_info', {})
    
    def update_auth_params(self, **kwargs) -> None:
        """
        更新认证参数并重新创建认证策略
        
        Args:
            **kwargs: 要更新的认证参数
        """
        self.auth_params.update(kwargs)
        self.auth_strategy = self._create_auth_strategy()
        self.logger.info(f"已更新认证参数: {kwargs.keys()}")


class DynamicAuthProvider:
    """
    动态认证提供者，支持运行时获取和刷新认证信息
    增强版支持更多的认证数据格式和更灵活的刷新策略
    """
    
    def __init__(self, 
                 auth_func: Optional[Callable] = None,
                 refresh_interval: int = 3600,
                 on_refresh: Optional[Callable] = None,
                 error_handler: Optional[Callable] = None):
        """
        初始化动态认证提供者
        
        Args:
            auth_func: 获取认证信息的回调函数
            refresh_interval: 刷新间隔（秒）
            on_refresh: 刷新成功后的回调函数
            error_handler: 错误处理回调函数
        """
        self.auth_func = auth_func
        self.refresh_interval = refresh_interval
        self.on_refresh = on_refresh
        self.error_handler = error_handler
        self.last_refresh = 0
        self.auth_data = None
        self.logger = logging.getLogger(__name__)
        self.last_error = None
    
    def get_auth_data(self) -> Any:
        """
        获取认证数据，自动处理刷新
        
        Returns:
            认证数据
        """
        current_time = time.time()
        
        # 需要刷新或首次获取
        if current_time - self.last_refresh >= self.refresh_interval or not self.auth_data:
            try:
                if self.auth_func:
                    self.auth_data = self.auth_func()
                    self.last_refresh = current_time
                    self.last_error = None
                    self.logger.info("成功刷新认证数据")
                    
                    # 调用刷新成功回调
                    if self.on_refresh:
                        try:
                            self.on_refresh(self.auth_data)
                        except Exception as e:
                            self.logger.error(f"执行on_refresh回调时出错: {str(e)}")
                else:
                    self.logger.error("未设置认证回调函数")
                    raise ValueError("未设置认证回调函数")
            except Exception as e:
                self.logger.error(f"获取认证数据时出错: {str(e)}")
                self.last_error = e
                
                # 调用错误处理回调
                if self.error_handler:
                    try:
                        return self.error_handler(e)
                    except Exception as handler_error:
                        self.logger.error(f"执行错误处理回调时出错: {str(handler_error)}")
        
        return self.auth_data
    
    def get_token(self) -> Optional[str]:
        """
        获取token
        
        Returns:
            token字符串或None
        """
        auth_data = self.get_auth_data()
        if not auth_data:
            return None
        
        if isinstance(auth_data, dict):
            # 支持多种token字段名
            return auth_data.get('token') or \
                   auth_data.get('access_token') or \
                   auth_data.get('api_token') or \
                   auth_data.get('key')
        elif isinstance(auth_data, str):
            return auth_data
        return None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        获取认证头信息
        
        Returns:
            认证头字典
        """
        auth_data = self.get_auth_data()
        if not auth_data:
            return {}
        
        if isinstance(auth_data, dict):
            # 如果直接提供了headers字段
            if 'headers' in auth_data:
                return auth_data['headers']
            
            # 尝试构建Bearer token头
            token = self.get_token()
            if token:
                token_type = auth_data.get('token_type', 'Bearer')
                return {'Authorization': f"{token_type} {token}"}
        
        return {}
    
    def force_refresh(self) -> Any:
        """
        强制刷新认证数据
        
        Returns:
            新的认证数据
        """
        self.last_refresh = 0
        return self.get_auth_data()
    
    def get_last_error(self) -> Optional[Exception]:
        """
        获取最后一次错误
        
        Returns:
            异常对象或None
        """
        return self.last_error
    
    def is_valid(self) -> bool:
        """
        检查认证数据是否有效
        
        Returns:
            是否有效
        """
        return self.auth_data is not None and self.last_error is None


# 提供便捷的认证器工厂函数
def create_auth_manager(auth_config: Union[Dict[str, Any], AuthManager]) -> AuthManager:
    """
    创建认证管理器
    
    Args:
        auth_config: 认证配置字典或已存在的AuthManager实例
        
    Returns:
        AuthManager实例
    """
    if isinstance(auth_config, AuthManager):
        return auth_config
    
    if not isinstance(auth_config, dict):
        raise TypeError("auth_config必须是字典或AuthManager实例")
    
    auth_type = auth_config.get('type', 'none')
    # 移除type字段，其他作为kwargs
    auth_params = auth_config.copy()
    auth_params.pop('type', None)
    
    return AuthManager(auth_type=auth_type, **auth_params)


# 提供创建动态认证提供者的便捷函数
def create_dynamic_auth_provider(
    auth_func: Callable,
    refresh_interval: int = 3600,
    on_refresh: Optional[Callable] = None,
    error_handler: Optional[Callable] = None
) -> DynamicAuthProvider:
    """
    创建动态认证提供者
    
    Args:
        auth_func: 获取认证信息的回调函数
        refresh_interval: 刷新间隔（秒）
        on_refresh: 刷新成功后的回调函数
        error_handler: 错误处理回调函数
        
    Returns:
        DynamicAuthProvider实例
    """
    return DynamicAuthProvider(
        auth_func=auth_func,
        refresh_interval=refresh_interval,
        on_refresh=on_refresh,
        error_handler=error_handler
    )


# 示例：创建一个用于获取token的通用函数
def create_token_fetcher(
    url: str,
    method: str = 'POST',
    auth_data: Dict[str, Any] = None,
    token_field: str = 'access_token',
    expires_in_field: str = 'expires_in'
) -> Callable:
    """
    创建一个自动获取token的回调函数
    
    Args:
        url: 获取token的API地址
        method: HTTP方法
        auth_data: 请求数据
        token_field: token字段名
        expires_in_field: 过期时间字段名
        
    Returns:
        可调用的token获取函数
    """
    import requests
    
    def fetch_token():
        try:
            response = requests.request(method, url, json=auth_data)
            response.raise_for_status()
            data = response.json()
            
            # 返回标准格式的token数据
            result = {
                'access_token': data.get(token_field),
                'token_type': data.get('token_type', 'Bearer')
            }
            
            # 如果有过期时间，也包含进去
            if expires_in_field in data:
                result['expires_in'] = data[expires_in_field]
            
            return result
        except Exception as e:
            logger.error(f"获取token失败: {str(e)}")
            raise
    
    return fetch_token


if __name__ == '__main__':
    # 示例1: 基本HMAC认证
    print("=== 基本HMAC认证示例 ===")
    auth_manager = AuthManager(
        auth_type='hmac',
        secret_key='test_secret_key',
        nonce_length=[8, 16, 32],
        sign_fields=['timestamp', 'nonce', 'method', 'path', 'body']
    )
    
    request_data = {
        'method': 'POST',
        'url': 'https://api.example.com/users',
        'json_data': {'name': 'test', 'age': 25},
        'headers': {}
    }
    
    auth_request = auth_manager.add_auth(request_data)
    print("添加认证后的请求头:")
    print(auth_request['headers'])
    print("\n认证信息:")
    print(auth_manager.get_auth_info(auth_request))
    
    # 示例2: 动态参数示例
    print("\n=== 动态参数示例 ===")
    
    def get_dynamic_token():
        # 模拟动态获取token
        print("正在动态获取token...")
        return "dynamic_token_" + str(int(time.time()))
    
    token_auth_manager = AuthManager(
        auth_type='token',
        token=get_dynamic_token,
        token_type='Bearer'
    )
    
    token_request = token_auth_manager.add_auth({'headers': {}})
    print("动态token认证后的请求头:")
    print(token_request['headers'])
    
    # 示例3: 动态HMAC认证
    print("\n=== 动态HMAC认证示例 ===")
    dynamic_hmac_manager = AuthManager(
        auth_type='hmac_dynamic',
        default_secret_key='default_secret',
        path_keys={
            '/api/users': 'users_secret',
            '/api/admin/*': {'secret_key': 'admin_secret', 'algorithm': 'sha512'},
            '/api/public': 'public_secret'
        }
    )
    
    # 测试不同路径
    for path in ['/api/users', '/api/admin/users', '/api/products']:
        test_request = {'method': 'GET', 'url': f'https://api.example.com{path}', 'headers': {}}
        test_auth_request = dynamic_hmac_manager.add_auth(test_request)
        print(f"路径 {path} 的认证头:")
        print(test_auth_request['headers'])
        print()