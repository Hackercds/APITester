import unittest
from unittest.mock import patch, MagicMock
import requests
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_auto_framework import ApiTestFramework

class TestApiRequests(unittest.TestCase):
    
    def setUp(self):
        # 初始化测试环境
        self.api = ApiTestFramework()
    
    @patch('requests.request')
    def test_send_request_success(self, mock_request):
        # 模拟成功的API请求
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True, 'data': 'test'}
        mock_request.return_value = mock_response
        
        # 执行测试
        result = self.api.send_request('GET', 'https://api.example.com/test')
        
        # 验证结果
        self.assertEqual(result['status_code'], 200)
        self.assertTrue(result['json']['success'])
        mock_request.assert_called_once_with(
            'GET', 'https://api.example.com/test', 
            headers=None, params=None, data=None, json=None,
            timeout=30
        )
    
    @patch('requests.request')
    def test_send_request_with_headers(self, mock_request):
        # 测试带headers的请求
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'success': True}
        mock_request.return_value = mock_response
        
        headers = {'Authorization': 'Bearer token123', 'Content-Type': 'application/json'}
        result = self.api.send_request('POST', 'https://api.example.com/test', headers=headers)
        
        self.assertEqual(result['status_code'], 200)
        mock_request.assert_called_once()
        called_headers = mock_request.call_args[1]['headers']
        self.assertEqual(called_headers['Authorization'], 'Bearer token123')
    
    @patch('requests.request')
    def test_send_request_with_body(self, mock_request):
        # 测试带JSON body的请求
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'created': True}
        mock_request.return_value = mock_response
        
        body = {'name': 'test', 'value': 123}
        result = self.api.send_request('POST', 'https://api.example.com/create', json=body)
        
        self.assertEqual(result['status_code'], 201)
        mock_request.assert_called_once()
        called_json = mock_request.call_args[1]['json']
        self.assertEqual(called_json, body)
    
    @patch('requests.request')
    def test_send_request_failure(self, mock_request):
        # 测试请求失败的情况
        mock_request.side_effect = requests.exceptions.RequestException("Connection error")
        
        with self.assertRaises(requests.exceptions.RequestException):
            self.api.send_request('GET', 'https://api.example.com/test')

if __name__ == '__main__':
    unittest.main()