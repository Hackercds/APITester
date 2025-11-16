#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口自动化测试用例增强模板

此增强版模板提供了编写不同类型接口测试用例的标准结构和示例，包括：
1. 同步HTTP接口测试
2. 异步HTTP接口测试
3. 大模型API流式接口测试
4. 数据驱动测试
5. 参数化测试
6. 性能监控测试
7. 异常场景测试
8. 依赖接口测试

使用时请按照实际需求修改相关参数和测试逻辑。
"""

import asyncio
import json
import logging
import os
import pytest
import time
import random
from typing import Dict, Any, List, Optional, Union, Callable
import allure

# 导入框架核心模块
from api_auto_framework.utils.requestutil import RequestManager, DefaultResponseHandler
from api_auto_framework.utils.modelutils import ModelAPI, AsyncModelResponseHandler
from api_auto_framework.utils.streamutil import AdvancedStreamTester
from api_auto_framework.utils.datautil import DataGenerator, CSVDataProvider, ExcelDataProvider
from api_auto_framework.utils.assertutil import AssertionHelper
from api_auto_framework.utils.perfutil import PerformanceTracker
from api_auto_framework.config.config import Config
from api_auto_framework.utils.exceptions import TestConfigError, TestExecutionError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据驱动测试的数据源
TEST_DATA_CSV = os.path.join(os.path.dirname(__file__), '../data/test_data.csv')
TEST_DATA_EXCEL = os.path.join(os.path.dirname(__file__), '../data/test_data.xlsx')

# 性能测试配置
PERF_TEST_CONFIG = {
    'max_response_time': 1.0,  # 最大响应时间（秒）
    'max_request_time': 0.5,   # 最大请求时间（秒）
    'max_retries': 3           # 最大重试次数
}


class TestAPITemplate:
    """
    API测试用例基类模板（增强版）
    提供通用的测试方法、配置管理、数据驱动、断言辅助和性能监控功能
    """
    
    # 测试环境配置
    ENV = os.getenv('TEST_ENV', 'dev')  # 可通过环境变量切换测试环境
    
    @pytest.fixture(scope="class")
    def config(self):
        """
        测试配置fixture，支持多环境配置
        """
        try:
            # 加载配置
            config = Config()
            # 根据测试环境选择配置
            base_url = config.get(f"{self.ENV}.base_url", "https://api.example.com")
            api_key = config.get(f"{self.ENV}.api_key", "default_api_key")
            
            # 增强配置参数
            config_data = {
                "base_url": base_url,
                "api_key": api_key,
                "timeout": config.get(f"{self.ENV}.timeout", 30),
                "retry_count": config.get(f"{self.ENV}.retry_count", 3),
                "connect_timeout": config.get(f"{self.ENV}.connect_timeout", 10),
                "read_timeout": config.get(f"{self.ENV}.read_timeout", 20),
                "verify_ssl": config.get(f"{self.ENV}.verify_ssl", True),
                "proxies": config.get(f"{self.ENV}.proxies", {})
            }
            
            logger.info(f"加载环境配置: {self.ENV}, 基础URL: {config_data['base_url']}")
            return config_data
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            raise TestConfigError(f"配置加载失败: {str(e)}")
    
    @pytest.fixture(scope="class")
    def request_manager(self, config):
        """
        请求管理器fixture，支持高级配置
        """
        try:
            # 创建请求管理器实例
            manager = RequestManager(
                base_url=config["base_url"],
                timeout=config["timeout"],
                retry_count=config["retry_count"],
                connect_timeout=config["connect_timeout"],
                read_timeout=config["read_timeout"],
                verify_ssl=config["verify_ssl"],
                proxies=config["proxies"]
            )
            
            # 添加默认请求头
            manager.add_header("Authorization", f"Bearer {config['api_key']}")
            manager.add_header("Content-Type", "application/json")
            manager.add_header("Accept", "application/json")
            
            # 添加测试标识
            manager.add_header("X-Test-ID", f"{self.__class__.__name__}-{int(time.time())}-{random.randint(1000, 9999)}")
            
            logger.info(f"初始化请求管理器，基础URL: {config['base_url']}")
            return manager
        except Exception as e:
            logger.error(f"初始化请求管理器失败: {str(e)}")
            raise TestExecutionError(f"请求管理器初始化失败: {str(e)}")
    
    @pytest.fixture
    def data_generator(self):
        """
        测试数据生成器fixture
        """
        return DataGenerator()
    
    @pytest.fixture
    def assertion_helper(self):
        """
        断言辅助工具fixture
        """
        return AssertionHelper()
    
    @pytest.fixture
    def performance_tracker(self):
        """
        性能跟踪工具fixture
        """
        return PerformanceTracker()
    
    @pytest.fixture
    def csv_data_provider(self):
        """
        CSV数据提供者fixture，用于数据驱动测试
        """
        if os.path.exists(TEST_DATA_CSV):
            return CSVDataProvider(TEST_DATA_CSV)
        logger.warning(f"CSV测试数据文件不存在: {TEST_DATA_CSV}")
        return None
    
    @pytest.fixture
    def excel_data_provider(self):
        """
        Excel数据提供者fixture，用于数据驱动测试
        """
        if os.path.exists(TEST_DATA_EXCEL):
            return ExcelDataProvider(TEST_DATA_EXCEL)
        logger.warning(f"Excel测试数据文件不存在: {TEST_DATA_EXCEL}")
        return None
    
    # 测试生命周期管理
    def setup_class(self):
        """
        测试类初始化，添加allure测试报告标记
        """
        allure.dynamic.label('environment', self.ENV)
        allure.dynamic.description(f"API测试类: {self.__class__.__name__}，环境: {self.ENV}")
        logger.info(f"开始执行测试类: {self.__class__.__name__}，环境: {self.ENV}")
        
        # 可以在这里添加测试前置准备工作，如清理测试数据、初始化测试环境等
    
    def teardown_class(self):
        """
        测试类清理
        """
        logger.info(f"测试类执行完成: {self.__class__.__name__}")
        
        # 可以在这里添加测试后置清理工作，如清理测试生成的数据等
    
    def setup_method(self, method):
        """
        每个测试方法执行前，添加性能跟踪和日志记录
        """
        allure.dynamic.label('test_method', method.__name__)
        allure.dynamic.label('start_time', time.strftime('%Y-%m-%d %H:%M:%S'))
        logger.info(f"开始执行测试方法: {method.__name__}")
    
    def teardown_method(self, method):
        """
        每个测试方法执行后，记录执行时间
        """
        allure.dynamic.label('end_time', time.strftime('%Y-%m-%d %H:%M:%S'))
        logger.info(f"测试方法执行完成: {method.__name__}")
    
    # 辅助方法
    def add_test_step(self, step_name: str) -> Callable:
        """
        添加测试步骤装饰器，用于记录测试步骤和性能
        
        Args:
            step_name: 步骤名称
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                with allure.step(step_name):
                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)
                        duration = time.time() - start_time
                        logger.info(f"测试步骤 '{step_name}' 执行成功，耗时: {duration:.3f}秒")
                        return result
                    except Exception as e:
                        duration = time.time() - start_time
                        logger.error(f"测试步骤 '{step_name}' 执行失败，耗时: {duration:.3f}秒，错误: {str(e)}")
                        raise
            return wrapper
        return decorator
    
    def handle_test_exception(self, exception: Exception, context: str = "") -> None:
        """
        统一异常处理方法
        
        Args:
            exception: 捕获的异常
            context: 异常上下文信息
        """
        error_msg = f"{context}: {str(exception)}"
        logger.error(error_msg)
        allure.attach(error_msg, name="错误详情", attachment_type=allure.attachment_type.TEXT)
        raise
    
    def log_test_data(self, data: Any, name: str = "test_data") -> None:
        """
        记录测试数据到allure报告
        
        Args:
            data: 要记录的数据
            name: 数据名称
        """
        try:
            if isinstance(data, (dict, list)):
                data_str = json.dumps(data, ensure_ascii=False, indent=2)
            else:
                data_str = str(data)
            allure.attach(data_str, name=name, attachment_type=allure.attachment_type.JSON)
        except Exception as e:
            logger.error(f"记录测试数据失败: {str(e)}")
    
    def assert_response_performance(self, response_time: float, max_time: float = None) -> None:
        """
        断言响应性能
        
        Args:
            response_time: 实际响应时间（秒）
            max_time: 最大允许响应时间（秒），默认使用配置值
        """
        if max_time is None:
            max_time = PERF_TEST_CONFIG['max_response_time']
        
        assert response_time <= max_time, \
            f"响应时间过长: {response_time:.3f}秒，超过最大允许时间: {max_time:.3f}秒"
        logger.info(f"响应性能测试通过: {response_time:.3f}秒 <= {max_time:.3f}秒")


