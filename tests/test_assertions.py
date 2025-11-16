import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.assertutil import AssertUtil

class TestAssertions(unittest.TestCase):
    
    def setUp(self):
        self.assert_util = AssertUtil()
    
    def test_assert_equal(self):
        # 测试相等断言
        result = self.assert_util.assert_equal(10, 10)
        self.assertTrue(result['success'])
        
        result = self.assert_util.assert_equal('test', 'test')
        self.assertTrue(result['success'])
        
        result = self.assert_util.assert_equal(10, 20)
        self.assertFalse(result['success'])
        self.assertIn('Expected 10, but got 20', result['message'])
    
    def test_assert_contains(self):
        # 测试包含断言
        result = self.assert_util.assert_contains('hello world', 'world')
        self.assertTrue(result['success'])
        
        result = self.assert_util.assert_contains('hello world', 'test')
        self.assertFalse(result['success'])
        self.assertIn('Expected string to contain', result['message'])
    
    def test_assert_json_path(self):
        # 测试JSON Path断言
        json_data = {'user': {'name': 'test', 'age': 25}, 'data': [1, 2, 3]}
        
        result = self.assert_util.assert_json_path(json_data, '$.user.name', 'test')
        self.assertTrue(result['success'])
        
        result = self.assert_util.assert_json_path(json_data, '$.user.age', 25)
        self.assertTrue(result['success'])
        
        result = self.assert_util.assert_json_path(json_data, '$.user.address', 'beijing')
        self.assertFalse(result['success'])
        
        result = self.assert_util.assert_json_path(json_data, '$.data[0]', 1)
        self.assertTrue(result['success'])
    
    def test_assert_status_code(self):
        # 测试状态码断言
        result = self.assert_util.assert_status_code(200, 200)
        self.assertTrue(result['success'])
        
        result = self.assert_util.assert_status_code(200, 404)
        self.assertFalse(result['success'])
        self.assertIn('Expected status code 200, but got 404', result['message'])

if __name__ == '__main__':
    unittest.main()