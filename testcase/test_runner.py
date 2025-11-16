"""
测试用例执行框架模块
提供通用的API测试执行功能
"""
import datetime
import json
import traceback
from typing import Dict, List, Any, Optional, Callable
import pytest

from common import BaseUtil, exceptions
from common.decorators import retry, log_function
from config.settings import DynamicParam
from utils import (
    get_test_cases,
    get_project_config,
    HttpClient,
    logger,
    TestCaseManager
)


class TestRunner:
    """
    通用测试运行器类
    负责测试用例的加载、执行和结果处理
    """
    
    def __init__(self, project_name: str, base_url: Optional[str] = None):
        """
        初始化测试运行器
        
        Args:
            project_name: 项目名称
            base_url: 基础URL，如果不提供则从配置获取
        """
        self.project_name = project_name
        self.base_url = base_url or get_project_config(project_name, 'url_api')
        if not self.base_url:
            raise exceptions.ConfigError(f"项目 {project_name} 的基础URL配置不存在")
            
        self.http_client = HttpClient(base_url=self.base_url)
        self.case_manager = TestCaseManager()
        self.start_time = datetime.datetime.now()
        self.test_results = []
        
        logger.info(f"测试运行器初始化完成 - 项目: {project_name}, 基础URL: {self.base_url}")
    
    def load_test_cases(self, run_only: bool = True) -> List[Dict[str, Any]]:
        """
        加载测试用例
        
        Args:
            run_only: 是否只加载启用的测试用例
            
        Returns:
            测试用例列表
        """
        return get_test_cases(self.project_name, run_only)
    
    @log_function
    def process_test_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个测试用例
        
        Args:
            case: 测试用例数据
            
        Returns:
            测试结果字典
        """
        start_time = datetime.datetime.now()
        result = {
            'case_id': case.get('id'),
            'case_name': case.get('title', '未命名'),
            'status': 'failed',
            'response': None,
            'error': None,
            'execution_time': 0
        }
        
        try:
            logger.info(f"执行测试用例: {result['case_name']} (ID: {result['case_id']})")
            
            # 解析测试用例数据
            url = case.get('url', '')
            method = case.get('method', 'GET').upper()
            headers = self._parse_data(case.get('headers', '{}'))
            cookies = self._parse_data(case.get('cookies', '{}'))
            request_body = self._parse_data(case.get('request_body', '{}'))
            relation = case.get('relation', None)
            
            # 处理关联参数
            headers = self._process_correlation(headers)
            cookies = self._process_correlation(cookies)
            request_body = self._process_correlation(request_body)
            
            # 发送请求
            response = self.http_client.request(
                method=method,
                url=url,
                headers=headers,
                cookies=cookies,
                **request_body
            )
            
            result['response'] = response
            
            # 处理关联数据
            if relation and response:
                self._extract_correlation_data(relation, response)
            
            # 验证结果
            self._validate_response(case, response)
            result['status'] = 'passed'
            logger.info(f"测试用例 {result['case_name']} 执行成功")
            
        except Exception as e:
            error_info = str(e)
            error_trace = traceback.format_exc()
            result['error'] = error_info
            logger.error(f"测试用例 {result['case_name']} 执行失败: {error_info}")
            logger.debug(f"错误详情: {error_trace}")
            raise
        
        finally:
            # 计算执行时间
            execution_time = (datetime.datetime.now() - start_time).total_seconds()
            result['execution_time'] = execution_time
            
            # 保存测试结果
            self.test_results.append(result)
            
            # 更新到数据库
            self._update_test_result(case.get('id'), result)
            
            logger.info(f"测试用例 {result['case_name']} 执行完成，耗时: {execution_time:.3f}s")
        
        return result
    
    @staticmethod
    def _parse_data(data_str: str) -> Dict[str, Any]:
        """
        解析字符串格式的数据
        
        Args:
            data_str: 字符串格式的数据
            
        Returns:
            解析后的字典
        """
        if not data_str or data_str.strip() == '':
            return {}
        
        try:
            # 尝试JSON解析
            if data_str.startswith('{') and data_str.endswith('}'):
                return json.loads(data_str)
            # 尝试eval解析
            return eval(data_str)
        except (json.JSONDecodeError, SyntaxError):
            logger.warning(f"无法解析数据: {data_str}，返回空字典")
            return {}
    
    def _process_correlation(self, data: Any) -> Any:
        """
        处理关联参数
        
        Args:
            data: 待处理的数据
            
        Returns:
            处理后的数据
        """
        # 先转换为字符串进行处理
        if isinstance(data, dict):
            data_str = json.dumps(data)
        else:
            data_str = str(data)
        
        # 查找所有的${变量名}格式的关联参数
        correlation_keys = BaseUtil.find(data_str)
        
        if not correlation_keys:
            return data
        
        # 构建替换字典
        replace_dict = {}
        for key in correlation_keys:
            value = getattr(DynamicParam, key, None)
            if value is not None:
                replace_dict[key] = value
                logger.debug(f"关联替换: ${key} -> {value}")
        
        # 执行替换
        if replace_dict:
            result_str = BaseUtil.replace(data_str, replace_dict)
            # 如果原数据是字典，转换回字典
            if isinstance(data, dict):
                return json.loads(result_str)
            return result_str
        
        return data
    
    def _extract_correlation_data(self, relation: str, response: Dict[str, Any]) -> None:
        """
        从响应中提取关联数据
        
        Args:
            relation: 关联表达式
            response: 响应数据
        """
        if not relation or relation == 'None':
            return
        
        try:
            # 支持多种格式的关联表达式
            if '=' in relation:
                parts = relation.split('=')
                if len(parts) == 2:
                    var_name, var_path = parts
                    var_name = var_name.strip()
                    var_path = var_path.strip()
                    
                    # 从响应中提取值
                    value = BaseUtil.deep_get(response, var_path)
                    if value is not None:
                        setattr(DynamicParam, var_name, value)
                        logger.debug(f"关联数据提取: {var_name} = {value}")
        except Exception as e:
            logger.error(f"提取关联数据失败: {str(e)}")
    
    def _validate_response(self, case: Dict[str, Any], response: Dict[str, Any]) -> None:
        """
        验证响应结果
        
        Args:
            case: 测试用例
            response: 响应数据
            
        Raises:
            AssertionError: 断言失败时抛出
        """
        # 获取预期结果
        expected_code = case.get('expected_code')
        
        # 如果没有预期结果，跳过验证
        if not expected_code:
            logger.warning(f"测试用例 {case.get('title')} 没有设置预期结果")
            return
        
        # 从响应中提取各种可能的结果字段
        actual_results = []
        
        # 检查body中的各种字段
        body = response.get('body', {})
        if isinstance(body, dict):
            actual_results.append(str(body.get('msg', '')))
            actual_results.append(str(body.get('message', '')))
            actual_results.append(str(body.get('success', '')))
        
        # 检查根级别的code字段
        actual_results.append(str(response.get('code', '')))
        
        # 执行断言
        expected_str = str(expected_code)
        assertion_passed = expected_str in actual_results
        
        if not assertion_passed:
            error_msg = (
                f"断言失败: 预期 '{expected_str}' 未在实际结果中找到\n"
                f"实际结果: {actual_results}\n"
                f"响应详情: {response}"
            )
            logger.error(error_msg)
            raise AssertionError(error_msg)
        
        logger.info(f"断言成功: 预期 '{expected_str}' 在实际结果中找到")
    
    def _update_test_result(self, case_id: int, result: Dict[str, Any]) -> None:
        """
        更新测试结果到数据库
        
        Args:
            case_id: 测试用例ID
            result: 测试结果
        """
        try:
            is_pass = 'True' if result['status'] == 'passed' else 'False'
            self.case_manager.updateResults(
                response=result.get('response', {}),
                is_pass=is_pass,
                case_id=str(case_id)
            )
        except Exception as e:
            logger.error(f"更新测试结果到数据库失败: {str(e)}")
    
    def generate_report(self) -> Dict[str, Any]:
        """
        生成测试报告
        
        Returns:
            测试报告字典
        """
        end_time = datetime.datetime.now()
        total_time = (end_time - self.start_time).total_seconds()
        
        total_cases = len(self.test_results)
        passed_cases = sum(1 for r in self.test_results if r['status'] == 'passed')
        failed_cases = total_cases - passed_cases
        
        report = {
            'project_name': self.project_name,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_time': round(total_time, 3),
            'total_cases': total_cases,
            'passed_cases': passed_cases,
            'failed_cases': failed_cases,
            'pass_rate': round(passed_cases / total_cases * 100, 2) if total_cases > 0 else 0,
            'details': self.test_results
        }
        
        logger.info(
            f"测试报告生成完成\n"
            f"总测试用例: {total_cases}, 通过: {passed_cases}, 失败: {failed_cases}\n"
            f"通过率: {report['pass_rate']}%, 总耗时: {report['total_time']}s"
        )
        
        return report


# Pytest测试类
class TestAPI:
    """
    用于Pytest运行的测试类
    """
    
    # 类变量，保存测试运行器实例
    _runner = None
    
    @classmethod
    def setup_class(cls):
        """
        类级别的初始化
        """
        # 这里可以配置不同的项目
        project_name = 'okr-api'  # 可以从配置文件或环境变量中获取
        cls._runner = TestRunner(project_name)
        logger.info(f"***** 开始执行测试用例，项目: {project_name} *****")
    
    @classmethod
    def teardown_class(cls):
        """
        类级别的清理
        """
        if cls._runner:
            report = cls._runner.generate_report()
            logger.info(f"***** 测试用例执行完成，通过率: {report['pass_rate']}% *****")
    
    @pytest.mark.parametrize('case', get_test_cases('okr-api', run_only=True))
    def test_run(self, case):
        """
        执行测试用例
        """
        result = self.__class__._runner.process_test_case(case)
        assert result['status'] == 'passed', f"测试用例执行失败: {result.get('error')}"


# 主程序执行入口
if __name__ == '__main__':
    pytest.main(['-s', '-v', 'test_runner.py'])