class TestSyncAPI(TestAPITemplate):
    """
    同步HTTP接口测试用例示例（增强版）
    包含: 数据驱动测试、参数化测试、性能监控、异常处理、高级断言
    """
    
    @pytest.mark.parametrize("page, limit, expected_min_items", [
        (1, 10, 5),    # 正常场景
        (1, 20, 10),   # 更大的分页
        (999, 10, 0),  # 超出范围的页号
        (0, 10, 0),    # 无效的页号
    ])
    def test_get_with_parametrization(self, request_manager, assertion_helper, performance_tracker):
        """
        使用参数化测试GET请求，测试不同分页参数的情况
        """
        allure.dynamic.title(f"参数化GET请求测试 - 第{page}页，每页{limit}条")
        
        # 准备请求参数
        endpoint = "/api/v1/resources"
        params = {
            "page": page,
            "limit": limit,
            "sort": "created_at:desc"
        }
        
        # 记录测试数据
        self.log_test_data(params, "请求参数")
        
        # 发送请求并跟踪性能
        with performance_tracker.measure("GET请求总耗时"):
            response = request_manager.get(
                endpoint=endpoint,
                params=params
            )
        
        # 记录响应时间性能
        self.assert_response_performance(performance_tracker.get_last_metric("GET请求总耗时"))
        
        # 使用高级断言工具验证响应
        assertion_helper.assert_status_code(response, 200)
        assertion_helper.assert_success_flag(response, True)
        assertion_helper.assert_key_exists(response.data, "items")
        assertion_helper.assert_is_instance(response.data["items"], list)
        
        # 验证返回的数据量
        assert len(response.data["items"]) >= expected_min_items
        
        logger.info(f"参数化GET请求测试成功，返回 {len(response.data['items'])} 条记录")
    
    def test_post_with_data_generation(self, request_manager, data_generator, performance_tracker):
        """
        使用测试数据生成器创建POST请求数据
        """
        # 使用数据生成器创建测试数据
        payload = {
            "name": data_generator.generate_string(length=10, prefix="测试_"),
            "description": data_generator.generate_paragraph(sentences=2),
            "status": data_generator.random_choice(["active", "inactive"]),
            "created_at": data_generator.generate_timestamp(),
            "metadata": {
                "test_id": data_generator.generate_uuid(),
                "tags": data_generator.generate_list(items=["test", "api"], length=3)
            }
        }
        
        # 记录测试数据
        self.log_test_data(payload, "创建资源请求体")
        
        # 发送请求并跟踪性能
        start_time = time.time()
        response = request_manager.post(
            endpoint="/api/v1/resources",
            json=payload
        )
        response_time = time.time() - start_time
        
        # 验证响应性能
        self.assert_response_performance(response_time)
        
        # 验证响应
        assert response.status_code == 201
        assert response.success is True
        
        # 验证创建的资源
        data = response.data
        assert "id" in data
        assert data["name"] == payload["name"]
        assert data["status"] == payload["status"]
        
        logger.info(f"创建资源成功，资源ID: {data['id']}")
        
        # 记录响应数据到报告
        self.log_test_data(data, "创建资源响应")
    
    def test_complete_resource_crud(self, request_manager, performance_tracker):
        """
        测试完整的CRUD操作流程，包含前置条件和清理
        """
        # 创建资源（前置条件）
        @self.add_test_step("创建测试资源")
        def create_test_resource():
            create_payload = {
                "name": f"CRUD测试资源_{int(time.time())}",
                "description": "用于CRUD集成测试的资源",
                "status": "active"
            }
            
            response = request_manager.post(
                endpoint="/api/v1/resources",
                json=create_payload
            )
            
            assert response.status_code == 201
            return response.data["id"]
        
        # 获取资源
        @self.add_test_step("获取创建的资源")
        def get_resource(resource_id):
            response = request_manager.get(
                endpoint=f"/api/v1/resources/{resource_id}"
            )
            assert response.status_code == 200
            return response.data
        
        # 更新资源
        @self.add_test_step("更新资源")
        def update_resource(resource_id):
            update_payload = {
                "name": f"更新后的CRUD测试资源_{int(time.time())}",
                "description": "更新后的测试描述",
                "status": "inactive"
            }
            
            response = request_manager.put(
                endpoint=f"/api/v1/resources/{resource_id}",
                json=update_payload
            )
            
            assert response.status_code == 200
            return response.data
        
        # 删除资源
        @self.add_test_step("删除资源")
        def delete_resource(resource_id):
            response = request_manager.delete(
                endpoint=f"/api/v1/resources/{resource_id}"
            )
            assert response.status_code == 204
        
        # 执行完整测试流程
        try:
            resource_id = create_test_resource()
            logger.info(f"成功创建测试资源，ID: {resource_id}")
            
            # 验证创建的资源
            resource_data = get_resource(resource_id)
            assert resource_data["status"] == "active"
            
            # 更新资源
            updated_data = update_resource(resource_id)
            assert updated_data["status"] == "inactive"
            assert updated_data["name"] != resource_data["name"]
            
            # 验证更新后的资源
            verify_data = get_resource(resource_id)
            assert verify_data["status"] == "inactive"
            
        except Exception as e:
            self.handle_test_exception(e, "CRUD流程测试失败")
        finally:
            # 无论测试成功失败，都确保资源被删除（清理）
            try:
                if 'resource_id' in locals():
                    delete_resource(resource_id)
                    logger.info(f"清理测试资源，ID: {resource_id}")
            except Exception as cleanup_error:
                logger.warning(f"清理测试资源失败: {str(cleanup_error)}")
    
    @pytest.mark.skipif(not os.path.exists(TEST_DATA_CSV), reason="CSV测试数据文件不存在")
    def test_data_driven_get_requests(self, request_manager, csv_data_provider, assertion_helper):
        """
        数据驱动测试 - 从CSV文件读取测试数据进行GET请求测试
        """
        if not csv_data_provider:
            pytest.skip("CSV数据提供者不可用")
        
        # 从CSV获取测试数据
        test_data = csv_data_provider.get_data()
        
        for row in test_data:
            with allure.step(f"测试场景: {row.get('test_name', '未命名')}"):
                # 准备请求参数
                endpoint = row.get('endpoint', '/api/v1/resources')
                params = {
                    "page": int(row.get('page', 1)),
                    "limit": int(row.get('limit', 10))
                }
                
                # 发送请求
                response = request_manager.get(
                    endpoint=endpoint,
                    params=params
                )
                
                # 根据测试数据进行断言
                expected_status = int(row.get('expected_status', 200))
                assertion_helper.assert_status_code(response, expected_status)
                
                if expected_status == 200:
                    assertion_helper.assert_success_flag(response, True)
                    expected_items_count = int(row.get('expected_items_count', 0))
                    if expected_items_count > 0:
                        assert len(response.data.get('items', [])) >= expected_items_count
    
    def test_error_handling(self, request_manager, assertion_helper):
        """
        测试错误场景处理
        """
        # 测试无效的endpoint
        with allure.step("测试无效的endpoint"):
            response = request_manager.get(endpoint="/invalid/endpoint")
            assertion_helper.assert_status_code(response, 404)
            assertion_helper.assert_key_exists(response.data, "error")
        
        # 测试缺少必要参数
        with allure.step("测试缺少必要参数"):
            response = request_manager.post(
                endpoint="/api/v1/resources",
                json={"name": "缺少必要字段"}  # 缺少description字段
            )
            assertion_helper.assert_status_code(response, 400)
            assertion_helper.assert_key_exists(response.data, "validation_errors")
        
        # 测试权限错误
        with allure.step("测试权限错误"):
            # 创建临时请求管理器，使用无效token
            temp_manager = request_manager.copy()
            temp_manager.update_header("Authorization", "Bearer invalid_token")
            
            response = temp_manager.get(endpoint="/api/v1/protected")
            assertion_helper.assert_status_code(response, 401)
            assertion_helper.assert_key_exists(response.data, "error")
    
    def test_performance_monitoring(self, request_manager, performance_tracker):
        """
        性能监控测试，测试多次请求的性能表现
        """
        # 执行多次请求并收集性能数据
        iterations = 5
        response_times = []
        
        for i in range(iterations):
            with allure.step(f"性能测试迭代 {i+1}/{iterations}"):
                start_time = time.time()
                response = request_manager.get(
                    endpoint="/api/v1/resources",
                    params={"page": 1, "limit": 5}
                )
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                # 记录每次迭代的响应时间
                logger.info(f"迭代 {i+1} 响应时间: {response_time:.3f}秒")
        
        # 计算性能统计数据
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        # 记录性能统计到报告
        performance_stats = {
            "iterations": iterations,
            "avg_response_time": avg_response_time,
            "max_response_time": max_response_time,
            "min_response_time": min_response_time
        }
        
        self.log_test_data(performance_stats, "性能统计数据")
        
        # 验证平均响应时间
        self.assert_response_performance(avg_response_time)
        
        logger.info(f"性能测试完成: 平均响应时间 {avg_response_time:.3f}秒")
    
    def test_dynamic_parameters(self, request_manager, data_generator):
        """
        测试动态参数处理
        """
        # 生成动态路径参数
        dynamic_id = data_generator.generate_number(min=1000, max=9999)
        
        # 使用动态参数发送请求
        response = request_manager.get(
            endpoint=f"/api/v1/resources/{dynamic_id}",
            params={
                "timestamp": int(time.time()),
                "random": data_generator.generate_string(length=8)
            }
        )
        
        # 验证响应
        if response.status_code == 200:
            # 资源存在的情况
            assert response.success is True
            assert response.data.get("id") == dynamic_id
        elif response.status_code == 404:
            # 资源不存在的情况
            assert response.success is False
            assert "error" in response.data
        else:
            # 其他状态码视为失败
            pytest.fail(f"Unexpected status code: {response.status_code}")
    



