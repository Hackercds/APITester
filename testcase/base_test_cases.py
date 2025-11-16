#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础测试用例模块，提供常用的测试用例模板和验证功能
"""

import copy
import json
import logging
import random
import re
import string
from urllib.parse import urlparse

from utils.authutil import AuthManager
from utils.concurrencyutil import ConcurrentExecutor
from utils.requestsutil import HttpClient

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BaseTestCase:
    """
    基础测试用例类
    """
    
    def __init__(self, name="BaseTest", description=""):
        """
        初始化测试用例
        
        Args:
            name: 测试用例名称
            description: 测试用例描述
        """
        self.name = name
        self.description = description
        self.result = {
            "name": name,
            "description": description,
            "status": "pending",  # pending, running, passed, failed, skipped
            "start_time": None,
            "end_time": None,
            "duration": None,
            "error": None,
            "details": {}
        }
        self.http_client = HttpClient()
    
    def setup(self):
        """
        测试前准备
        """
        self.result["start_time"] = self.http_client.get_current_time()
        self.result["status"] = "running"
        logger.info(f"开始执行测试用例: {self.name}")
    
    def teardown(self):
        """
        测试后清理
        """
        self.result["end_time"] = self.http_client.get_current_time()
        if self.result["start_time"]:
            self.result["duration"] = self.result["end_time"] - self.result["start_time"]
        logger.info(f"测试用例 {self.name} 执行完成，状态: {self.result['status']}")
    
    def run(self):
        """
        运行测试用例
        
        Returns:
            测试结果
        """
        try:
            self.setup()
            self.execute()
            if self.result["status"] == "running":
                self.result["status"] = "passed"
        except AssertionError as e:
            self.result["status"] = "failed"
            self.result["error"] = str(e)
            logger.error(f"测试用例 {self.name} 失败: {str(e)}")
        except Exception as e:
            self.result["status"] = "failed"
            self.result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"测试用例 {self.name} 出现异常: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
        finally:
            self.teardown()
        return self.result
    
    def execute(self):
        """
        执行测试逻辑，子类需要实现此方法
        """
        pass
    
    def assert_equal(self, actual, expected, message=""):
        """
        断言相等
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 断言失败消息
        """
        if actual != expected:
            error_msg = message or f"断言失败: 期望 {expected}，实际 {actual}"
            logger.error(error_msg)
            raise AssertionError(error_msg)
    
    def assert_not_equal(self, actual, expected, message=""):
        """
        断言不相等
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 断言失败消息
        """
        if actual == expected:
            error_msg = message or f"断言失败: 期望不等于 {expected}，但实际等于"
            logger.error(error_msg)
            raise AssertionError(error_msg)
    
    def assert_true(self, condition, message=""):
        """
        断言为True
        
        Args:
            condition: 条件
            message: 断言失败消息
        """
        if not condition:
            error_msg = message or "断言失败: 期望为True，但实际为False"
            logger.error(error_msg)
            raise AssertionError(error_msg)
    
    def assert_false(self, condition, message=""):
        """
        断言为False
        
        Args:
            condition: 条件
            message: 断言失败消息
        """
        if condition:
            error_msg = message or "断言失败: 期望为False，但实际为True"
            logger.error(error_msg)
            raise AssertionError(error_msg)
    
    def assert_in(self, item, container, message=""):
        """
        断言item在container中
        
        Args:
            item: 要检查的项
            container: 容器
            message: 断言失败消息
        """
        if item not in container:
            error_msg = message or f"断言失败: {item} 不在 {container} 中"
            logger.error(error_msg)
            raise AssertionError(error_msg)
    
    def assert_not_in(self, item, container, message=""):
        """
        断言item不在container中
        
        Args:
            item: 要检查的项
            container: 容器
            message: 断言失败消息
        """
        if item in container:
            error_msg = message or f"断言失败: {item} 在 {container} 中"
            logger.error(error_msg)
            raise AssertionError(error_msg)
    
    def assert_status_code(self, response, expected_code, message=""):
        """
        断言响应状态码
        
        Args:
            response: 响应对象
            expected_code: 期望的状态码
            message: 断言失败消息
        """
        actual_code = response.get('status_code')
        if actual_code != expected_code:
            error_msg = message or f"状态码不匹配: 期望 {expected_code}，实际 {actual_code}"
            error_msg += f"\n响应内容: {json.dumps(response.get('content'), ensure_ascii=False)}"
            logger.error(error_msg)
            raise AssertionError(error_msg)
    
    def assert_json_contains(self, response, expected_data, message=""):
        """
        断言JSON响应包含指定数据
        
        Args:
            response: 响应对象
            expected_data: 期望包含的数据
            message: 断言失败消息
        """
        content = response.get('content')
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                raise AssertionError(f"响应内容不是有效的JSON: {content}")
        
        if not isinstance(content, dict):
            raise AssertionError(f"响应内容不是JSON对象: {content}")
        
        # 递归检查期望的数据是否都在实际数据中
        def check_contains(actual, expected):
            if isinstance(expected, dict):
                for key, value in expected.items():
                    if key not in actual:
                        return False, key
                    if isinstance(value, (dict, list)):
                        result, missing = check_contains(actual[key], value)
                        if not result:
                            return False, f"{key}.{missing}"
                    elif actual[key] != value:
                        return False, f"{key}: 期望 {value}，实际 {actual[key]}"
            elif isinstance(expected, list):
                if len(expected) > len(actual):
                    return False, f"列表长度不匹配: 期望至少 {len(expected)}，实际 {len(actual)}"
                for i, item in enumerate(expected):
                    if isinstance(item, (dict, list)):
                        result, missing = check_contains(actual[i], item)
                        if not result:
                            return False, f"[{i}].{missing}"
                    elif actual[i] != item:
                        return False, f"[{i}]: 期望 {item}，实际 {actual[i]}"
            else:
                return actual == expected, None
            return True, None
        
        result, missing = check_contains(content, expected_data)
        if not result:
            error_msg = message or f"JSON响应缺少或不匹配: {missing}"
            logger.error(error_msg)
            raise AssertionError(error_msg)


class AuthTest(BaseTestCase):
    """
    鉴权测试用例基类
    """
    
    def __init__(self, name="AuthTest", description="鉴权测试", 
                 base_url="", endpoint="", method="GET", auth_config=None):
        """
        初始化鉴权测试用例
        
        Args:
            name: 测试用例名称
            description: 测试用例描述
            base_url: 基础URL
            endpoint: 接口路径
            method: HTTP方法
            auth_config: 认证配置
        """
        super().__init__(name, description)
        self.base_url = base_url
        self.endpoint = endpoint
        self.method = method
        self.auth_config = auth_config or {"type": "none"}
        
        # 根据认证配置创建AuthManager
        self.auth_manager = AuthManager(**self.auth_config)
        self.http_client.auth_manager = self.auth_manager
    
    def _get_url(self):
        """
        获取完整的URL
        
        Returns:
            完整的URL字符串
        """
        if self.base_url.endswith('/') and self.endpoint.startswith('/'):
            return self.base_url + self.endpoint[1:]
        elif not self.base_url.endswith('/') and not self.endpoint.startswith('/'):
            return self.base_url + '/' + self.endpoint
        else:
            return self.base_url + self.endpoint
    
    def execute(self):
        """
        执行测试逻辑
        """
        # 子类实现具体的测试逻辑
        pass


class AuthParameterTest(AuthTest):
    """
    鉴权参数验证测试
    """
    
    def __init__(self, name="AuthParameterTest", description="鉴权参数验证测试",
                 base_url="", endpoint="", method="GET", auth_config=None):
        """
        初始化鉴权参数验证测试
        """
        super().__init__(name, description, base_url, endpoint, method, auth_config)
    
    def execute(self):
        """
        执行鉴权参数验证测试
        """
        # 1. 正常鉴权请求
        logger.info("测试1: 正常鉴权请求")
        request_data = {
            "method": self.method,
            "url": self._get_url(),
            "headers": {}
        }
        
        # 添加认证信息
        auth_request = self.auth_manager.add_auth(copy.deepcopy(request_data))
        
        # 验证认证头是否被正确添加
        auth_info = self.auth_manager.get_auth_info(auth_request)
        headers = auth_request.get('headers', {})
        
        # 根据认证类型验证
        if self.auth_config.get('type') == 'hmac' or self.auth_config.get('type') == 'hmac_dynamic':
            self._verify_hmac_auth(headers, auth_info)
        elif self.auth_config.get('type') == 'basic':
            self._verify_basic_auth(headers)
        elif self.auth_config.get('type') == 'token':
            self._verify_token_auth(headers)
        
        # 2. 发送实际请求（可选）
        # response = self.http_client.send_request(**auth_request)
        # self.assert_status_code(response, 200)
        
        logger.info("鉴权参数验证测试通过")
    
    def _verify_hmac_auth(self, headers, auth_info):
        """
        验证HMAC认证
        """
        # 验证必要的头信息
        timestamp_header = self.auth_config.get('timestamp_header', 'X-Timestamp')
        nonce_header = self.auth_config.get('nonce_header', 'X-Nonce')
        signature_header = self.auth_config.get('signature_header', 'X-Signature')
        
        self.assert_in(timestamp_header, headers, f"缺少HMAC认证头: {timestamp_header}")
        self.assert_in(nonce_header, headers, f"缺少HMAC认证头: {nonce_header}")
        self.assert_in(signature_header, headers, f"缺少HMAC认证头: {signature_header}")
        
        # 验证nonce长度
        nonce = headers[nonce_header]
        nonce_length = self.auth_config.get('nonce_length', 8)
        if isinstance(nonce_length, int):
            self.assertEqual(len(nonce), nonce_length, f"Nonce长度不匹配: 期望 {nonce_length}，实际 {len(nonce)}")
        elif isinstance(nonce_length, list):
            self.assert_in(len(nonce), nonce_length, f"Nonce长度不在允许的范围内: {len(nonce)} not in {nonce_length}")
        
        # 验证签名格式（Base64）
        signature = headers[signature_header]
        import base64
        try:
            base64.b64decode(signature)
            is_valid_base64 = True
        except:
            is_valid_base64 = False
        self.assert_true(is_valid_base64, f"HMAC签名不是有效的Base64格式: {signature}")
    
    def _verify_basic_auth(self, headers):
        """
        验证Basic认证
        """
        self.assert_in('Authorization', headers, "缺少Authorization头")
        auth_header = headers['Authorization']
        self.assert_true(auth_header.startswith('Basic '), f"Authorization头不是Basic类型: {auth_header}")
    
    def _verify_token_auth(self, headers):
        """
        验证Token认证
        """
        self.assert_in('Authorization', headers, "缺少Authorization头")
        auth_header = headers['Authorization']
        token_type = self.auth_config.get('token_type', 'Bearer')
        self.assert_true(auth_header.startswith(f'{token_type} '), 
                        f"Authorization头不是{token_type}类型: {auth_header}")


class InvalidAuthTest(AuthTest):
    """
    无效鉴权测试
    """
    
    def __init__(self, name="InvalidAuthTest", description="无效鉴权测试",
                 base_url="", endpoint="", method="GET", auth_config=None,
                 expected_status_code=401):
        """
        初始化无效鉴权测试
        
        Args:
            name: 测试用例名称
            description: 测试用例描述
            base_url: 基础URL
            endpoint: 接口路径
            method: HTTP方法
            auth_config: 认证配置
            expected_status_code: 期望的状态码
        """
        super().__init__(name, description, base_url, endpoint, method, auth_config)
        self.expected_status_code = expected_status_code
    
    def execute(self):
        """
        执行无效鉴权测试
        """
        # 1. 缺少认证
        logger.info("测试1: 缺少认证")
        request_data = {
            "method": self.method,
            "url": self._get_url(),
            "headers": {}
        }
        response = self.http_client.send_request(**request_data)
        self.assert_status_code(response, self.expected_status_code, "缺少认证应该返回401/403")
        
        # 2. 篡改认证信息（如果是HMAC）
        if self.auth_config.get('type') in ['hmac', 'hmac_dynamic']:
            logger.info("测试2: 篡改HMAC认证信息")
            request_data = {
                "method": self.method,
                "url": self._get_url(),
                "headers": {}
            }
            # 添加正确认证
            auth_request = self.auth_manager.add_auth(copy.deepcopy(request_data))
            # 篡改签名
            signature_header = self.auth_config.get('signature_header', 'X-Signature')
            headers = auth_request.get('headers', {})
            if signature_header in headers:
                headers[signature_header] = "invalid_signature"
                # 发送篡改后的请求
                tampered_response = self.http_client.send_request(**auth_request)
                self.assert_status_code(
                    tampered_response, 
                    self.expected_status_code, 
                    "篡改签名后应该返回401/403"
                )


class RequestBodyTest(BaseTestCase):
    """
    请求体验证测试
    """
    
    def __init__(self, name="RequestBodyTest", description="请求体验证测试",
                 base_url="", endpoint="", method="POST", auth_config=None):
        """
        初始化请求体验证测试
        
        Args:
            name: 测试用例名称
            description: 测试用例描述
            base_url: 基础URL
            endpoint: 接口路径
            method: HTTP方法
            auth_config: 认证配置
        """
        super().__init__(name, description)
        self.base_url = base_url
        self.endpoint = endpoint
        self.method = method
        
        # 设置认证
        if auth_config:
            self.http_client.auth_manager = AuthManager(**auth_config)
    
    def _get_url(self):
        """
        获取完整的URL
        """
        if self.base_url.endswith('/') and self.endpoint.startswith('/'):
            return self.base_url + self.endpoint[1:]
        elif not self.base_url.endswith('/') and not self.endpoint.startswith('/'):
            return self.base_url + '/' + self.endpoint
        else:
            return self.base_url + self.endpoint
    
    def execute(self):
        """
        执行请求体验证测试
        """
        # 子类实现具体的测试逻辑
        pass


class RequiredFieldTest(RequestBodyTest):
    """
    必选字段验证测试
    """
    
    def __init__(self, name="RequiredFieldTest", description="必选字段验证测试",
                 base_url="", endpoint="", method="POST", auth_config=None,
                 required_fields=None, sample_data=None):
        """
        初始化必选字段验证测试
        
        Args:
            name: 测试用例名称
            description: 测试用例描述
            base_url: 基础URL
            endpoint: 接口路径
            method: HTTP方法
            auth_config: 认证配置
            required_fields: 必选字段列表
            sample_data: 样本请求数据
        """
        super().__init__(name, description, base_url, endpoint, method, auth_config)
        self.required_fields = required_fields or []
        self.sample_data = sample_data or {}
    
    def execute(self):
        """
        执行必选字段验证测试
        """
        # 1. 正常请求（所有字段都提供）
        logger.info("测试1: 正常请求（所有必选字段都提供）")
        request_data = {
            "method": self.method,
            "url": self._get_url(),
            "json_data": copy.deepcopy(self.sample_data)
        }
        response = self.http_client.send_request(**request_data)
        
        # 记录正常请求的响应状态
        self.result["details"]["normal_request_status"] = response.get('status_code')
        
        # 2. 逐一移除必选字段，验证错误处理
        for field in self.required_fields:
            logger.info(f"测试2: 缺少必选字段 '{field}'")
            # 创建缺少该字段的请求数据
            invalid_data = copy.deepcopy(self.sample_data)
            if field in invalid_data:
                del invalid_data[field]
            
            request_data = {
                "method": self.method,
                "url": self._get_url(),
                "json_data": invalid_data
            }
            
            # 发送请求
            response = self.http_client.send_request(**request_data)
            
            # 记录结果
            field_key = f"missing_field_{field}"
            self.result["details"][field_key] = {
                "status_code": response.get('status_code'),
                "error_message": response.get('content')
            }
            
            # 验证返回400错误
            self.assert_true(
                response.get('status_code') >= 400, 
                f"缺少必选字段 '{field}' 应该返回错误状态码，实际返回 {response.get('status_code')}"
            )


class InvalidFieldTest(RequestBodyTest):
    """
    无效字段值验证测试
    """
    
    def __init__(self, name="InvalidFieldTest", description="无效字段值验证测试",
                 base_url="", endpoint="", method="POST", auth_config=None,
                 field_validations=None, sample_data=None):
        """
        初始化无效字段值验证测试
        
        Args:
            name: 测试用例名称
            description: 测试用例描述
            base_url: 基础URL
            endpoint: 接口路径
            method: HTTP方法
            auth_config: 认证配置
            field_validations: 字段验证配置，格式为 {"field_name": [invalid_value1, invalid_value2...]}
            sample_data: 样本请求数据
        """
        super().__init__(name, description, base_url, endpoint, method, auth_config)
        self.field_validations = field_validations or {}
        self.sample_data = sample_data or {}
    
    def execute(self):
        """
        执行无效字段值验证测试
        """
        # 对每个字段进行无效值测试
        for field_name, invalid_values in self.field_validations.items():
            if field_name not in self.sample_data:
                logger.warning(f"字段 '{field_name}' 不在样本数据中，跳过测试")
                continue
            
            for invalid_value in invalid_values:
                test_name = f"invalid_{field_name}_{str(invalid_value)[:20]}"
                logger.info(f"测试: {test_name}")
                
                # 创建包含无效值的请求数据
                invalid_data = copy.deepcopy(self.sample_data)
                invalid_data[field_name] = invalid_value
                
                request_data = {
                    "method": self.method,
                    "url": self._get_url(),
                    "json_data": invalid_data
                }
                
                # 发送请求
                response = self.http_client.send_request(**request_data)
                
                # 记录结果
                self.result["details"][test_name] = {
                    "status_code": response.get('status_code'),
                    "error_message": response.get('content'),
                    "invalid_value": invalid_value
                }
                
                # 验证返回400错误
                self.assert_true(
                    response.get('status_code') >= 400, 
                    f"字段 '{field_name}' 包含无效值应该返回错误状态码，实际返回 {response.get('status_code')}"
                )


class HeaderValidationTest(BaseTestCase):
    """
    Header验证测试
    """
    
    def __init__(self, name="HeaderValidationTest", description="Header验证测试",
                 base_url="", endpoint="", method="GET", auth_config=None):
        """
        初始化Header验证测试
        
        Args:
            name: 测试用例名称
            description: 测试用例描述
            base_url: 基础URL
            endpoint: 接口路径
            method: HTTP方法
            auth_config: 认证配置
        """
        super().__init__(name, description)
        self.base_url = base_url
        self.endpoint = endpoint
        self.method = method
        
        # 设置认证
        if auth_config:
            self.http_client.auth_manager = AuthManager(**auth_config)
    
    def _get_url(self):
        """
        获取完整的URL
        """
        if self.base_url.endswith('/') and self.endpoint.startswith('/'):
            return self.base_url + self.endpoint[1:]
        elif not self.base_url.endswith('/') and not self.endpoint.startswith('/'):
            return self.base_url + '/' + self.endpoint
        else:
            return self.base_url + self.endpoint
    
    def execute(self):
        """
        执行Header验证测试
        """
        # 1. 缺少必要的Header（如果有）
        logger.info("测试1: 缺少Content-Type Header")
        request_data = {
            "method": self.method,
            "url": self._get_url(),
            "headers": {},
            "json_data": {"test": "data"}
        }
        response = self.http_client.send_request(**request_data)
        self.result["details"]["missing_content_type"] = response.get('status_code')
        
        # 2. 无效的Content-Type
        logger.info("测试2: 无效的Content-Type")
        request_data = {
            "method": self.method,
            "url": self._get_url(),
            "headers": {"Content-Type": "text/plain"},
            "json_data": {"test": "data"}
        }
        response = self.http_client.send_request(**request_data)
        self.result["details"]["invalid_content_type"] = response.get('status_code')
        
        # 3. 特殊字符的Header值
        logger.info("测试3: 特殊字符的Header值")
        request_data = {
            "method": self.method,
            "url": self._get_url(),
            "headers": {"X-Custom-Header": "!@#$%^&*()"}
        }
        response = self.http_client.send_request(**request_data)
        self.result["details"]["special_chars_header"] = response.get('status_code')
        
        # 4. 非常长的Header值
        logger.info("测试4: 非常长的Header值")
        long_value = ''.join(random.choice(string.ascii_letters) for _ in range(1000))
        request_data = {
            "method": self.method,
            "url": self._get_url(),
            "headers": {"X-Long-Header": long_value}
        }
        response = self.http_client.send_request(**request_data)
        self.result["details"]["long_header_value"] = response.get('status_code')


class BatchTestCase(BaseTestCase):
    """
    批量测试用例，用于并行执行多个子测试用例
    """
    
    def __init__(self, name="BatchTest", description="批量测试", 
                 test_cases=None, max_workers=5):
        """
        初始化批量测试用例
        
        Args:
            name: 测试用例名称
            description: 测试用例描述
            test_cases: 测试用例列表
            max_workers: 最大工作线程数
        """
        super().__init__(name, description)
        self.test_cases = test_cases or []
        self.max_workers = max_workers
        self.results = []
    
    def add_test_case(self, test_case):
        """
        添加测试用例
        
        Args:
            test_case: 测试用例对象
        """
        self.test_cases.append(test_case)
    
    def execute(self):
        """
        执行批量测试
        """
        if not self.test_cases:
            logger.warning("批量测试中没有测试用例")
            return
        
        logger.info(f"开始执行批量测试，共 {len(self.test_cases)} 个测试用例")
        
        # 使用并发执行器运行测试用例
        executor = ConcurrentExecutor(
            max_workers=self.max_workers,
            executor_type='thread'
        )
        
        # 提交所有测试用例
        futures = []
        for test_case in self.test_cases:
            future = executor.submit(test_case.run)
            futures.append(future)
        
        # 等待所有测试完成
        for future, test_case in zip(futures, self.test_cases):
            try:
                result = future.result()
                self.results.append(result)
            except Exception as e:
                logger.error(f"测试用例 {test_case.name} 执行出错: {str(e)}")
                error_result = {
                    "name": test_case.name,
                    "status": "failed",
                    "error": str(e)
                }
                self.results.append(error_result)
        
        # 统计结果
        self._summarize_results()
    
    def _summarize_results(self):
        """
        汇总测试结果
        """
        passed = sum(1 for r in self.results if r.get('status') == 'passed')
        failed = sum(1 for r in self.results if r.get('status') == 'failed')
        skipped = sum(1 for r in self.results if r.get('status') == 'skipped')
        
        self.result["details"]["summary"] = {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": (passed / len(self.results) * 100) if self.results else 0
        }
        
        # 如果有失败的测试，标记整个批量测试为失败
        if failed > 0:
            self.result["status"] = "failed"
            self.result["error"] = f"有 {failed} 个测试用例失败"
        
        logger.info(f"批量测试完成: 通过 {passed}, 失败 {failed}, 跳过 {skipped}")
    
    def get_results(self):
        """
        获取所有测试用例的结果
        
        Returns:
            测试结果列表
        """
        return self.results


# 快捷创建测试用例的函数
def create_auth_tests(base_url, endpoints, auth_config):
    """
    批量创建鉴权测试用例
    
    Args:
        base_url: 基础URL
        endpoints: 接口路径列表
        auth_config: 认证配置
        
    Returns:
        测试用例列表
    """
    tests = []
    
    for endpoint in endpoints:
        # 创建正常鉴权测试
        auth_test = AuthParameterTest(
            name=f"AuthTest_{endpoint.replace('/', '_')}",
            description=f"测试 {endpoint} 接口的鉴权参数",
            base_url=base_url,
            endpoint=endpoint,
            auth_config=auth_config
        )
        tests.append(auth_test)
        
        # 创建无效鉴权测试
        invalid_auth_test = InvalidAuthTest(
            name=f"InvalidAuthTest_{endpoint.replace('/', '_')}",
            description=f"测试 {endpoint} 接口的无效鉴权处理",
            base_url=base_url,
            endpoint=endpoint,
            auth_config=auth_config
        )
        tests.append(invalid_auth_test)
    
    return tests


def create_request_body_tests(base_url, endpoint, sample_data, required_fields, field_validations, auth_config=None):
    """
    创建请求体验证测试用例
    
    Args:
        base_url: 基础URL
        endpoint: 接口路径
        sample_data: 样本请求数据
        required_fields: 必选字段列表
        field_validations: 字段验证配置
        auth_config: 认证配置
        
    Returns:
        测试用例列表
    """
    tests = []
    
    # 创建必选字段测试
    required_test = RequiredFieldTest(
        name=f"RequiredFieldTest_{endpoint.replace('/', '_')}",
        description=f"测试 {endpoint} 接口的必选字段验证",
        base_url=base_url,
        endpoint=endpoint,
        method="POST",
        auth_config=auth_config,
        required_fields=required_fields,
        sample_data=sample_data
    )
    tests.append(required_test)
    
    # 创建无效字段测试
    if field_validations:
        invalid_field_test = InvalidFieldTest(
            name=f"InvalidFieldTest_{endpoint.replace('/', '_')}",
            description=f"测试 {endpoint} 接口的无效字段验证",
            base_url=base_url,
            endpoint=endpoint,
            method="POST",
            auth_config=auth_config,
            field_validations=field_validations,
            sample_data=sample_data
        )
        tests.append(invalid_field_test)
    
    # 创建Header验证测试
    header_test = HeaderValidationTest(
        name=f"HeaderValidationTest_{endpoint.replace('/', '_')}",
        description=f"测试 {endpoint} 接口的Header验证",
        base_url=base_url,
        endpoint=endpoint,
        auth_config=auth_config
    )
    tests.append(header_test)
    
    return tests


if __name__ == '__main__':
    # 示例用法
    print("基础测试用例模块示例")
    
    # 创建一个简单的测试用例
    test = BaseTestCase(name="ExampleTest", description="示例测试")
    
    # 设置测试逻辑
    def custom_execute():
        # 模拟测试通过
        print("执行测试逻辑")
    
    test.execute = custom_execute
    
    # 运行测试
    result = test.run()
    print(f"测试结果: {result['status']}")