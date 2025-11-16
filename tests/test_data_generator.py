import unittest
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.randomutil import DataGenerator

class TestDataGenerator(unittest.TestCase):
    
    def setUp(self):
        self.data_generator = DataGenerator()
    
    def test_generate_email(self):
        # 测试生成邮箱
        email = self.data_generator.generate('email')
        self.assertIsInstance(email, str)
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        self.assertTrue(re.match(email_pattern, email))
    
    def test_generate_mobile(self):
        # 测试生成手机号
        mobile = self.data_generator.generate('mobile')
        self.assertIsInstance(mobile, str)
        # 验证手机号格式（简单验证）
        self.assertTrue(len(mobile) == 11)
        self.assertTrue(mobile.isdigit())
    
    def test_generate_id_card(self):
        # 测试生成身份证号
        id_card = self.data_generator.generate('id_card')
        self.assertIsInstance(id_card, str)
        self.assertTrue(len(id_card) == 18)
    
    def test_generate_text(self):
        # 测试生成文本
        text = self.data_generator.generate('text', {'length': 10})
        self.assertIsInstance(text, str)
        self.assertEqual(len(text), 10)
    
    def test_generate_integer(self):
        # 测试生成整数
        integer = self.data_generator.generate('integer', {'min': 10, 'max': 20})
        self.assertIsInstance(integer, int)
        self.assertTrue(10 <= integer <= 20)
    
    def test_generate_datetime(self):
        # 测试生成日期时间
        datetime_str = self.data_generator.generate('datetime')
        self.assertIsInstance(datetime_str, str)
        # 验证日期时间格式
        datetime_pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$'
        self.assertTrue(re.match(datetime_pattern, datetime_str))
    
    def test_generate_uuid(self):
        # 测试生成UUID
        uuid_str = self.data_generator.generate('uuid')
        self.assertIsInstance(uuid_str, str)
        # 验证UUID格式
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        self.assertTrue(re.match(uuid_pattern, uuid_str))

if __name__ == '__main__':
    unittest.main()