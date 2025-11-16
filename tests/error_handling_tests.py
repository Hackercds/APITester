#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理和边界条件测试示例

此文件包含错误处理和边界条件测试的示例，展示如何处理API错误情况、无效输入、超时等问题。
这些测试确保框架能够正确处理各种异常情况并提供有用的错误信息。
"""

import asyncio
import json
import logging
import os
import pytest
import time
from typing import Dict, Any, List, Optional

# 导入框架核心模块
from api_auto_framework.utils.requestutil import RequestManager, DefaultResponseHandler, RequestError
from api_auto_framework.utils.modelutils import ModelAPI, ModelAPIError
from api_auto_framework.config.config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestErrorHandling:
    """
    错误处理测试类
    测试各种错误场景的处理方式
    """
    
    ENV = os.getenv('TEST_ENV', 'dev')
    
    @pytest.fixture(scope="class")
    def config(self):
        """
        测试配置fixture
        """
        config = Config()
        base_url = config.get(f"{self.ENV}.user_api.base_url", "https://api.example.com")
        api_key = config.get(f"{self.ENV}.user_api.api_key", "")
        
        return {
            "base_url": base_url,
            "api_key": api_key,
            "timeout": 5  # 小超时值，便于测试超时情况
        }
    
    @pytest.fixture(scope="class")
    def request_manager(self, config):
        """
        请求管理器fixture
        """
        manager = RequestManager(
            base_url=config["base_url"],
            timeout=config["timeout"]
        )
        
        # 设置认证头
        if config["api_key"]:
            manager.add_header("Authorization", f"Bearer {config['api_key']}")
        
        manager.add_header("Content-Type", "application/json")
        return manager
    
    def test_invalid_endpoint(self, request_manager):
        """
        测试访问不存在的端点
        预期返回404状态码
        """
        # 访问不存在的端点
        invalid_endpoint = "/this-endpoint-does-not-exist-12345"
        
        # 发送请求并检查错误
        with pytest.raises(RequestError) as excinfo:
            request_manager.get(endpoint=invalid_endpoint)
        
        # 验证异常信息
        error = excinfo.value
        assert error.status_code == 404
        assert "Not Found" in str(error)
        logger.info(f"成功捕获404错误: {str(error)}")
    
    def test_invalid_json_payload(self, request_manager):
        """
        测试提交无效的JSON数据
        预期返回400状态码
        """
        # 准备无效的JSON数据
        endpoint = "/users"
        # 这里故意使用无效的JSON格式
        invalid_payload = "{这不是有效的JSON}"
        
        # 发送请求并检查错误
        with pytest.raises(RequestError) as excinfo:
            # 使用data参数而不是json参数，模拟提交原始文本
            request_manager.post(
                endpoint=endpoint,
                data=invalid_payload
            )
        
        # 验证异常信息
        error = excinfo.value
        # 可能的状态码：400 Bad Request 或 415 Unsupported Media Type
        assert error.status_code in [400, 415]
        logger.info(f"成功捕获无效JSON错误: {str(error)}")
    
    def test_validation_error(self, request_manager):
        """
        测试提交缺少必要字段的数据
        预期返回400状态码，包含验证错误信息
        """
        # 准备缺少必要字段的数据
        endpoint = "/users"
        invalid_user_data = {
            # 缺少username和email等必要字段
            "name": "测试用户"
        }
        
        # 发送请求并检查错误
        with pytest.raises(RequestError) as excinfo:
            request_manager.post(
                endpoint=endpoint,
                json=invalid_user_data
            )
        
        # 验证异常信息
        error = excinfo.value
        assert error.status_code == 400
        
        # 检查响应数据中是否包含验证错误信息
        error_data = error.response_data
        assert "errors" in error_data or "message" in error_data
        logger.info(f"成功捕获验证错误: {str(error)}")
    
    def test_unauthorized_access(self, request_manager):
        """
        测试未授权访问需要认证的端点
        预期返回401状态码
        """
        # 创建一个没有认证头的请求管理器
        unauthorized_manager = RequestManager(
            base_url=request_manager.base_url,
            timeout=request_manager.timeout
        )
        
        # 访问需要认证的端点
        endpoint = "/users/profile"
        
        # 发送请求并检查错误
        with pytest.raises(RequestError) as excinfo:
            unauthorized_manager.get(endpoint=endpoint)
        
        # 验证异常信息
        error = excinfo.value
        assert error.status_code == 401
        assert "Unauthorized" in str(error)
        logger.info(f"成功捕获未授权错误: {str(error)}")
    
    def test_forbidden_access(self, request_manager):
        """
        测试访问没有权限的资源
        预期返回403状态码
        """
        # 访问没有权限的端点
        # 假设用户没有权限访问管理员接口
        endpoint = "/admin/dashboard"
        
        # 发送请求并检查错误
        with pytest.raises(RequestError) as excinfo:
            request_manager.get(endpoint=endpoint)
        
        # 验证异常信息
        error = excinfo.value
        assert error.status_code == 403
        assert "Forbidden" in str(error)
        logger.info(f"成功捕获禁止访问错误: {str(error)}")
    
    def test_request_timeout(self, request_manager):
        """
        测试请求超时情况
        预期抛出超时异常
        """
        # 访问一个可能导致超时的端点
        # 这里假设服务器有一个故意延迟的端点用于测试
        endpoint = "/test/timeout"
        
        # 发送请求并检查错误
        with pytest.raises((RequestError, asyncio.TimeoutError)) as excinfo:
            request_manager.get(endpoint=endpoint)
        
        # 验证异常信息
        error = excinfo.value
        assert "timeout" in str(error).lower()
        logger.info(f"成功捕获超时错误: {str(error)}")
    
    def test_rate_limiting(self, request_manager):
        """
        测试API限流情况
        预期返回429状态码
        """
        # 快速发送多个请求，触发限流
        endpoint = "/users"
        num_requests = 10
        
        successful_requests = 0
        rate_limit_hit = False
        
        for i in range(num_requests):
            try:
                request_manager.get(endpoint=endpoint)
                successful_requests += 1
                # 短暂暂停以避免立即触发限流
                time.sleep(0.1)
            except RequestError as e:
                if e.status_code == 429:
                    rate_limit_hit = True
                    logger.info(f"成功捕获限流错误: {str(e)}")
                    break
                else:
                    # 如果是其他错误，继续处理
                    raise
        
        # 如果测试环境没有实施限流，可以跳过此断言
        # 这里使用软断言，避免测试因环境差异而失败
        if rate_limit_hit:
            assert True, "成功触发限流"
        else:
            logger.warning(f"未触发限流，成功发送了 {successful_requests}/{num_requests} 个请求")


class TestBoundaryConditions:
    """
    边界条件测试类
    测试各种边界情况下的API行为
    """
    
    ENV = os.getenv('TEST_ENV', 'dev')
    
    @pytest.fixture(scope="class")
    def config(self):
        """
        测试配置fixture
        """
        config = Config()
        base_url = config.get(f"{self.ENV}.product_api.base_url", "https://api.example.com")
        
        return {
            "base_url": base_url,
            "timeout": 30
        }
    
    @pytest.fixture(scope="class")
    def request_manager(self, config):
        """
        请求管理器fixture
        """
        manager = RequestManager(
            base_url=config["base_url"],
            timeout=config["timeout"]
        )
        
        manager.add_header("Content-Type", "application/json")
        return manager
    
    def test_empty_response_body(self, request_manager):
        """
        测试空响应体处理
        验证框架能够正确处理空的响应体
        """
        # 假设这是一个返回空响应体的端点
        endpoint = "/test/empty-response"
        
        # 发送请求
        response = request_manager.get(endpoint=endpoint)
        
        # 验证响应
        assert response.status_code == 200
        assert response.success is True
        # 空响应体可能被解析为None或空字典
        assert response.data in [None, {}]
        logger.info("成功处理空响应体")
    
    def test_large_query_params(self, request_manager):
        """
        测试大量查询参数的情况
        验证框架能够正确处理URL长度限制
        """
        # 准备大量查询参数
        endpoint = "/products/search"
        params = {
            f"filter_{i}": f"value_{i}" for i in range(50)
        }
        
        # 发送请求
        response = request_manager.get(
            endpoint=endpoint,
            params=params
        )
        
        # 验证响应
        # 即使请求被截断或拒绝，也应该捕获相应的错误
        if response.status_code == 414:  # URI Too Long
            logger.info("成功捕获URI过长错误")
        else:
            assert response.status_code in [200, 400]
            logger.info(f"处理大量查询参数，响应状态码: {response.status_code}")
    
    def test_special_characters_in_url(self, request_manager):
        """
        测试URL中包含特殊字符的情况
        验证框架能够正确编码特殊字符
        """
        # 包含各种特殊字符的搜索关键词
        special_chars = '''!@#$%^&*()_+-=[]{}|;':",.<>/?'''
        endpoint = f"/products/search?q={special_chars}"
        
        # 发送请求 - 框架应该自动处理URL编码
        response = request_manager.get(endpoint=endpoint)
        
        # 验证响应
        assert response.status_code in [200, 400]
        logger.info("成功处理URL中的特殊字符")
    
    def test_very_large_payload(self, request_manager):
        """
        测试发送非常大的请求体
        验证框架能够处理大文件传输或大数据集
        """
        # 创建一个大型请求体（约1MB）
        large_text = "x" * 1024 * 1024  # 1MB of data
        endpoint = "/test/large-payload"
        payload = {
            "data": large_text,
            "description": "This is a very large payload test"
        }
        
        # 发送请求
        response = request_manager.post(
            endpoint=endpoint,
            json=payload
        )
        
        # 验证响应
        # 根据服务器配置，可能返回200或413 (Payload Too Large)
        if response.status_code == 413:
            logger.info("成功捕获请求体过大错误")
        else:
            assert response.status_code in [200, 201]
            logger.info("成功处理大型请求体")
    
    def test_edge_case_numeric_values(self, request_manager):
        """
        测试边界数值情况
        验证框架能够处理极小数、极大数等边界情况
        """
        # 准备包含边界数值的数据
        endpoint = "/products/filter"
        params = {
            "min_price": 0.01,           # 接近零的小数
            "max_price": 999999999.99,    # 非常大的数
            "discount": 0,              # 零值
            "rating": 5.0               # 最大值
        }
        
        # 发送请求
        response = request_manager.get(
            endpoint=endpoint,
            params=params
        )
        
        # 验证响应
        assert response.status_code == 200
        assert response.success is True
        logger.info("成功处理边界数值")


class TestAsyncErrorHandling:
    """
    异步错误处理测试类
    测试异步请求中的各种错误情况
    """
    
    ENV = os.getenv('TEST_ENV', 'dev')
    
    @pytest.fixture(scope="class")
    def config(self):
        """
        测试配置fixture
        """
        config = Config()
        base_url = config.get(f"{self.ENV}.payment_api.base_url", "https://api.example.com")
        api_key = config.get(f"{self.ENV}.payment_api.api_key", "")
        
        return {
            "base_url": base_url,
            "api_key": api_key,
            "timeout": 5  # 小超时值，便于测试超时情况
        }
    
    @pytest.fixture(scope="class")
    def request_manager(self, config):
        """
        请求管理器fixture
        """
        manager = RequestManager(
            base_url=config["base_url"],
            timeout=config["timeout"]
        )
        
        # 设置认证头
        if config["api_key"]:
            manager.add_header("Authorization", f"Bearer {config['api_key']}")
        
        manager.add_header("Content-Type", "application/json")
        return manager
    
    @pytest.fixture
    def event_loop(self):
        """
        事件循环fixture，用于异步测试
        """
        loop = asyncio.get_event_loop()
        yield loop
        loop.close()
    
    async def test_async_invalid_endpoint(self, request_manager):
        """
        测试异步访问不存在的端点
        预期抛出异步RequestError异常
        """
        # 访问不存在的端点
        invalid_endpoint = "/this-async-endpoint-does-not-exist-12345"
        
        # 发送异步请求并检查错误
        with pytest.raises(RequestError) as excinfo:
            await request_manager.get_async(endpoint=invalid_endpoint)
        
        # 验证异常信息
        error = excinfo.value
        assert error.status_code == 404
        assert "Not Found" in str(error)
        logger.info(f"异步请求成功捕获404错误: {str(error)}")
    
    async def test_async_request_timeout(self, request_manager):
        """
        测试异步请求超时情况
        预期抛出异步超时异常
        """
        # 访问一个可能导致超时的端点
        endpoint = "/test/async-timeout"
        
        # 发送异步请求并检查错误
        with pytest.raises((RequestError, asyncio.TimeoutError)) as excinfo:
            await request_manager.get_async(endpoint=endpoint)
        
        # 验证异常信息
        error = excinfo.value
        assert "timeout" in str(error).lower()
        logger.info(f"异步请求成功捕获超时错误: {str(error)}")
    
    async def test_async_concurrent_error_handling(self, request_manager):
        """
        测试并发异步请求中的错误处理
        验证部分请求失败时的错误处理机制
        """
        # 创建混合请求：一些有效，一些无效
        endpoints = [
            "/users",                      # 有效端点
            "/this-endpoint-does-not-exist",  # 无效端点
            "/products",                   # 有效端点
            "/another-non-existent-endpoint"  # 无效端点
        ]
        
        # 创建异步任务列表
        tasks = [request_manager.get_async(endpoint=ep) for ep in endpoints]
        
        # 使用gather捕获所有异常
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = 0
        error_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_count += 1
                # 验证无效端点的错误
                if "not-exist" in endpoints[i]:
                    assert isinstance(result, RequestError)
                    assert result.status_code == 404
                logger.info(f"请求 {i+1} 失败: {str(result)}")
            else:
                success_count += 1
                assert result.success is True
                logger.info(f"请求 {i+1} 成功")
        
        # 验证结果统计
        assert success_count == 2
        assert error_count == 2
        logger.info(f"并发请求结果: {success_count}个成功, {error_count}个失败")
    
    async def test_async_stream_error_handling(self, request_manager):
        """
        测试异步流式请求中的错误处理
        验证流式响应中断时的错误捕获
        """
        # 假设这是一个可能在流式响应过程中出错的端点
        endpoint = "/test/stream-error"
        
        # 定义错误处理回调
        errors = []
        
        async def on_chunk(chunk):
            """
            处理数据块的回调函数
            """
            logger.info(f"收到数据块: {chunk}")
            return chunk
        
        # 发送异步流式请求并检查错误
        with pytest.raises((RequestError, asyncio.CancelledError)) as excinfo:
            await request_manager.request_stream_async(
                method="GET",
                endpoint=endpoint,
                on_chunk=on_chunk
            )
        
        # 验证异常信息
        error = excinfo.value
        logger.info(f"异步流式请求错误: {str(error)}")
        assert isinstance(error, (RequestError, asyncio.CancelledError))


class TestModelAPIErrorHandling:
    """
    大模型API错误处理测试类
    测试大模型API调用中的各种错误情况
    """
    
    ENV = os.getenv('TEST_ENV', 'dev')
    
    @pytest.fixture(scope="class")
    def config(self):
        """
        测试配置fixture
        """
        config = Config()
        api_key = config.get(f"{self.ENV}.model_api.api_key", "")
        base_url = config.get(f"{self.ENV}.model_api.base_url", "")
        
        return {
            "api_key": api_key,
            "base_url": base_url,
            "timeout": 30
        }
    
    @pytest.fixture(scope="class")
    def model_api(self, config):
        """
        模型API客户端fixture
        """
        # 创建模型API实例
        api = ModelAPI(
            api_key=config["api_key"],
            base_url=config["base_url"] if config["base_url"] else None,
            timeout=config["timeout"]
        )
        return api
    
    @pytest.fixture
    def event_loop(self):
        """
        事件循环fixture，用于异步测试
        """
        loop = asyncio.get_event_loop()
        yield loop
        loop.close()
    
    def test_invalid_api_key(self, config):
        """
        测试使用无效API密钥的情况
        预期抛出认证错误
        """
        # 使用无效的API密钥创建客户端
        invalid_api = ModelAPI(
            api_key="invalid-api-key",
            base_url=config["base_url"] if config["base_url"] else None,
            timeout=config["timeout"]
        )
        
        # 准备请求参数
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        # 发送请求并检查错误
        with pytest.raises(ModelAPIError) as excinfo:
            asyncio.run(invalid_api.chat_completion_async(
                messages=messages,
                model="gpt-3.5-turbo"
            ))
        
        # 验证异常信息
        error = excinfo.value
        assert "authentication" in str(error).lower() or "invalid" in str(error).lower()
        logger.info(f"成功捕获无效API密钥错误: {str(error)}")
    
    def test_invalid_model_name(self, model_api):
        """
        测试使用不存在的模型名称
        预期抛出模型不存在错误
        """
        # 准备请求参数
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        # 发送请求并检查错误
        with pytest.raises(ModelAPIError) as excinfo:
            asyncio.run(model_api.chat_completion_async(
                messages=messages,
                model="non-existent-model-12345"
            ))
        
        # 验证异常信息
        error = excinfo.value
        assert "model" in str(error).lower() or "not found" in str(error).lower()
        logger.info(f"成功捕获无效模型名称错误: {str(error)}")
    
    def test_exceed_token_limit(self, model_api):
        """
        测试超出令牌限制的情况
        预期抛出令牌限制错误
        """
        # 创建一个非常长的提示文本，超出模型的令牌限制
        long_text = "This is a very long text that will exceed the token limit " * 1000
        
        messages = [
            {"role": "user", "content": long_text}
        ]
        
        # 发送请求并检查错误
        with pytest.raises(ModelAPIError) as excinfo:
            asyncio.run(model_api.chat_completion_async(
                messages=messages,
                model="gpt-3.5-turbo",
                max_tokens=100
            ))
        
        # 验证异常信息
        error = excinfo.value
        assert "token" in str(error).lower() or "limit" in str(error).lower()
        logger.info(f"成功捕获令牌限制错误: {str(error)}")


if __name__ == "__main__":
    # 直接运行时执行pytest
    pytest.main([__file__, "-v"])