class TestAsyncAPI(TestAPITemplate):
    """
    异步HTTP接口测试用例示例
    """
    
    @pytest.fixture
    def event_loop(self):
        """
        事件循环fixture，用于异步测试
        """
        loop = asyncio.get_event_loop()
        yield loop
        loop.close()
    
    async def test_get_async_example(self, request_manager):
        """
        测试异步GET请求示例
        """
        # 1. 准备请求参数
        endpoint = "/api/v1/resources"
        params = {
            "page": 1,
            "limit": 10
        }
        
        # 2. 发送异步请求
        response = await request_manager.get_async(
            endpoint=endpoint,
            params=params
        )
        
        # 3. 验证响应
        assert response.status_code == 200
        assert response.success is True
        
        # 验证响应数据
        data = response.data
        assert "items" in data
        
        logger.info(f"异步获取资源成功，返回 {len(data['items'])} 条记录")
    
    async def test_post_async_example(self, request_manager):
        """
        测试异步POST请求示例
        """
        # 1. 准备请求参数
        endpoint = "/api/v1/resources"
        payload = {
            "name": "异步测试资源",
            "description": "这是一个异步测试创建的资源"
        }
        
        # 2. 发送异步请求
        response = await request_manager.post_async(
            endpoint=endpoint,
            json=payload
        )
        
        # 3. 验证响应
        assert response.status_code == 201
        assert response.success is True
        
        # 验证创建的资源
        data = response.data
        assert "id" in data
        
        logger.info(f"异步创建资源成功，资源ID: {data['id']}")
    
    async def test_concurrent_requests(self, request_manager):
        """
        测试并发请求示例
        """
        # 准备多个请求
        endpoints = [
            "/api/v1/resources/1",
            "/api/v1/resources/2",
            "/api/v1/resources/3"
        ]
        
        # 创建任务列表
        tasks = [
            request_manager.get_async(endpoint=endpoint)
            for endpoint in endpoints
        ]
        
        # 并发执行所有请求
        responses = await asyncio.gather(*tasks)
        
        # 验证所有响应
        for i, response in enumerate(responses):
            assert response.status_code == 200
            assert response.success is True
            logger.info(f"并发请求 {i+1} 成功")
    
    async def test_timeout_handling(self, request_manager):
        """
        测试超时处理示例
        """
        # 设置较短的超时时间
        original_timeout = request_manager.timeout
        request_manager.timeout = 0.001  # 极短的超时时间
        
        try:
            # 1. 准备请求参数
            endpoint = "/api/v1/resources"
            
            # 2. 发送可能会超时的请求
            with pytest.raises(asyncio.TimeoutError):
                await request_manager.get_async(endpoint=endpoint)
                
            logger.info("超时处理测试通过")
        finally:
            # 恢复原始超时设置
            request_manager.timeout = original_timeout


