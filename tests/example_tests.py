#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实际API测试示例

此文件包含几个实际可用的API测试示例，展示如何使用接口自动化框架进行测试。
这些示例涵盖了常见的API测试场景，并提供了详细的注释说明。
"""

import asyncio
import json
import logging
import os
import pytest
import time
from typing import Dict, Any, List, Optional

# 导入框架核心模块
from api_auto_framework.utils.requestutil import RequestManager, DefaultResponseHandler
from api_auto_framework.utils.modelutils import ModelAPI, AsyncModelResponseHandler
from api_auto_framework.utils.streamutil import AdvancedStreamTester, create_json_extractor
from api_auto_framework.config.config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestUserManagementAPI:
    """
    用户管理API测试类
    测试用户的创建、查询、更新和删除等功能
    """
    
    # 测试环境配置
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
        
        # 设置认证头
        if config["api_key"]:
            manager.add_header("Authorization", f"Bearer {config['api_key']}")
        
        manager.add_header("Content-Type", "application/json")
        return manager
    
    @pytest.fixture
    def test_user_data(self):
        """
        测试用户数据fixture
        生成一个唯一的测试用户数据
        """
        timestamp = int(time.time())
        return {
            "username": f"test_user_{timestamp}",
            "email": f"test_{timestamp}@example.com",
            "password": "Test@123456",
            "name": "测试用户"
        }
    
    def test_create_user(self, request_manager, test_user_data):
        """
        测试创建用户接口
        1. 发送POST请求创建用户
        2. 验证响应状态码和数据
        3. 记录创建的用户ID以便后续测试使用
        """
        # 准备请求数据
        endpoint = "/users"
        payload = test_user_data.copy()
        
        # 发送请求
        response = request_manager.post(
            endpoint=endpoint,
            json=payload
        )
        
        # 验证响应
        assert response.status_code == 201, f"创建用户失败: {response.text}"
        assert response.success is True
        
        # 验证创建的用户数据
        user_data = response.data
        assert "id" in user_data
        assert user_data["username"] == payload["username"]
        assert user_data["email"] == payload["email"]
        assert "name" in user_data
        
        # 保存用户ID到fixture数据中，供后续测试使用
        test_user_data["id"] = user_data["id"]
        logger.info(f"成功创建测试用户: {user_data['id']} - {user_data['username']}")
    
    def test_get_user(self, request_manager, test_user_data):
        """
        测试获取用户信息接口
        依赖于test_create_user测试创建的用户
        """
        # 确保用户ID已存在
        assert "id" in test_user_data, "用户ID不存在，请先运行创建用户测试"
        
        # 准备请求
        user_id = test_user_data["id"]
        endpoint = f"/users/{user_id}"
        
        # 发送请求
        response = request_manager.get(endpoint=endpoint)
        
        # 验证响应
        assert response.status_code == 200, f"获取用户信息失败: {response.text}"
        assert response.success is True
        
        # 验证用户数据
        user_data = response.data
        assert user_data["id"] == user_id
        assert user_data["username"] == test_user_data["username"]
        assert user_data["email"] == test_user_data["email"]
        
        logger.info(f"成功获取用户信息: {user_data['id']}")
    
    def test_update_user(self, request_manager, test_user_data):
        """
        测试更新用户信息接口
        依赖于test_create_user测试创建的用户
        """
        # 确保用户ID已存在
        assert "id" in test_user_data, "用户ID不存在，请先运行创建用户测试"
        
        # 准备请求数据
        user_id = test_user_data["id"]
        endpoint = f"/users/{user_id}"
        update_data = {
            "name": f"更新后的{test_user_data['name']}",
            "email": f"updated_{test_user_data['email']}"
        }
        
        # 发送请求
        response = request_manager.put(
            endpoint=endpoint,
            json=update_data
        )
        
        # 验证响应
        assert response.status_code == 200, f"更新用户信息失败: {response.text}"
        assert response.success is True
        
        # 验证更新后的用户数据
        user_data = response.data
        assert user_data["id"] == user_id
        assert user_data["name"] == update_data["name"]
        assert user_data["email"] == update_data["email"]
        
        # 更新fixture数据
        test_user_data.update(update_data)
        logger.info(f"成功更新用户信息: {user_id}")
    
    def test_delete_user(self, request_manager, test_user_data):
        """
        测试删除用户接口
        依赖于test_create_user测试创建的用户
        """
        # 确保用户ID已存在
        assert "id" in test_user_data, "用户ID不存在，请先运行创建用户测试"
        
        # 准备请求
        user_id = test_user_data["id"]
        endpoint = f"/users/{user_id}"
        
        # 发送请求
        response = request_manager.delete(endpoint=endpoint)
        
        # 验证响应
        assert response.status_code == 204, f"删除用户失败: {response.text}"
        
        # 验证用户确实被删除了
        verify_response = request_manager.get(endpoint=endpoint)
        assert verify_response.status_code == 404, "用户应该已被删除"
        
        logger.info(f"成功删除用户: {user_id}")
    
    def test_list_users(self, request_manager):
        """
        测试获取用户列表接口
        验证分页功能和响应格式
        """
        # 准备请求参数
        endpoint = "/users"
        params = {
            "page": 1,
            "limit": 10,
            "sort": "created_at:desc"
        }
        
        # 发送请求
        response = request_manager.get(
            endpoint=endpoint,
            params=params
        )
        
        # 验证响应
        assert response.status_code == 200, f"获取用户列表失败: {response.text}"
        assert response.success is True
        
        # 验证响应数据结构
        data = response.data
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        
        # 验证分页参数
        assert data["page"] == params["page"]
        assert data["limit"] == params["limit"]
        assert len(data["items"]) <= params["limit"]
        
        logger.info(f"成功获取用户列表，共 {data['total']} 个用户，当前显示第 {data['page']} 页")


class TestProductCatalogAPI:
    """
    产品目录API测试类
    测试产品的查询、过滤和搜索功能
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
    
    def test_get_product_by_id(self, request_manager):
        """
        测试根据ID获取产品详情
        """
        # 假设我们知道一个存在的产品ID
        product_id = "1001"
        endpoint = f"/products/{product_id}"
        
        # 发送请求
        response = request_manager.get(endpoint=endpoint)
        
        # 验证响应
        assert response.status_code == 200, f"获取产品详情失败: {response.text}"
        assert response.success is True
        
        # 验证产品数据结构
        product = response.data
        assert product["id"] == product_id
        assert "name" in product
        assert "price" in product
        assert "description" in product
        assert "category" in product
        
        # 验证价格格式
        assert isinstance(product["price"], (int, float)), "价格应该是数字"
        assert product["price"] >= 0, "价格不能为负数"
        
        logger.info(f"成功获取产品详情: {product['name']} (ID: {product_id})")
    
    def test_search_products(self, request_manager):
        """
        测试产品搜索功能
        """
        # 准备搜索参数
        endpoint = "/products/search"
        params = {
            "q": "手机",  # 搜索关键词
            "min_price": 1000,
            "max_price": 5000
        }
        
        # 发送请求
        response = request_manager.get(
            endpoint=endpoint,
            params=params
        )
        
        # 验证响应
        assert response.status_code == 200, f"搜索产品失败: {response.text}"
        assert response.success is True
        
        # 验证搜索结果
        data = response.data
        assert "products" in data
        assert isinstance(data["products"], list)
        
        # 验证每个产品都符合搜索条件
        for product in data["products"]:
            # 检查价格范围
            assert params["min_price"] <= product["price"] <= params["max_price"]
            # 检查关键词是否在名称或描述中
            product_text = f"{product['name']} {product['description']}".lower()
            assert params["q"].lower() in product_text
        
        logger.info(f"成功搜索到 {len(data['products'])} 个产品")
    
    def test_filter_products_by_category(self, request_manager):
        """
        测试按类别筛选产品
        """
        # 准备请求参数
        endpoint = "/products"
        category = "electronics"
        params = {
            "category": category,
            "limit": 20
        }
        
        # 发送请求
        response = request_manager.get(
            endpoint=endpoint,
            params=params
        )
        
        # 验证响应
        assert response.status_code == 200, f"筛选产品失败: {response.text}"
        assert response.success is True
        
        # 验证筛选结果
        data = response.data
        assert "items" in data
        
        # 验证每个产品的类别
        for product in data["items"]:
            assert product["category"] == category
        
        logger.info(f"成功筛选到 {len(data['items'])} 个 {category} 类别的产品")


