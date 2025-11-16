#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
框架功能验证脚本
用于验证重构后的框架核心功能是否正常工作
"""

import os
import sys
import json
import logging
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入框架核心组件
try:
    # 尝试直接从utils模块导入（利用__init__.py中的别名）
    from utils import RequestManager
    from config.settings import ConfigManager
    import logging
    logger = logging.getLogger(__name__)
except ImportError as e:
    # 如果导入失败，输出详细错误信息并尝试备用导入方式
    print(f"直接导入失败: {e}")
    try:
        # 尝试直接导入具体模块
        from utils.requestsutil import HttpClient as RequestManager
        import logging
        logger = logging.getLogger(__name__)
        from config.settings import ConfigManager
        print("备用导入方式成功")
    except ImportError as e2:
        print(f"备用导入也失败: {e2}")
        raise

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入框架核心模块
try:
    # 尝试直接从框架根模块导入
    from api_auto_framework import ApiTestFramework
    logger.info("成功导入ApiTestFramework")
except ImportError:
    logger.warning("无法直接导入ApiTestFramework，尝试从utils导入")

try:
    from utils import RequestManager, ConfigManager, LogUtil
    logger.info("成功从utils导入核心组件")
except ImportError as e:
    logger.error(f"从utils导入失败: {e}")
    try:
        # 备用导入方式
        from utils.requestutil import RequestManager
        from utils.configutil import ConfigManager
        from utils.logutil import LogUtil
        logger.info("备用导入方式成功")
    except Exception as fallback_error:
        logger.error(f"备用导入也失败: {fallback_error}")
        raise ImportError("无法导入必要的框架组件")

def verify_http_client_basic_functionality():
    """
    验证HTTP请求功能（使用RequestManager）
    """
    logger.info("开始验证 HTTP请求功能...")
    
    # 创建RequestManager实例
    try:
        request_manager = RequestManager(timeout=10)
        logger.info("RequestManager 实例创建成功")
        
        # 测试GET请求
        logger.info("测试 GET 请求...")
        response = request_manager.get("https://httpbin.org/get", params={"test": "value"})
        logger.info(f"GET 请求成功，状态码: {response['status_code']}")
        assert response['status_code'] == 200
        assert "args" in response['json']
        assert response['json']["args"]["test"] == "value"
        logger.info("GET 请求验证通过")
        
        # 测试POST请求
        logger.info("测试 POST 请求...")
        post_data = {"key": "value", "number": 123}
        response = request_manager.post("https://httpbin.org/post", json_data=post_data)
        logger.info(f"POST 请求成功，状态码: {response['status_code']}")
        assert response['status_code'] == 200
        assert "json" in response['json']
        assert response['json']['json'] == post_data
        logger.info("POST 请求验证通过")
        
        # 测试请求头设置
        logger.info("测试 请求头设置...")
        custom_header = {"X-Custom-Header": "test_value"}
        response = request_manager.get("https://httpbin.org/headers", headers=custom_header)
        assert response['status_code'] == 200
        assert "headers" in response['json']
        assert response['json']['headers']['X-Custom-Header'] == "test_value"
        logger.info("请求头设置验证通过")
        
        # 测试404状态码处理
        logger.info("测试 404状态码处理...")
        response = request_manager.get("https://httpbin.org/status/404")
        assert response['status_code'] == 404
        logger.info("404状态码处理验证通过")
        
        logger.info("HTTP请求功能验证通过")
        return True
    except Exception as e:
        logger.error(f"HTTP请求功能验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_request_manager_functionality():
    """
    验证RequestManager的功能
    """
    logger.info("开始验证 RequestManager 功能...")
    
    try:
        # 创建RequestManager实例
        request_manager = RequestManager(
            timeout=10,
            retry_count=3,
            retry_backoff_factor=0.3
        )
        logger.info("RequestManager 实例创建成功")
        
        # 测试基本请求
        logger.info("测试 基本请求...")
        response = request_manager.request("GET", "https://httpbin.org/get")
        assert response['status_code'] == 200
        logger.info("基本请求验证通过")
        
        # 测试认证功能
        logger.info("测试 认证功能...")
        # 创建一个简单的认证管理器
        class SimpleAuth:
            def add_auth(self, request_data):
                if "headers" not in request_data:
                    request_data["headers"] = {}
                request_data["headers"]["Authorization"] = "Bearer test_token"
                return request_data
        
        request_manager.set_auth_manager(SimpleAuth())
        response = request_manager.get("https://httpbin.org/headers")
        assert "Authorization" in response['json']['headers']
        assert response['json']['headers']['Authorization'] == "Bearer test_token"
        logger.info("认证功能验证通过")
        
        # 测试响应处理
        logger.info("测试 响应处理...")
        # 使用默认的响应处理器
        response = request_manager.get("https://httpbin.org/get")
        assert 'status_code' in response
        assert 'json' in response
        logger.info("响应处理验证通过")
        
        logger.info("RequestManager 功能验证通过")
        return True
        
    except Exception as e:
        logger.error(f"RequestManager 功能验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_config_functionality():
    """
    验证配置管理功能
    """
    logger.info("开始验证 配置管理功能...")
    
    try:
        # 测试配置读取
        logger.info("测试 配置读取...")
        config = ConfigManager()
        # 验证ConfigManager实例正常
        assert config is not None
        logger.info("配置实例创建验证通过")
        
        # 测试基本配置访问
        logger.info("测试 基本配置访问...")
        # 访问一些已知的配置属性
        if hasattr(config, 'api_config'):
            assert config.api_config is not None
            logger.info("API配置访问验证通过")
        
        logger.info("配置管理功能验证通过")
        return True
        
    except Exception as e:
        logger.error(f"配置管理功能验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def run_comprehensive_verification():
    """
    运行全面的框架功能验证
    """
    logger.info("开始全面验证接口自动化框架功能...")
    
    results = {
        "http_client": verify_http_client_basic_functionality(),
        "request_manager": verify_request_manager_functionality(),
        "config": verify_config_functionality()
    }
    
    # 汇总结果
    logger.info("\n===== 验证结果汇总 =====")
    all_passed = True
    
    for component, passed in results.items():
        status = "通过" if passed else "失败"
        logger.info(f"{component}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\n🎉 恭喜！所有核心功能验证通过！")
    else:
        logger.error("\n❌ 警告！部分功能验证失败，请检查相关组件。")
    
    return all_passed

if __name__ == "__main__":
    logger.info("========================================")
    logger.info("         接口自动化框架功能验证        ")
    logger.info("========================================")
    
    success = run_comprehensive_verification()
    
    logger.info("========================================")
    logger.info("验证完成！")
    logger.info("========================================")
    
    # 根据验证结果设置退出码
    sys.exit(0 if success else 1)