class TestStreamingModelAPI(TestAPITemplate):
    """
    大模型API流式接口测试用例示例
    """
    
    @pytest.fixture
    def event_loop(self):
        """
        事件循环fixture，用于异步测试
        """
        loop = asyncio.get_event_loop()
        yield loop
        loop.close()
    
    @pytest.fixture
    def model_api(self, config):
        """
        模型API客户端fixture
        """
        # 创建模型API实例
        api = ModelAPI(
            api_key=config["api_key"],
            base_url=config.get("model_api_base_url", "https://api.model.example.com"),
            timeout=config["timeout"]
        )
        return api
    
    @pytest.fixture
    def stream_tester(self):
        """
        流式测试器fixture
        """
        tester = AdvancedStreamTester()
        # 添加一些通用的断言
        tester.add_assertion(
            "内容不为空",
            "length_gt",
            0
        )
        return tester
    
    async def test_chat_completion_stream(self, model_api, stream_tester):
        """
        测试模型聊天完成流式接口
        """
        # 1. 准备请求参数
        messages = [
            {"role": "system", "content": "你是一个有用的助手"},
            {"role": "user", "content": "请简要介绍一下人工智能"}
        ]
        
        # 定义自定义的流式响应处理函数
        full_response = {"content": ""}
        
        async def process_stream_chunk(chunk):
            # 处理每个流式数据块
            content = chunk.get("content", "")
            full_response["content"] += content
            
            # 使用流式测试器处理数据块
            processed_chunk = await stream_tester.process_chunk_async(chunk)
            
            logger.info(f"收到流式数据块，内容长度: {len(content)}")
            return processed_chunk
        
        # 2. 开始测试
        stream_tester.start()
        
        # 3. 发送流式请求
        response = await model_api.chat_completion_async(
            messages=messages,
            model="gpt-4",  # 替换为实际使用的模型
            stream=True,
            on_chunk=process_stream_chunk
        )
        
        # 4. 停止测试并获取结果
        test_results = stream_tester.stop()
        
        # 5. 验证响应
        assert response["success"] is True
        assert full_response["content"] != ""
        
        # 验证测试结果
        assert test_results["all_assertions_passed"] is True
        assert test_results["performance_metrics"]["total_chunks"] > 0
        
        logger.info(f"流式测试完成，生成内容长度: {len(full_response['content'])}")
        logger.info(f"性能指标: TTFB={test_results['performance_metrics']['ttfb']:.3f}s, " 
                    f"总时间={test_results['performance_metrics']['total_time']:.3f}s")
    
    async def test_stream_validation(self, model_api, stream_tester):
        """
        测试流式响应验证功能
        """
        # 1. 准备请求参数
        messages = [
            {"role": "system", "content": "你是一个专业的数学老师"},
            {"role": "user", "content": "请计算2+2等于多少？并简要解释"}
        ]
        
        # 添加特定的断言
        stream_tester.add_assertion(
            "包含计算结果",
            "contains",
            "4"
        )
        stream_tester.add_assertion(
            "包含解释",
            "contains",
            "等于"
        )
        
        # 2. 开始测试
        stream_tester.start()
        
        # 3. 发送流式请求
        await model_api.chat_completion_async(
            messages=messages,
            model="gpt-4",  # 替换为实际使用的模型
            stream=True,
            on_chunk=lambda chunk: stream_tester.process_chunk_async(chunk)
        )
        
        # 4. 停止测试并获取结果
        test_results = stream_tester.stop()
        
        # 5. 验证所有断言是否通过
        assert test_results["all_assertions_passed"] is True
        
        # 保存测试记录以供后续分析
        stream_tester.save_recording("stream_validation_test.json")
        
        logger.info(f"流式验证测试完成，断言通过率: {test_results['assertion_summary']['pass_rate']*100:.1f}%")
    
    async def test_stream_performance(self, model_api, stream_tester):
        """
        测试流式响应性能
        """
        # 1. 准备请求参数（较长的提示词）
        messages = [
            {"role": "system", "content": "你是一个高效的文本生成助手"},
            {"role": "user", "content": "请生成一个关于接口自动化测试的段落，至少包含200个汉字。"}
        ]
        
        # 2. 开始测试
        stream_tester.start()
        
        # 3. 发送流式请求
        await model_api.chat_completion_async(
            messages=messages,
            model="gpt-4",  # 替换为实际使用的模型
            stream=True,
            max_tokens=300,
            on_chunk=lambda chunk: stream_tester.process_chunk_async(chunk)
        )
        
        # 4. 停止测试并获取性能指标
        test_results = stream_tester.stop()
        metrics = test_results["performance_metrics"]
        
        # 5. 验证性能指标
        assert metrics["total_time"] > 0
        assert metrics["total_chunks"] > 0
        
        # 打印详细性能指标
        logger.info("流式性能测试结果:")
        logger.info(f"  总响应时间: {metrics['total_time']:.3f}秒")
        logger.info(f"  首次响应时间(TTFB): {metrics['ttfb']:.3f}秒")
        logger.info(f"  总数据块数: {metrics['total_chunks']}")
        logger.info(f"  平均块间隔: {metrics['avg_chunk_interval']*1000:.2f}毫秒")
        logger.info(f"  内容生成速度: {metrics['content_generation_speed']:.2f}字符/秒")


if __name__ == "__main__":
    # 直接运行时执行pytest
    pytest.main([__file__, "-v"])