class TestAsyncPaymentAPI:
    """
    支付API异步测试类
    测试支付处理和退款功能的异步接口
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
    
    @pytest.fixture
    def test_payment_data(self):
        """
        测试支付数据fixture
        """
        return {
            "amount": 100.50,
            "currency": "CNY",
            "payment_method": "credit_card",
            "card_number": "4111111111111111",
            "cardholder_name": "测试用户",
            "expiry_month": "12",
            "expiry_year": "2030",
            "cvv": "123",
            "description": "测试支付订单"
        }
    
    async def test_create_payment_async(self, request_manager, test_payment_data):
        """
        测试异步创建支付
        """
        # 准备请求数据
        endpoint = "/payments"
        payload = test_payment_data.copy()
        
        # 发送异步请求
        response = await request_manager.post_async(
            endpoint=endpoint,
            json=payload
        )
        
        # 验证响应
        assert response.status_code == 201, f"创建支付失败: {response.text}"
        assert response.success is True
        
        # 验证支付数据
        payment_data = response.data
        assert "id" in payment_data
        assert payment_data["amount"] == payload["amount"]
        assert payment_data["currency"] == payload["currency"]
        assert payment_data["status"] == "pending"
        
        # 保存支付ID以供后续测试使用
        test_payment_data["id"] = payment_data["id"]
        logger.info(f"成功创建异步支付: {payment_data['id']}")
    
    async def test_get_payment_status_async(self, request_manager, test_payment_data):
        """
        测试异步获取支付状态
        依赖于test_create_payment_async测试创建的支付
        """
        # 确保支付ID已存在
        assert "id" in test_payment_data, "支付ID不存在，请先运行创建支付测试"
        
        # 准备请求
        payment_id = test_payment_data["id"]
        endpoint = f"/payments/{payment_id}"
        
        # 发送异步请求
        response = await request_manager.get_async(endpoint=endpoint)
        
        # 验证响应
        assert response.status_code == 200, f"获取支付状态失败: {response.text}"
        assert response.success is True
        
        # 验证支付数据
        payment_data = response.data
        assert payment_data["id"] == payment_id
        assert "status" in payment_data
        
        logger.info(f"成功获取支付状态: {payment_data['status']}")
    
    async def test_refund_payment_async(self, request_manager, test_payment_data):
        """
        测试异步退款功能
        依赖于test_create_payment_async测试创建的支付
        """
        # 确保支付ID已存在
        assert "id" in test_payment_data, "支付ID不存在，请先运行创建支付测试"
        
        # 准备请求数据
        payment_id = test_payment_data["id"]
        endpoint = f"/payments/{payment_id}/refund"
        refund_data = {
            "amount": test_payment_data["amount"],  # 全额退款
            "reason": "测试退款"
        }
        
        # 发送异步请求
        response = await request_manager.post_async(
            endpoint=endpoint,
            json=refund_data
        )
        
        # 验证响应
        assert response.status_code == 201, f"创建退款失败: {response.text}"
        assert response.success is True
        
        # 验证退款数据
        refund_data = response.data
        assert "id" in refund_data
        assert refund_data["payment_id"] == payment_id
        assert refund_data["amount"] == test_payment_data["amount"]
        assert refund_data["status"] == "processing"
        
        # 保存退款ID
        test_payment_data["refund_id"] = refund_data["id"]
        logger.info(f"成功创建退款请求: {refund_data['id']}")
    
    async def test_concurrent_payments(self, request_manager):
        """
        测试并发处理多个支付请求
        """
        # 准备多个支付请求
        payment_payloads = [
            {
                "amount": 50.00 + i * 10,
                "currency": "CNY",
                "payment_method": "credit_card",
                "description": f"并发测试支付 {i+1}"
            }
            for i in range(3)
        ]
        
        # 创建异步任务列表
        tasks = []
        for payload in payment_payloads:
            task = request_manager.post_async(
                endpoint="/payments",
                json=payload
            )
            tasks.append(task)
        
        # 并发执行所有请求
        responses = await asyncio.gather(*tasks)
        
        # 验证所有响应
        for i, response in enumerate(responses):
            assert response.status_code == 201, f"支付 {i+1} 创建失败"
            assert response.success is True
            assert response.data["amount"] == payment_payloads[i]["amount"]
            logger.info(f"并发支付 {i+1} 成功: {response.data['id']}")


class TestModelAPI:
    """
    大模型API测试类
    测试文本生成、聊天完成和流式响应功能
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
        model_name = config.get(f"{self.ENV}.model_api.default_model", "gpt-3.5-turbo")
        
        return {
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name,
            "timeout": 60
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
    
    async def test_chat_completion_stream_with_validation(self, model_api):
        """
        测试带有验证的聊天完成流式响应
        使用AdvancedStreamTester验证流式响应内容
        """
        # 创建流式测试器
        stream_tester = AdvancedStreamTester()
        
        # 添加断言
        stream_tester.add_assertion(
            "响应包含关键词",
            "contains",
            "Python"
        )
        stream_tester.add_assertion(
            "响应长度检查",
            "length_gt",
            50
        )
        
        # 准备请求参数
        messages = [
            {"role": "system", "content": "你是一位专业的编程老师，回答要简洁明了。"},
            {"role": "user", "content": "请简要介绍Python语言的主要特点。"}
        ]
        
        # 开始测试
        stream_tester.start()
        
        # 发送流式请求
        full_response = {"content": ""}
        
        async def process_chunk(chunk):
            # 处理每个数据块
            content = chunk.get("content", "")
            full_response["content"] += content
            
            # 使用测试器验证数据块
            await stream_tester.process_chunk_async(chunk)
            
            # 记录进度
            if len(content) > 0:
                logger.info(f"收到数据块，累计长度: {len(full_response['content'])}")
            
            return chunk
        
        response = await model_api.chat_completion_async(
            messages=messages,
            model="gpt-3.5-turbo",
            stream=True,
            max_tokens=200,
            on_chunk=process_chunk
        )
        
        # 停止测试并获取结果
        test_results = stream_tester.stop()
        
        # 验证测试结果
        assert response["success"] is True
        assert full_response["content"] != ""
        assert test_results["all_assertions_passed"] is True
        
        # 记录详细性能指标
        metrics = test_results["performance_metrics"]
        logger.info(f"流式响应测试完成")
        logger.info(f"  总响应时间: {metrics['total_time']:.3f}秒")
        logger.info(f"  首次响应时间: {metrics['ttfb']:.3f}秒")
        logger.info(f"  生成内容长度: {len(full_response['content'])}字符")
        logger.info(f"  数据块数量: {metrics['total_chunks']}")
        logger.info(f"  内容生成速度: {metrics['content_generation_speed']:.2f}字符/秒")


if __name__ == "__main__":
    # 直接运行时执行pytest
    pytest.main([__file__, "-v"])