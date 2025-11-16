import unittest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.configutil import ConfigUtil
from utils.logutil import LogUtil

class TestConfigAndLog(unittest.TestCase):
    
    def setUp(self):
        self.config_util = ConfigUtil()
        self.log_util = LogUtil()
    
    def test_config_loading(self):
        # 测试配置加载
        config = self.config_util.load_config()
        self.assertIsInstance(config, dict)
        # 验证是否包含必要的配置项
        # 注意：这里的测试会根据实际的配置文件内容进行调整
    
    def test_get_config_value(self):
        # 测试获取配置值
        # 测试默认值功能
        default_value = self.config_util.get('non_existent_key', 'default_value')
        self.assertEqual(default_value, 'default_value')
    
    def test_log_util_init(self):
        # 测试日志工具初始化
        self.assertIsNotNone(self.log_util.logger)
        self.assertEqual(self.log_util.logger.name, 'ApiTestFramework')
    
    def test_log_methods(self):
        # 测试不同级别的日志方法（不实际写入文件，只验证方法存在且可调用）
        try:
            self.log_util.info('This is an info log')
            self.log_util.error('This is an error log')
            self.log_util.warning('This is a warning log')
            self.log_util.debug('This is a debug log')
            success = True
        except Exception:
            success = False
        self.assertTrue(success)
    
    def test_user_logger(self):
        # 测试用户日志功能
        user_logger = self.log_util.get_user_logger('test_user')
        self.assertIsNotNone(user_logger)
        self.assertEqual(user_logger.name, 'test_user')
        try:
            user_logger.info('This is a user log')
            success = True
        except Exception:
            success = False
        self.assertTrue(success)

if __name__ == '__main__':
    unittest.main()