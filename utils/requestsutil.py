# 导入Requests库
"""
HTTP请求工具模块
提供增强的HTTP请求功能，支持智能重试、流式响应、动态参数等特性
"""
import json
import time
import random
import threading
import statistics
import string
import re
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Union, Any, Tuple, Generator, Callable, Pattern
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
from utils.logutil import logger

# 导入认证工具
from utils.authutil import AuthManager, create_auth_manager as default_auth_manager

# 导入并发控制工具
from utils.concurrencyutil import (
    RateLimiter, ConcurrentExecutor, ConcurrencyManager,
    limited_concurrency, run_with_rate_limit
)
# 禁用不安全请求警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class RandomContentGenerator:
    """
    随机内容生成器，用于生成测试数据和大模型接口测试所需的随机字符
    """
    
    def __init__(self):
        # 常用的中文汉字集，用于生成更真实的中文文本
        self.common_chinese_chars = "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市克何除消构府称太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严"
        # 常见的英文单词，用于生成更真实的英文文本
        self.common_english_words = [
            "the", "be", "to", "of", "and", "a", "in", "that", "have", "I",
            "it", "for", "not", "with", "he", "as", "you", "do", "at", "this",
            "but", "his", "by", "from", "they", "we", "say", "her", "she", "or",
            "an", "will", "my", "one", "all", "would", "there", "their", "what", "so"
        ]
    
    def random_string(self, length: int = 10, charset: str = None) -> str:
        """
        生成指定长度的随机字符串
        
        Args:
            length: 字符串长度
            charset: 字符集，默认为大小写字母和数字
            
        Returns:
            随机生成的字符串
        """
        if charset is None:
            charset = string.ascii_letters + string.digits
        return ''.join(random.choice(charset) for _ in range(length))
    
    def random_chinese(self, length: int = 10) -> str:
        """
        生成指定长度的随机中文字符串
        
        Args:
            length: 字符串长度
            
        Returns:
            随机生成的中文字符串
        """
        return ''.join(random.choice(self.common_chinese_chars) for _ in range(length))
    
    def random_english_sentence(self, word_count: int = 10) -> str:
        """
        生成随机英文句子
        
        Args:
            word_count: 单词数量
            
        Returns:
            随机生成的英文句子
        """
        words = [random.choice(self.common_english_words) for _ in range(word_count)]
        # 首字母大写，添加标点
        if words:
            words[0] = words[0].capitalize()
        return ' '.join(words) + '.'
    
    def random_chinese_paragraph(self, char_count: int = 100) -> str:
        """
        生成随机中文段落
        
        Args:
            char_count: 字符数量
            
        Returns:
            随机生成的中文段落
        """
        return ''.join(random.choice(self.common_chinese_chars) for _ in range(char_count))
    
    def generate_from_token_list(self, token_list: List[str], count: int = 10, min_length: int = 5) -> str:
        """
        从给定的token列表中随机选择生成文本
        适用于根据模型分词表生成测试文本
        
        Args:
            token_list: token列表
            count: 选择的token数量
            min_length: 最小文本长度
            
        Returns:
            生成的文本
        """
        result = []
        current_length = 0
        
        while current_length < min_length or len(result) < count:
            token = random.choice(token_list)
            result.append(token)
            current_length += len(token)
        
        return ''.join(result)
    
    def generate_test_data(self, data_type: str, **kwargs) -> Any:
        """
        生成各种类型的测试数据
        
        Args:
            data_type: 数据类型 (string, number, boolean, list, dict, chinese, english)
            **kwargs: 其他参数
            
        Returns:
            生成的测试数据
        """
        if data_type == "string":
            length = kwargs.get("length", 10)
            return self.random_string(length)
        elif data_type == "number":
            min_val = kwargs.get("min", 0)
            max_val = kwargs.get("max", 100)
            is_float = kwargs.get("is_float", False)
            if is_float:
                return random.uniform(min_val, max_val)
            return random.randint(min_val, max_val)
        elif data_type == "boolean":
            return random.choice([True, False])
        elif data_type == "list":
            item_type = kwargs.get("item_type", "string")
            length = kwargs.get("length", 5)
            return [self.generate_test_data(item_type, **kwargs) for _ in range(length)]
        elif data_type == "dict":
            fields = kwargs.get("fields", {"key": "string"})
            return {k: self.generate_test_data(v, **kwargs) for k, v in fields.items()}
        elif data_type == "chinese":
            length = kwargs.get("length", 10)
            return self.random_chinese(length)
        elif data_type == "english":
            word_count = kwargs.get("word_count", 10)
            return self.random_english_sentence(word_count)
        else:
            return self.random_string()


# 创建全局随机内容生成器实例
default_random_generator = RandomContentGenerator()


class PerformanceTester:
    """
    性能测试类，提供自动爬坡找极限性能功能
    支持智能爬坡算法、多路径测试、详细性能指标和报告生成
    """
    
    def __init__(self, http_client, base_url=None, path="/"):
        """
        初始化性能测试器
        
        Args:
            http_client: HttpClient实例
            base_url: 基础URL
            path: 测试路径
        """
        self.http_client = http_client
        self.base_url = base_url or http_client.base_url
        self.path = path
        self.results = []
        self.stop_event = threading.Event()
        self.current_test_id = time.strftime("%Y%m%d_%H%M%S")
        self.error_details = {}  # 错误类型统计
    
    def _test_request(self, method='GET', params=None, data=None, json_data=None, headers=None, path=None, **kwargs):
        """
        执行单个测试请求
        
        Args:
            method: 请求方法
            params: 请求参数
            data: 请求数据
            json_data: JSON数据
            headers: 请求头
            path: 可选的特定路径
            **kwargs: 其他参数
            
        Returns:
            (是否成功, 响应时间, 错误信息, 错误类型)
        """
        start_time = time.time()
        try:
            current_path = path or self.path
            url = urljoin(self.base_url, current_path)
            response = self.http_client.send_request(
                method=method,
                url=url,
                params=params,
                data=data,
                json_data=json_data,
                headers=headers,
                **kwargs
            )
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            success = response.status_code < 400
            error_msg = f"HTTP错误: {response.status_code}" if not success else None
            error_type = f"HTTP_{response.status_code}" if not success else None
            return success, response_time, error_msg, error_type
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_type = type(e).__name__
            error_msg = str(e)
            return False, response_time, error_msg, error_type
    
    def _run_concurrent_tests(self, concurrency, duration, paths=None, path_weights=None, **request_kwargs):
        """
        以指定并发数运行测试，支持多路径混合测试
        
        Args:
            concurrency: 并发数
            duration: 测试持续时间（秒）
            paths: 要测试的路径列表
            path_weights: 路径权重字典，控制各路径的请求比例
            request_kwargs: 请求参数
            
        Returns:
            测试结果字典
        """
        results = []
        path_results = {}
        if paths:
            for path in paths:
                path_results[path] = []
        
        stop_time = time.time() + duration
        active_count = threading.Semaphore(concurrency)
        
        # 错误类型统计
        error_types = {}
        
        # 准备路径选择器
        if paths:
            if path_weights:
                # 基于权重选择路径
                weighted_paths = []
                for path, weight in path_weights.items():
                    weighted_paths.extend([path] * weight)
                path_selector = lambda: random.choice(weighted_paths)
            else:
                # 等概率选择路径
                path_selector = lambda: random.choice(paths)
        else:
            path_selector = lambda: None
        
        def worker():
            while time.time() < stop_time and not self.stop_event.is_set():
                with active_count:
                    if self.stop_event.is_set():
                        break
                    # 选择当前请求的路径
                    current_path = path_selector()
                    success, response_time, error, error_type = self._test_request(
                        path=current_path, **request_kwargs
                    )
                    
                    result = {
                        'success': success,
                        'response_time': response_time,
                        'error': error,
                        'error_type': error_type,
                        'path': current_path
                    }
                    results.append(result)
                    
                    # 按路径统计
                    if current_path and paths:
                        path_results[current_path].append(result)
                    
                    # 统计错误类型
                    if not success and error_type:
                        error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # 创建线程
        threads = []
        for _ in range(concurrency):
            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 计算总体结果
        total_requests = len(results)
        success_count = sum(1 for r in results if r['success'])
        error_count = total_requests - success_count
        error_rate = error_count / total_requests if total_requests > 0 else 0
        
        response_times = [r['response_time'] for r in results if r['success']]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        # 计算更多统计指标
        p90_response_time = 0
        p95_response_time = 0
        p99_response_time = 0
        if response_times:
            sorted_times = sorted(response_times)
            p90_response_time = sorted_times[int(len(sorted_times) * 0.90)]
            p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
            p99_response_time = sorted_times[int(len(sorted_times) * 0.99)]
        
        tps = total_requests / duration if duration > 0 else 0
        
        # 计算路径级别的统计
        path_stats = {}
        if paths:
            for path, path_data in path_results.items():
                if path_data:
                    path_success = sum(1 for r in path_data if r['success'])
                    path_times = [r['response_time'] for r in path_data if r['success']]
                    path_stats[path] = {
                        'total_requests': len(path_data),
                        'success_count': path_success,
                        'error_count': len(path_data) - path_success,
                        'error_rate': (len(path_data) - path_success) / len(path_data) if path_data else 0,
                        'avg_response_time': statistics.mean(path_times) if path_times else 0
                    }
        
        # 汇总结果
        result_dict = {
            'concurrency': concurrency,
            'duration': duration,
            'total_requests': total_requests,
            'success_count': success_count,
            'error_count': error_count,
            'error_rate': error_rate,
            'avg_response_time': avg_response_time,
            'p90_response_time': p90_response_time,
            'p95_response_time': p95_response_time,
            'p99_response_time': p99_response_time,
            'tps': tps,
            'error_types': error_types,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 添加路径统计
        if path_stats:
            result_dict['path_stats'] = path_stats
        
        return result_dict
    
    def find_max_concurrency(self, start_concurrency=1, max_concurrency=100, 
                           step=1, duration=5, error_threshold=0.05, 
                           response_time_threshold=2000, scaling_strategy='linear',
                           paths=None, path_weights=None, **request_kwargs):
        """
        自动爬坡找最大并发数，支持多种爬坡策略
        
        Args:
            start_concurrency: 起始并发数
            max_concurrency: 最大并发数
            step: 每次增加的并发数
            duration: 每个并发级别测试的持续时间（秒）
            error_threshold: 错误率阈值，超过此值则认为系统达到瓶颈
            response_time_threshold: 响应时间阈值（毫秒）
            scaling_strategy: 爬坡策略，可选值：'linear'(线性增长), 'exponential'(指数增长), 'binary'(二分查找)
            paths: 要测试的路径列表
            path_weights: 路径权重字典，控制各路径的请求比例
            request_kwargs: 请求参数
            
        Returns:
            测试报告字典
        """
        self.results = []
        self.stop_event.clear()
        best_concurrency = start_concurrency
        
        try:
            # 根据策略生成并发数序列
            if scaling_strategy == 'linear':
                concurrency_sequence = range(start_concurrency, max_concurrency + 1, step)
            elif scaling_strategy == 'exponential':
                # 指数增长策略
                concurrency_sequence = []
                current = start_concurrency
                while current <= max_concurrency:
                    concurrency_sequence.append(current)
                    current = int(current * 1.5) + step  # 1.5倍增长加上基础步长
                # 确保不超过最大值
                concurrency_sequence = [c for c in concurrency_sequence if c <= max_concurrency]
            elif scaling_strategy == 'binary':
                # 二分查找策略
                concurrency_sequence = self._generate_binary_search_sequence(start_concurrency, max_concurrency)
            else:
                raise ValueError(f"不支持的爬坡策略: {scaling_strategy}")
            
            # 记录最佳性能指标
            best_tps = 0
            best_avg_response_time = float('inf')
            
            for concurrency in concurrency_sequence:
                if self.stop_event.is_set():
                    break
                    
                logger.info(f"测试并发数: {concurrency}, 策略: {scaling_strategy}")
                result = self._run_concurrent_tests(
                    concurrency, duration, paths=paths, path_weights=path_weights, **request_kwargs
                )
                self.results.append(result)
                
                # 更新最佳指标
                if result['tps'] > best_tps or (
                    result['tps'] == best_tps and result['avg_response_time'] < best_avg_response_time
                ):
                    best_tps = result['tps']
                    best_avg_response_time = result['avg_response_time']
                    best_concurrency = concurrency
                
                # 检查是否达到瓶颈
                if result['error_rate'] > error_threshold:
                    logger.warning(f"错误率({result['error_rate']:.2%})超过阈值({error_threshold:.2%})，停止测试")
                    # 在二分查找模式下，我们可能需要回退到上一个可用的并发数
                    if scaling_strategy == 'binary' and len(self.results) > 1:
                        prev_result = self.results[-2]
                        if prev_result['error_rate'] <= error_threshold:
                            logger.info(f"回退到上一个成功的并发数: {prev_result['concurrency']}")
                            best_concurrency = prev_result['concurrency']
                    break
                
                if result['avg_response_time'] > response_time_threshold:
                    logger.warning(f"平均响应时间({result['avg_response_time']:.2f}ms)超过阈值({response_time_threshold}ms)，停止测试")
                    break
                
                # 短暂休息，让系统恢复
                time.sleep(1)
            
            # 生成报告
            report = {
                'test_type': 'concurrency_scaling',
                'start_concurrency': start_concurrency,
                'max_concurrency': max_concurrency,
                'best_concurrency': best_concurrency,
                'best_tps': best_tps,
                'best_avg_response_time': best_avg_response_time,
                'error_threshold': error_threshold,
                'response_time_threshold': response_time_threshold,
                'step': step,
                'scaling_strategy': scaling_strategy,
                'duration_per_step': duration,
                'detailed_results': self.results,
                'test_id': self.current_test_id,
                'start_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() - len(self.results) * (duration + 1))),
                'end_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 保存错误详情
            for result in self.results:
                if result['error_types']:
                    self.error_details.update(result['error_types'])
            
            return report
            
        except KeyboardInterrupt:
            logger.warning("测试被用户中断")
            # 返回已收集的结果
            return self._generate_interrupted_report('concurrency_scaling', start_concurrency, max_concurrency)
        except Exception as e:
            logger.error(f"测试过程中出错: {str(e)}")
            return self._generate_interrupted_report('concurrency_scaling', start_concurrency, max_concurrency)
        finally:
            self.stop_event.set()
    
    def _generate_binary_search_sequence(self, start, end):
        """
        生成二分查找序列
        
        Args:
            start: 起始值
            end: 结束值
            
        Returns:
            二分查找序列列表
        """
        sequence = []
        if start == end:
            return [start]
            
        # 先生成初始的几个点，然后进行二分
        # 先测试起始点
        sequence.append(start)
        
        # 测试中间点
        mid = (start + end) // 2
        sequence.append(mid)
        
        # 测试终点
        sequence.append(end)
        
        # 添加一些中间点，确保覆盖合理的测试范围
        current = start
        while current < end:
            current = min(current * 2, end)
            if current not in sequence:
                sequence.append(current)
        
        # 排序并去重
        sequence = sorted(list(set(sequence)))
        
        return sequence
    
    def _generate_interrupted_report(self, test_type, start_value, max_value):
        """
        生成中断测试的报告
        
        Args:
            test_type: 测试类型
            start_value: 起始值
            max_value: 最大值
            
        Returns:
            报告字典
        """
        # 计算最佳值
        best_value = start_value
        best_tps = 0
        if self.results:
            # 选择TPS最高的结果
            best_result = max(self.results, key=lambda x: x.get('tps', 0))
            best_value = best_result.get('concurrency', start_value)
            best_tps = best_result.get('tps', 0)
        
        report = {
            'test_type': test_type,
            'start_value': start_value,
            'max_value': max_value,
            'best_value': best_value,
            'best_tps': best_tps,
            'interrupted': True,
            'detailed_results': self.results,
            'test_id': self.current_test_id,
            'message': "测试被中断或发生错误"
        }
        
        return report
    
    def find_max_tps(self, start_tps=1, max_tps=100, step=1, 
                    duration=5, error_threshold=0.05,
                    response_time_threshold=2000, scaling_strategy='linear',
                    paths=None, path_weights=None, **request_kwargs):
        """
        自动爬坡找最大TPS，支持多种爬坡策略和多路径测试
        
        Args:
            start_tps: 起始TPS
            max_tps: 最大TPS
            step: 每次增加的TPS数
            duration: 每个TPS级别测试的持续时间（秒）
            error_threshold: 错误率阈值
            response_time_threshold: 响应时间阈值（毫秒）
            scaling_strategy: 爬坡策略，可选值：'linear'(线性增长), 'exponential'(指数增长), 'binary'(二分查找)
            paths: 要测试的路径列表
            path_weights: 路径权重字典，控制各路径的请求比例
            request_kwargs: 请求参数
            
        Returns:
            测试报告字典
        """
        self.results = []
        self.stop_event.clear()
        best_tps = start_tps
        original_rate_limiter = None
        
        try:
            # 保存原始速率限制器
            original_rate_limiter = self.http_client.rate_limiter
            
            # 根据策略生成TPS序列
            if scaling_strategy == 'linear':
                tps_sequence = range(start_tps, max_tps + 1, step)
            elif scaling_strategy == 'exponential':
                # 指数增长策略
                tps_sequence = []
                current = start_tps
                while current <= max_tps:
                    tps_sequence.append(current)
                    current = int(current * 1.5) + step  # 1.5倍增长加上基础步长
                # 确保不超过最大值
                tps_sequence = [t for t in tps_sequence if t <= max_tps]
            elif scaling_strategy == 'binary':
                # 二分查找策略
                tps_sequence = self._generate_binary_search_sequence(start_tps, max_tps)
            else:
                raise ValueError(f"不支持的爬坡策略: {scaling_strategy}")
            
            # 记录最佳性能指标
            best_avg_response_time = float('inf')
            
            for tps in tps_sequence:
                if self.stop_event.is_set():
                    break
                    
                logger.info(f"测试TPS: {tps}, 策略: {scaling_strategy}")
                
                # 设置速率限制器
                self.http_client.rate_limiter = RateLimiter(rate=tps, time_unit=1.0)
                
                # 并发数设置为TPS的2倍，确保有足够的线程来达到目标TPS
                concurrency = max(tps * 2, 10)  # 至少10个并发
                
                result = self._run_concurrent_tests(
                    concurrency, duration, paths=paths, path_weights=path_weights, **request_kwargs
                )
                self.results.append(result)
                
                # 更新最佳指标
                actual_tps = result['tps']
                if actual_tps >= tps * 0.9 and (
                    actual_tps > best_tps or 
                    (actual_tps == best_tps and result['avg_response_time'] < best_avg_response_time)
                ):
                    # 只有当实际TPS接近目标TPS时才更新最佳值
                    best_tps = actual_tps
                    best_avg_response_time = result['avg_response_time']
                
                # 检查是否达到瓶颈
                if result['error_rate'] > error_threshold:
                    logger.warning(f"错误率({result['error_rate']:.2%})超过阈值({error_threshold:.2%})，停止测试")
                    break
                
                if result['avg_response_time'] > response_time_threshold:
                    logger.warning(f"平均响应时间({result['avg_response_time']:.2f}ms)超过阈值({response_time_threshold}ms)，停止测试")
                    break
                
                # 短暂休息，让系统恢复
                time.sleep(1)
            
            # 生成报告
            report = {
                'test_type': 'tps_scaling',
                'start_tps': start_tps,
                'max_tps': max_tps,
                'best_tps': best_tps,
                'best_avg_response_time': best_avg_response_time,
                'error_threshold': error_threshold,
                'response_time_threshold': response_time_threshold,
                'step': step,
                'scaling_strategy': scaling_strategy,
                'duration_per_step': duration,
                'detailed_results': self.results,
                'test_id': self.current_test_id,
                'start_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() - len(self.results) * (duration + 1))),
                'end_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 保存错误详情
            for result in self.results:
                if result['error_types']:
                    self.error_details.update(result['error_types'])
            
            return report
            
        except KeyboardInterrupt:
            logger.warning("测试被用户中断")
            return self._generate_interrupted_report('tps_scaling', start_tps, max_tps)
        except Exception as e:
            logger.error(f"测试过程中出错: {str(e)}")
            return self._generate_interrupted_report('tps_scaling', start_tps, max_tps)
        finally:
            self.stop_event.set()
            # 确保恢复原始速率限制器
            if original_rate_limiter is not None:
                self.http_client.rate_limiter = original_rate_limiter
    
    def generate_report(self, format='json', include_chart_data=False, save_to_file=None):
        """
        生成测试报告，支持多种格式和图表数据
        
        Args:
            format: 报告格式，支持'json', 'text', 'html'
            include_chart_data: 是否包含图表数据
            save_to_file: 是否保存到文件，None表示不保存，否则提供文件路径
            
        Returns:
            格式化的报告
        """
        if not self.results:
            return "暂无测试数据"
            
        # 准备基础报告数据
        report_data = {
            'test_id': self.current_test_id,
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_runs': len(self.results),
            'results': self.results,
            'error_summary': self.error_details
        }
        
        # 计算总体统计
        if self.results:
            total_requests = sum(r['total_requests'] for r in self.results)
            total_success = sum(r['success_count'] for r in self.results)
            total_errors = sum(r['error_count'] for r in self.results)
            
            all_response_times = []
            for r in self.results:
                if 'path_stats' in r:
                    for path_stats in r['path_stats'].values():
                        if path_stats['avg_response_time'] > 0:
                            all_response_times.append(path_stats['avg_response_time'])
                elif r['avg_response_time'] > 0:
                    all_response_times.append(r['avg_response_time'])
            
            overall_avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
            
            report_data.update({
                'total_requests': total_requests,
                'total_success': total_success,
                'total_errors': total_errors,
                'overall_error_rate': total_errors / total_requests if total_requests > 0 else 0,
                'overall_avg_response_time': overall_avg_response_time
            })
        
        # 添加图表数据
        if include_chart_data:
            chart_data = self._prepare_chart_data()
            report_data['chart_data'] = chart_data
        
        # 生成指定格式的报告
        if format == 'json':
            report_content = json.dumps(report_data, indent=2, ensure_ascii=False)
        elif format == 'text':
            report_content = self._generate_text_report(report_data)
        elif format == 'html':
            report_content = self._generate_html_report(report_data)
        else:
            raise ValueError(f"不支持的报告格式: {format}")
        
        # 保存到文件
        if save_to_file:
            try:
                with open(save_to_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                logger.info(f"报告已保存到: {save_to_file}")
            except Exception as e:
                logger.error(f"保存报告失败: {str(e)}")
        
        return report_content
    
    def _prepare_chart_data(self):
        """
        准备图表数据
        
        Returns:
            图表数据字典
        """
        # 提取并发数和TPS数据
        concurrency_values = []
        tps_values = []
        error_rates = []
        response_times = []
        
        for result in self.results:
            concurrency_values.append(result.get('concurrency', 0))
            tps_values.append(result.get('tps', 0))
            error_rates.append(result.get('error_rate', 0) * 100)  # 转换为百分比
            response_times.append(result.get('avg_response_time', 0))
        
        # 路径级别的数据
        path_data = {}
        for result in self.results:
            if 'path_stats' in result:
                for path, stats in result['path_stats'].items():
                    if path not in path_data:
                        path_data[path] = {
                            'concurrency': [],
                            'tps': [],
                            'response_time': []
                        }
                    
                    # 计算该路径的TPS
                    path_tps = stats['total_requests'] / result.get('duration', 1)
                    path_data[path]['concurrency'].append(result.get('concurrency', 0))
                    path_data[path]['tps'].append(path_tps)
                    path_data[path]['response_time'].append(stats.get('avg_response_time', 0))
        
        chart_data = {
            'main': {
                'concurrency': concurrency_values,
                'tps': tps_values,
                'error_rate': error_rates,
                'avg_response_time': response_times
            },
            'path_data': path_data
        }
        
        return chart_data
    
    def _generate_text_report(self, report_data):
        """
        生成文本格式的报告
        
        Args:
            report_data: 报告数据字典
            
        Returns:
            文本报告
        """
        lines = []
        lines.append("=" * 60)
        lines.append("          性能测试报告          ")
        lines.append("=" * 60)
        lines.append(f"测试ID: {report_data.get('test_id', 'N/A')}")
        lines.append(f"生成时间: {report_data.get('generated_at', 'N/A')}")
        lines.append(f"总运行次数: {report_data.get('total_runs', 0)}")
        lines.append("-" * 60)
        
        # 总体统计
        lines.append("【总体统计】")
        lines.append(f"总请求数: {report_data.get('total_requests', 0)}")
        lines.append(f"成功请求: {report_data.get('total_success', 0)}")
        lines.append(f"失败请求: {report_data.get('total_errors', 0)}")
        lines.append(f"总体错误率: {report_data.get('overall_error_rate', 0):.2%}")
        lines.append(f"平均响应时间: {report_data.get('overall_avg_response_time', 0):.2f}ms")
        lines.append("-" * 60)
        
        # 详细结果
        lines.append("【详细测试结果】")
        for i, result in enumerate(report_data['results'], 1):
            lines.append(f"测试 #{i}")
            lines.append(f"  并发数: {result.get('concurrency', 'N/A')}")
            lines.append(f"  持续时间: {result.get('duration', 'N/A')}秒")
            lines.append(f"  请求总数: {result.get('total_requests', 0)}")
            lines.append(f"  成功数: {result.get('success_count', 0)}")
            lines.append(f"  错误数: {result.get('error_count', 0)}")
            lines.append(f"  错误率: {result.get('error_rate', 0):.2%}")
            lines.append(f"  平均响应时间: {result.get('avg_response_time', 0):.2f}ms")
            lines.append(f"  P90响应时间: {result.get('p90_response_time', 0):.2f}ms")
            lines.append(f"  P95响应时间: {result.get('p95_response_time', 0):.2f}ms")
            lines.append(f"  P99响应时间: {result.get('p99_response_time', 0):.2f}ms")
            lines.append(f"  TPS: {result.get('tps', 0):.2f}")
            
            # 错误类型统计
            if result.get('error_types'):
                lines.append("  错误类型分布:")
                for error_type, count in result['error_types'].items():
                    lines.append(f"    {error_type}: {count}")
            
            # 路径统计
            if result.get('path_stats'):
                lines.append("  路径统计:")
                for path, stats in result['path_stats'].items():
                    lines.append(f"    路径 {path}:")
                    lines.append(f"      请求数: {stats.get('total_requests', 0)}")
                    lines.append(f"      平均响应时间: {stats.get('avg_response_time', 0):.2f}ms")
            
            lines.append("")
        
        # 错误总结
        if report_data.get('error_summary'):
            lines.append("【错误类型总结】")
            for error_type, count in report_data['error_summary'].items():
                lines.append(f"  {error_type}: {count}")
            lines.append("")
        
        lines.append("=" * 60)
        
        return '\n'.join(lines)
    
    def _generate_html_report(self, report_data):
        """
        生成HTML格式的报告
        
        Args:
            report_data: 报告数据字典
            
        Returns:
            HTML报告
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='zh-CN'>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "<title>性能测试报告</title>",
            "<style>",
            "  body { font-family: Arial, sans-serif; margin: 20px; }",
            "  h1, h2, h3 { color: #2c3e50; }",
            "  .header { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }",
            "  .summary { background-color: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px; }",
            "  .details { margin-bottom: 20px; }",
            "  .result-card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 15px; }",
            "  .error-type { background-color: #f8d7da; padding: 10px; border-radius: 3px; }",
            "  .path-stats { background-color: #e3f2fd; padding: 10px; border-radius: 3px; }",
            "  table { border-collapse: collapse; width: 100%; margin-top: 10px; }",
            "  th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }",
            "  th { background-color: #f2f2f2; }",
            "  tr:hover { background-color: #f5f5f5; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>性能测试报告</h1>",
        ]
        
        # 头部信息
        html_parts.append("<div class='header'>")
        html_parts.append(f"<p><strong>测试ID:</strong> {report_data.get('test_id', 'N/A')}</p>")
        html_parts.append(f"<p><strong>生成时间:</strong> {report_data.get('generated_at', 'N/A')}</p>")
        html_parts.append(f"<p><strong>总运行次数:</strong> {report_data.get('total_runs', 0)}</p>")
        html_parts.append("</div>")
        
        # 总体统计
        html_parts.append("<div class='summary'>")
        html_parts.append("<h2>总体统计</h2>")
        html_parts.append("<table>")
        html_parts.append("<tr><th>指标</th><th>值</th></tr>")
        html_parts.append(f"<tr><td>总请求数</td><td>{report_data.get('total_requests', 0)}</td></tr>")
        html_parts.append(f"<tr><td>成功请求</td><td>{report_data.get('total_success', 0)}</td></tr>")
        html_parts.append(f"<tr><td>失败请求</td><td>{report_data.get('total_errors', 0)}</td></tr>")
        html_parts.append(f"<tr><td>总体错误率</td><td>{report_data.get('overall_error_rate', 0):.2%}</td></tr>")
        html_parts.append(f"<tr><td>平均响应时间</td><td>{report_data.get('overall_avg_response_time', 0):.2f}ms</td></tr>")
        html_parts.append("</table>")
        html_parts.append("</div>")
        
        # 详细结果
        html_parts.append("<div class='details'>")
        html_parts.append("<h2>详细测试结果</h2>")
        
        for i, result in enumerate(report_data['results'], 1):
            html_parts.append(f"<div class='result-card'>")
            html_parts.append(f"<h3>测试 #{i}</h3>")
            html_parts.append("<table>")
            html_parts.append("<tr><th>指标</th><th>值</th></tr>")
            html_parts.append(f"<tr><td>并发数</td><td>{result.get('concurrency', 'N/A')}</td></tr>")
            html_parts.append(f"<tr><td>持续时间</td><td>{result.get('duration', 'N/A')}秒</td></tr>")
            html_parts.append(f"<tr><td>请求总数</td><td>{result.get('total_requests', 0)}</td></tr>")
            html_parts.append(f"<tr><td>成功数</td><td>{result.get('success_count', 0)}</td></tr>")
            html_parts.append(f"<tr><td>错误数</td><td>{result.get('error_count', 0)}</td></tr>")
            html_parts.append(f"<tr><td>错误率</td><td>{result.get('error_rate', 0):.2%}</td></tr>")
            html_parts.append(f"<tr><td>平均响应时间</td><td>{result.get('avg_response_time', 0):.2f}ms</td></tr>")
            html_parts.append(f"<tr><td>P90响应时间</td><td>{result.get('p90_response_time', 0):.2f}ms</td></tr>")
            html_parts.append(f"<tr><td>P95响应时间</td><td>{result.get('p95_response_time', 0):.2f}ms</td></tr>")
            html_parts.append(f"<tr><td>P99响应时间</td><td>{result.get('p99_response_time', 0):.2f}ms</td></tr>")
            html_parts.append(f"<tr><td>TPS</td><td>{result.get('tps', 0):.2f}</td></tr>")
            html_parts.append("</table>")
            
            # 错误类型统计
            if result.get('error_types'):
                html_parts.append("<h4>错误类型分布</h4>")
                html_parts.append("<div class='error-type'>")
                html_parts.append("<table>")
                html_parts.append("<tr><th>错误类型</th><th>次数</th></tr>")
                for error_type, count in result['error_types'].items():
                    html_parts.append(f"<tr><td>{error_type}</td><td>{count}</td></tr>")
                html_parts.append("</table>")
                html_parts.append("</div>")
            
            # 路径统计
            if result.get('path_stats'):
                html_parts.append("<h4>路径统计</h4>")
                html_parts.append("<div class='path-stats'>")
                html_parts.append("<table>")
                html_parts.append("<tr><th>路径</th><th>请求数</th><th>平均响应时间</th></tr>")
                for path, stats in result['path_stats'].items():
                    html_parts.append(f"<tr><td>{path}</td><td>{stats.get('total_requests', 0)}</td><td>{stats.get('avg_response_time', 0):.2f}ms</td></tr>")
                html_parts.append("</table>")
                html_parts.append("</div>")
            
            html_parts.append("</div>")
        
        html_parts.append("</div>")
        
        # 错误总结
        if report_data.get('error_summary'):
            html_parts.append("<div class='summary'>")
            html_parts.append("<h2>错误类型总结</h2>")
            html_parts.append("<table>")
            html_parts.append("<tr><th>错误类型</th><th>总次数</th></tr>")
            for error_type, count in report_data['error_summary'].items():
                html_parts.append(f"<tr><td>{error_type}</td><td>{count}</td></tr>")
            html_parts.append("</table>")
            html_parts.append("</div>")
        
        html_parts.append("</body>")
        html_parts.append("</html>")
        
        return '\n'.join(html_parts)
    
    def stop_test(self):
        """
        停止当前运行的测试
        """
        self.stop_event.set()
        logger.info("性能测试已停止")
    
    def run_load_test(self, concurrency, duration, warmup_time=3, **request_kwargs):
        """
        执行固定参数的负载测试
        
        Args:
            concurrency: 并发数
            duration: 测试持续时间（秒）
            warmup_time: 预热时间（秒）
            **request_kwargs: 请求参数
            
        Returns:
            测试结果字典
        """
        self.stop_event.clear()
        
        try:
            logger.info(f"开始负载测试 - 并发数: {concurrency}, 持续时间: {duration}秒, 预热时间: {warmup_time}秒")
            
            # 预热阶段
            if warmup_time > 0:
                logger.info(f"预热阶段开始，持续 {warmup_time} 秒")
                warmup_result = self._run_concurrent_tests(concurrency, warmup_time, **request_kwargs)
                logger.info(f"预热阶段结束，TPS: {warmup_result['tps']:.2f}")
            
            # 正式测试阶段
            logger.info("正式测试阶段开始")
            test_result = self._run_concurrent_tests(concurrency, duration, **request_kwargs)
            logger.info(f"正式测试阶段结束，TPS: {test_result['tps']:.2f}")
            
            # 保存结果
            self.results.append(test_result)
            
            # 生成报告
            report = {
                'test_type': 'load_test',
                'concurrency': concurrency,
                'duration': duration,
                'warmup_time': warmup_time,
                'result': test_result,
                'test_id': self.current_test_id,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return report
            
        except KeyboardInterrupt:
            logger.warning("负载测试被用户中断")
        except Exception as e:
            logger.error(f"负载测试过程中出错: {str(e)}")
        finally:
            self.stop_event.set()


# 导入RequestManager以进行包装
# 不需要导入，因为HttpClient类将直接实现相关功能


class HttpClient:
    """
    HTTP客户端工具类，作为RequestManager的高级包装器
    提供统一的HTTP请求接口，支持同步/异步请求、批量操作、多IP等高级功能
    """
    
    def __init__(self, 
                 base_url: str = None, 
                 timeout: int = 30, 
                 retry_count: int = 3, 
                 retry_backoff_factor: float = 0.3,
                 retry_enabled: bool = True,
                 retry_status_codes: Optional[List[int]] = None,
                 retry_methods: Optional[List[str]] = None,
                 proxy_pool: Optional[Dict[str, str]] = None,
                 max_workers: int = 10,
                 rate_limit: Optional[float] = None,
                 rate_limit_period: float = 1.0,
                 random_generator: RandomContentGenerator = None,
                 logger=None):
        """
        初始化HTTP客户端
        
        Args:
            base_url: 基础URL，用于拼接请求URL
            timeout: 请求超时时间（秒）
            retry_count: 请求失败重试次数
            retry_backoff_factor: 重试退避因子
            retry_enabled: 是否启用重试机制
            retry_status_codes: 需要重试的HTTP状态码列表，默认包含5xx错误和429
            retry_methods: 需要重试的HTTP方法列表
            proxy_pool: 代理池字典，格式为 {"http": "http://ip:port", "https": "https://ip:port"}
            max_workers: 并发请求的最大工作线程数
            rate_limit: 每秒最大请求数（None表示不限制）
            rate_limit_period: 速率限制的时间窗口（秒）
            random_generator: 随机内容生成器实例
        """
        self.base_url = base_url
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_backoff_factor = retry_backoff_factor
        self.random_generator = random_generator or default_random_generator
        
        # 初始化日志记录器，如果未提供则使用默认logger
        self.logger = logger or logging.getLogger(__name__)
        
        # 动态参数替换模式
        self.dynamic_param_pattern: Pattern = re.compile(r'\$\{(.+?)\}')
        
        # 初始化IP选择相关属性
        self._ip_lock = threading.Lock()
        self._current_ip_index = 0
        self.ip_list = []
        
        # 初始化认证配置存储
        self.auth_strategy = None
        self.auth_config = {}
        self.ip_auth_configs = {}
        self.path_auth_configs = {}
        self.ip_path_auth_configs = {}
        self.auth_manager = None  # 初始化auth_manager属性
        
        # 配置重试和代理设置
        self.retry_enabled = retry_enabled
        self.retry_status_forcelist = tuple(retry_status_codes) if retry_status_codes else (429, 500, 502, 503, 504)
        self.retry_methods = tuple(retry_methods) if retry_methods else ("GET", "POST", "PUT", "DELETE", "PATCH")
        self.proxy_pool = proxy_pool
        self.verify_ssl = True  # 默认验证SSL
        
        # 初始化并发控制组件
        self.concurrency_manager = ConcurrencyManager()
        self.max_workers = max_workers
        
        # 初始化速率限制器
        self.rate_limiter = None
        if rate_limit is not None:
            self.rate_limiter = RateLimiter(rate=rate_limit, period=rate_limit_period)
        
        # 初始化线程池执行器
        self.executor = None
        if max_workers > 1:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 已在文件顶部导入AuthManager和default_auth_manager
    
    def _prepare_url(self, url: str) -> str:
        """
        准备请求URL
        
        Args:
            url: 请求URL
            
        Returns:
            完整的请求URL
        """
        # 如果URL已经是完整的URL，直接返回
        if url.startswith(('http://', 'https://')):
            return url
        
        # 如果有基础URL，拼接完整URL
        if self.base_url:
            return urljoin(self.base_url, url)
        
        # 否则直接返回
        return url
    
    def set_auth_manager(self, auth_manager):
        """
        设置认证管理器
        
        Args:
            auth_manager: 认证管理器实例
        """
        self.auth_manager = auth_manager
    
    def request(self, method: str, url: str, **kwargs) -> dict:
        """
        发送HTTP请求的通用方法
        
        Args:
            method: 请求方法（GET, POST, PUT等）
            url: 请求URL
            **kwargs: 其他请求参数（headers, params, data, json等）
            
        Returns:
            请求响应字典
        """
        import requests
        
        # 准备URL
        full_url = self._prepare_url(url)
        
        # 记录请求日志
        self._log_request(method, full_url, **kwargs)
        
        # 设置超时
        kwargs.setdefault('timeout', self.timeout)
        
        # 设置代理
        if self.proxy_pool:
            kwargs.setdefault('proxies', self.proxy_pool)
        
        # 设置SSL验证
        kwargs.setdefault('verify', self.verify_ssl)
        
        # 使用auth_manager添加认证信息
        if hasattr(self, 'auth_manager') and self.auth_manager:
            request_data = {'headers': kwargs.get('headers', {})}
            updated_data = self.auth_manager.add_auth(request_data)
            if updated_data and 'headers' in updated_data:
                kwargs['headers'] = updated_data['headers']
        
        # 尝试发送请求（带重试机制）
        retry_count = 0
        last_error = None
        
        while retry_count <= self.retry_count:
            try:
                response = requests.request(method, full_url, **kwargs)
                # 检查是否需要重试
                if self.retry_enabled and method in self.retry_methods and response.status_code in self.retry_status_forcelist:
                    retry_count += 1
                    if retry_count > self.retry_count:
                        break
                    
                    # 计算重试延迟
                    import time
                    delay = self.retry_backoff_factor * (2 ** (retry_count - 1))
                    time.sleep(delay)
                    continue
                
                # 请求成功，返回响应
                return {
                    'status_code': response.status_code,
                    'text': response.text,
                    'headers': dict(response.headers),
                    'json': response.json() if 'application/json' in response.headers.get('Content-Type', '') else None
                }
            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count > self.retry_count:
                    break
                
                # 计算重试延迟
                import time
                delay = self.retry_backoff_factor * (2 ** (retry_count - 1))
                time.sleep(delay)
        
        # 所有重试都失败了，抛出最后一个错误
        raise last_error or Exception(f"Request failed after {self.retry_count} retries")
    
    def _log_request(self, method: str, url: str, **kwargs) -> None:
        """
        记录请求日志
        
        Args:
            method: 请求方法
            url: 请求URL
            **kwargs: 其他请求参数
        """
        log_data = {
            'method': method,
            'url': url,
        }
        
        # 只记录关键字段，避免日志过大
        if 'params' in kwargs and kwargs['params']:
            log_data['params'] = kwargs['params']
        
        if 'headers' in kwargs and kwargs['headers']:
            # 过滤敏感信息
            safe_headers = {}
            for k, v in kwargs['headers'].items():
                if k.lower() not in ['authorization', 'token', 'secret']:
                    safe_headers[k] = v
            if safe_headers:
                log_data['headers'] = safe_headers
        
        # 对于请求体，只记录是否存在和类型，不记录具体内容
        if 'data' in kwargs and kwargs['data']:
            log_data['has_data'] = True
            log_data['data_type'] = type(kwargs['data']).__name__
        
        if 'json_data' in kwargs and kwargs['json_data']:
            log_data['has_json'] = True
        
        if 'files' in kwargs and kwargs['files']:
            log_data['has_files'] = True
            log_data['file_count'] = len(kwargs['files'])
        
        self.logger.info(f"发送请求: {json.dumps(log_data, ensure_ascii=False)}")
    
    def _log_response(self, response: requests.Response) -> None:
        """
        记录响应日志
        
        Args:
            response: 请求响应对象
        """
        log_data = {
            'url': response.url,
            'status_code': response.status_code,
            'elapsed_ms': response.elapsed.total_seconds() * 1000
        }
        
        # 尝试解析JSON响应
        try:
            response_json = response.json()
            log_data['response_type'] = 'json'
            # 只记录响应的简要信息
            if isinstance(response_json, dict) and len(response_json) > 10:
                log_data['response_keys'] = list(response_json.keys())[:10] + ['...']
        except:
            log_data['response_type'] = 'text'
            # 只记录响应的前100个字符
            log_data['response_sample'] = response.text[:100] + ('...' if len(response.text) > 100 else '')
        
        self.logger.info(f"收到响应: {json.dumps(log_data, ensure_ascii=False)}")
    
    def prepare_file_upload(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备文件上传数据
        
        Args:
            files: 文件数据字典，支持以下格式：
                - {"field_name": file_path} - 文件路径字符串
                - {"field_name": file_object} - 文件对象
                - {"field_name": (filename, file_object, content_type, custom_headers)} - 完整文件元组
        
        Returns:
            处理后的文件字典，适合requests库使用
        """
        processed_files = {}
        
        for field_name, file_data in files.items():
            # 如果是字符串，假设是文件路径
            if isinstance(file_data, str):
                file_path = file_data
                try:
                    # 获取文件名
                    import os
                    filename = os.path.basename(file_path)
                    # 打开文件并添加到处理后的文件字典
                    processed_files[field_name] = (filename, open(file_path, 'rb'))
                    logger.info(f"准备上传文件: {file_path}")
                except Exception as e:
                    logger.error(f"无法打开文件 {file_path}: {str(e)}")
                    # 跳过这个文件
                    continue
            # 如果是元组，检查是否符合requests文件元组格式
            elif isinstance(file_data, tuple):
                # 确保元组长度正确
                if len(file_data) >= 2:
                    processed_files[field_name] = file_data
                else:
                    logger.warning(f"文件元组格式不正确: {file_data}")
                    # 跳过这个文件
                    continue
            # 如果是文件对象或其他可读取对象
            elif hasattr(file_data, 'read'):
                # 尝试获取文件名
                filename = 'unknown_file'
                if hasattr(file_data, 'name'):
                    import os
                    filename = os.path.basename(file_data.name)
                # 构造文件元组
                processed_files[field_name] = (filename, file_data)
            else:
                logger.warning(f"不支持的文件数据类型: {type(file_data)}")
                # 跳过这个文件
                continue
        
        return processed_files

    def _get_next_ip(self) -> Optional[str]:
        """
        获取下一个要使用的IP地址（轮询策略）
        
        Returns:
            IP地址，如果没有可用IP则返回None
        """
        with self._ip_lock:
            if not self.ip_list:
                return None
            
            # 使用轮询策略选择IP
            ip = self.ip_list[self._current_ip_index]
            self._current_ip_index = (self._current_ip_index + 1) % len(self.ip_list)
            return ip
    
    def _prepare_request_with_ip(self, url: str, ip: Optional[str] = None) -> str:
        """
        准备带IP的请求URL
        
        Args:
            url: 原始URL
            ip: 要使用的IP地址
            
        Returns:
            处理后的URL
        """
        if not ip:
            return url
        
        # 解析URL
        from urllib.parse import urlparse, urlunparse
        parsed_url = urlparse(url)
        
        # 替换主机名为IP地址
        netloc = parsed_url.netloc
        if ':' in netloc:
            host, port = netloc.split(':', 1)
            new_netloc = f"{ip}:{port}"
        else:
            new_netloc = ip
        
        # 重建URL
        new_url = urlunparse((
            parsed_url.scheme,
            new_netloc,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment
        ))
        
        # 添加Host头信息
        if not hasattr(self, '_host_headers'):
            self._host_headers = {}
        self._host_headers[new_url] = netloc
        
        return new_url
    
    def set_auth_config(self, auth_config: Dict[str, Any]) -> None:
        """
        设置默认认证配置
        
        Args:
            auth_config: 认证配置字典
        """
        self.auth_config = auth_config
    
    def set_auth_strategy(self, auth_strategy: str) -> None:
        """
        设置默认认证策略
        
        Args:
            auth_strategy: 认证策略名称
        """
        self.auth_strategy = auth_strategy
    
    def set_ip_auth_config(self, ip: str, auth_config: Dict[str, Any], auth_strategy: Optional[str] = None) -> None:
        """
        为特定IP设置认证配置
        
        Args:
            ip: IP地址
            auth_config: 认证配置字典
            auth_strategy: 认证策略名称（可选）
        """
        self.ip_auth_configs[ip] = {
            'config': auth_config,
            'strategy': auth_strategy
        }
    
    def set_path_auth_config(self, path_pattern: str, auth_config: Dict[str, Any], auth_strategy: Optional[str] = None) -> None:
        """
        为特定路径模式设置认证配置
        
        Args:
            path_pattern: 路径模式（支持精确匹配或前缀匹配）
            auth_config: 认证配置字典
            auth_strategy: 认证策略名称（可选）
        """
        self.path_auth_configs[path_pattern] = {
            'config': auth_config,
            'strategy': auth_strategy
        }
    
    def set_ip_path_auth_config(self, ip: str, path_pattern: str, auth_config: Dict[str, Any], auth_strategy: Optional[str] = None) -> None:
        """
        为特定IP和路径组合设置认证配置
        
        Args:
            ip: IP地址
            path_pattern: 路径模式
            auth_config: 认证配置字典
            auth_strategy: 认证策略名称（可选）
        """
        key = (ip, path_pattern)
        self.ip_path_auth_configs[key] = {
            'config': auth_config,
            'strategy': auth_strategy
        }
    
    def _get_auth_config_for_request(self, url: str, ip: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        根据URL和IP获取对应的认证配置
        
        Args:
            url: 请求URL
            ip: 使用的IP地址
            
        Returns:
            (认证配置字典, 认证策略名称) 的元组
        """
        # 解析URL获取路径
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # 1. 检查IP+路径的特定配置（最高优先级）
        if ip:
            # 尝试精确匹配IP+路径
            for (config_ip, config_path), config_info in self.ip_path_auth_configs.items():
                if config_ip == ip and path == config_path:
                    return config_info['config'], config_info['strategy']
            
            # 尝试IP+路径前缀匹配
            for (config_ip, config_path), config_info in self.ip_path_auth_configs.items():
                if config_ip == ip and path.startswith(config_path):
                    return config_info['config'], config_info['strategy']
        
        # 2. 检查路径特定配置
        # 尝试精确路径匹配
        for config_path, config_info in self.path_auth_configs.items():
            if path == config_path:
                return config_info['config'], config_info['strategy']
        
        # 尝试路径前缀匹配
        for config_path, config_info in self.path_auth_configs.items():
            if path.startswith(config_path):
                return config_info['config'], config_info['strategy']
        
        # 3. 检查IP特定配置
        if ip and ip in self.ip_auth_configs:
            config_info = self.ip_auth_configs[ip]
            return config_info['config'], config_info['strategy']
        
        # 4. 返回默认配置
        return self.auth_config.copy(), self.auth_strategy
    
    def _prepare_auth_headers(self, 
                             method: str,
                             url: str,
                             ip: Optional[str] = None,
                             headers: Optional[Dict[str, str]] = None,
                             data: Optional[Union[Dict[str, Any], str]] = None,
                             json_data: Optional[Dict[str, Any]] = None,
                             files: Optional[Dict[str, Any]] = None,
                             auth_strategy: Optional[str] = None,
                             auth_config: Optional[Dict[str, Any]] = None,
                             file_md5: Optional[str] = None) -> Dict[str, str]:
        """
        准备认证请求头
        
        Args:
            method: 请求方法
            url: 请求URL
            ip: 使用的IP地址
            headers: 原始请求头
            data: 请求数据
            json_data: JSON请求数据
            files: 文件数据
            auth_strategy: 认证策略名称
            auth_config: 认证配置
            file_md5: 文件MD5值（如果有）
            
        Returns:
            包含认证信息的请求头
        """
        # 获取URL和IP对应的认证配置
        dynamic_config, dynamic_strategy = self._get_auth_config_for_request(url, ip)
        
        # 使用指定的认证策略或动态策略或默认认证策略
        strategy = auth_strategy or dynamic_strategy or self.auth_strategy
        
        # 如果没有指定认证策略，则直接返回原始请求头
        if not strategy:
            return headers or {}
        
        # 使用指定的认证配置或动态配置或默认认证配置
        config = auth_config or dynamic_config or self.auth_config.copy()
        
        # 对于需要body内容的请求方法
        if method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # 确定要使用的body内容
            body_content = json_data if json_data is not None else data
            
            # 如果有文件上传，处理文件MD5
            file_md5_map = None
            if files:
                if not file_md5:
                    # 如果有多个文件，使用process_files_for_auth
                    if len(files) > 1:
                        try:
                            # 使用HMACAuth中的方法进行文件MD5计算
                            file_md5_map = {}
                            for key, file_obj in files.items():
                                if isinstance(file_obj, tuple) and len(file_obj) >= 2:
                                    file_md5_map[key] = HMACAuth._calculate_file_path_md5(file_obj[1])
                                elif hasattr(file_obj, 'name'):
                                    file_md5_map[key] = HMACAuth._calculate_file_path_md5(file_obj.name)
                                elif hasattr(file_obj, 'read'):
                                    file_md5_map[key] = HMACAuth._calculate_file_md5(file_obj)
                        except Exception as e:
                            logger.warning(f"无法处理多个文件的MD5: {str(e)}")
                    else:
                        # 单个文件，尝试计算MD5
                        for file_key, file_info in files.items():
                            if isinstance(file_info, tuple) and len(file_info) >= 2:
                                file_obj = file_info[1]
                                if hasattr(file_obj, 'name'):
                                    try:
                                        file_md5 = HMACAuth._calculate_file_path_md5(file_obj.name)
                                    except Exception as e:
                                        logger.warning(f"无法计算文件 {file_obj.name} 的MD5: {str(e)}")
                                elif hasattr(file_obj, 'read'):
                                    try:
                                        file_md5 = HMACAuth._calculate_file_md5(file_obj)
                                    except Exception as e:
                                        logger.warning(f"无法计算二进制文件对象的MD5: {str(e)}")
            
            # 添加必要的内容到配置中
            config['body_content'] = body_content
            config['file_md5'] = file_md5
            config['file_md5_map'] = file_md5_map
            config['files'] = files
        
        try:
            # 获取认证请求头
            auth_headers = default_auth_manager.get_auth_headers(strategy, **config)
            
            # 合并请求头
            result_headers = (headers or {}).copy()
            result_headers.update(auth_headers)
            
            # 添加Host头（如果有）
            from urllib.parse import urlparse
            if url in getattr(self, '_host_headers', {}):
                result_headers['Host'] = self._host_headers[url]
            
            return result_headers
        except Exception as e:
            logger.error(f"生成认证请求头失败: {str(e)}")
            return headers or {}
    
    def _process_dynamic_params(self, data: Any, param_funcs: Optional[Dict[str, Callable]] = None) -> Any:
        """
        处理动态参数替换
        
        Args:
            data: 需要处理的数据（字典、列表、字符串等）
            param_funcs: 自定义参数处理函数字典
            
        Returns:
            处理后的数据
        """
        if param_funcs is None:
            param_funcs = {}
        
        # 默认参数处理函数
        default_funcs = {
            'timestamp': lambda: str(int(time.time())),
            'random_str': lambda: self.random_generator.random_string(),
            'random_num': lambda: str(random.randint(1000, 9999)),
            'date': lambda: time.strftime('%Y-%m-%d'),
            'datetime': lambda: time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 合并默认函数和自定义函数
        all_funcs = {**default_funcs, **param_funcs}
        
        # 处理字符串中的动态参数
        def _replace_in_string(text: str) -> str:
            def replace_match(match):
                expr = match.group(1).strip()
                # 检查是否是函数调用形式: func() 或 func(arg1, arg2)
                func_match = re.match(r'([a-zA-Z_]\w*)\((.*)\)', expr)
                if func_match:
                    func_name, args_str = func_match.groups()
                    if func_name in all_funcs:
                        # 解析参数
                        args = [arg.strip() for arg in args_str.split(',')] if args_str.strip() else []
                        try:
                            return str(all_funcs[func_name](*args))
                        except Exception as e:
                            logger.warning(f"动态参数函数执行失败: {expr}, 错误: {str(e)}")
                            return expr
                # 检查是否是简单的变量名
                elif expr in all_funcs:
                    try:
                        return str(all_funcs[expr]())
                    except Exception as e:
                        logger.warning(f"动态参数函数执行失败: {expr}, 错误: {str(e)}")
                        return expr
                return f"${{{expr}}}"  # 保留原始格式
            
            return self.dynamic_param_pattern.sub(replace_match, text)
        
        # 递归处理数据结构
        if isinstance(data, dict):
            return {k: self._process_dynamic_params(v, param_funcs) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._process_dynamic_params(item, param_funcs) for item in data]
        elif isinstance(data, str):
            return _replace_in_string(data)
        else:
            return data
    
    def send_request(self, 
                      method: str, 
                      url: str, 
                      params: Optional[Dict[str, Any]] = None,
                      data: Optional[Union[Dict[str, Any], str]] = None,
                      json_data: Optional[Dict[str, Any]] = None,
                      headers: Optional[Dict[str, str]] = None,
                      cookies: Optional[Dict[str, str]] = None,
                      files: Optional[Dict[str, Any]] = None,
                      timeout: Optional[int] = None,
                      verify: bool = True,
                      allow_redirects: bool = True,
                      use_ip: Optional[str] = None,
                      use_proxy: bool = False,
                      auth_strategy: Optional[str] = None,
                      auth_config: Optional[Dict[str, Any]] = None,
                      file_md5: Optional[str] = None,
                      retry_enabled: Optional[bool] = None,
                      retry_count: Optional[int] = None,
                      retry_on_status_codes: Optional[List[int]] = None,
                      dynamic_params: bool = True,
                      param_funcs: Optional[Dict[str, Callable]] = None,
                      stream: bool = False,
                      **kwargs) -> requests.Response:
        """
        发送HTTP请求，支持智能重试、动态参数和流式响应
        
        Args:
            method: 请求方法（GET, POST, PUT, DELETE, PATCH等）
            url: 请求URL
            params: URL查询参数
            data: 请求体数据（表单数据）
            json_data: JSON格式的请求体数据
            headers: 请求头
            cookies: 请求cookies
            files: 文件上传数据
            timeout: 超时时间（秒），默认使用实例的timeout
            verify: 是否验证SSL证书
            allow_redirects: 是否允许重定向
            use_ip: 指定使用的IP地址（覆盖自动选择）
            use_proxy: 是否使用代理
            auth_strategy: 认证策略
            auth_config: 认证配置
            file_md5: 文件MD5值
            retry_enabled: 是否启用重试（覆盖全局设置）
            retry_count: 重试次数（覆盖全局设置）
            retry_on_status_codes: 需要重试的状态码（覆盖全局设置）
            dynamic_params: 是否启用动态参数替换
            param_funcs: 自定义动态参数处理函数
            stream: 是否启用流式响应处理
            **kwargs: 其他requests库支持的参数
            
        Returns:
            requests.Response对象
        """
        # 准备请求URL
        full_url = self._prepare_url(url)
        
        # 使用指定IP或从IP列表中获取
        ip = use_ip if use_ip else self._get_next_ip()
        if ip:
            full_url = self._prepare_request_with_ip(full_url, ip)
            logger.info(f"使用IP: {ip} 发送请求")
        
        # 使用实例的timeout如果没有指定
        if timeout is None:
            timeout = self.timeout
        
        # 处理重试配置
        current_retry_enabled = self.retry_enabled if retry_enabled is None else retry_enabled
        current_retry_count = self.retry_count if retry_count is None else retry_count
        current_retry_status_codes = self.retry_status_codes if retry_on_status_codes is None else retry_on_status_codes
        
        # 处理动态参数替换
        if dynamic_params:
            if params is not None:
                params = self._process_dynamic_params(params, param_funcs)
            if isinstance(data, dict) or isinstance(data, list):
                data = self._process_dynamic_params(data, param_funcs)
            if json_data is not None:
                json_data = self._process_dynamic_params(json_data, param_funcs)
            if headers is not None:
                headers = self._process_dynamic_params(headers, param_funcs)
            if cookies is not None:
                cookies = self._process_dynamic_params(cookies, param_funcs)
        
        # 准备请求参数
        request_kwargs = {
            'timeout': timeout,
            'verify': verify,
            'allow_redirects': allow_redirects,
            'stream': stream  # 设置流式响应
        }
        
        # 添加代理（如果启用）
        if use_proxy and self.proxy_pool:
            request_kwargs['proxies'] = self.proxy_pool
            logger.info("使用代理发送请求")
        
        # 预处理文件（如果有）
        processed_files = None
        if files:
            processed_files = self.prepare_file_upload(files)
            if self.file_upload_chunk_size > 0:
                request_kwargs['stream'] = True
        
        # 处理认证
        headers = self._prepare_auth_headers(
            method=method,
            url=full_url,
            ip=ip,
            headers=headers,
            data=data,
            json_data=json_data,
            files=processed_files,
            auth_strategy=auth_strategy,
            auth_config=auth_config,
            file_md5=file_md5
        )
        
        # 添加其他参数
        if params is not None:
            request_kwargs['params'] = params
        if data is not None:
            request_kwargs['data'] = data
        if json_data is not None:
            request_kwargs['json'] = json_data
        if headers is not None:
            request_kwargs['headers'] = headers
        if cookies is not None:
            request_kwargs['cookies'] = cookies
        if processed_files is not None:
            request_kwargs['files'] = processed_files
        
        # 添加额外的参数
        request_kwargs.update(kwargs)
        
        # 记录请求日志
        self._log_request(method, full_url, **request_kwargs)
        
        # 定义发送请求的函数，用于速率限制和并发控制
        def _send_request_inner():
            retry_count = 0
            max_retries = current_retry_count if current_retry_enabled else 0
            last_exception = None
            last_response = None
            
            while retry_count <= max_retries:
                try:
                    # 对于文件上传请求，确保每次重试前重置文件指针
                    if processed_files:
                        for key, file_info in processed_files.items():
                            if isinstance(file_info, tuple) and len(file_info) >= 2:
                                file_obj = file_info[1]
                                if hasattr(file_obj, 'seek'):
                                    file_obj.seek(0)
                    
                    start_time = time.time()
                    response = self.session.request(method=method.upper(), url=full_url, **request_kwargs)
                    
                    # 记录响应时间
                    response_time = time.time() - start_time
                    logger.info(f"请求耗时: {response_time:.3f} 秒, 状态码: {response.status_code}")
                    
                    # 检查是否需要重试（基于状态码）
                    if current_retry_enabled and response.status_code in current_retry_status_codes:
                        retry_count += 1
                        last_response = response
                        wait_time = (self.retry_backoff_factor * (2 ** (retry_count - 1))) + random.uniform(0, 1)
                        logger.warning(f"请求返回状态码 {response.status_code}, 第 {retry_count} 次重试，等待 {wait_time:.2f} 秒")
                        time.sleep(wait_time)
                        continue
                    
                    # 记录响应日志
                    self._log_response(response)
                    
                    return response
                except Exception as e:
                    # 检查是否是需要重试的异常类型
                    should_retry = False
                    for exc_type in self.retry_exceptions:
                        if isinstance(e, exc_type):
                            should_retry = True
                            break
                    
                    last_exception = e
                    
                    if current_retry_enabled and should_retry and retry_count < max_retries:
                        retry_count += 1
                        wait_time = (self.retry_backoff_factor * (2 ** (retry_count - 1))) + random.uniform(0, 1)
                        logger.warning(f"请求异常: {type(e).__name__} - {str(e)}, 第 {retry_count} 次重试，等待 {wait_time:.2f} 秒")
                        time.sleep(wait_time)
                    else:
                        error_msg = f"请求发送失败: {str(e)}"
                        logger.error(error_msg)
                        # 如果有之前的响应，返回它
                        if last_response:
                            return last_response
                        return None
        
        # 应用速率限制
        if hasattr(self, 'rate_limiter') and self.rate_limiter:
            # 使用装饰器风格的速率限制
            @run_with_rate_limit(self.rate_limiter)
            def _send_request_with_rate_limit():
                return _send_request_inner()
            
            return _send_request_with_rate_limit()
        else:
            # 直接发送请求
            return _send_request_inner()
    
    def stream_request(self, 
                      method: str, 
                      url: str, 
                      chunk_size: int = 1024, 
                      process_func: Optional[Callable] = None,
                      **kwargs) -> Generator[Any, None, None]:
        """
        发送流式请求，适用于大模型接口等流式响应场景
        
        Args:
            method: 请求方法
            url: 请求URL
            chunk_size: 每次读取的字节数
            process_func: 对每个chunk的处理函数，返回处理后的结果
            **kwargs: 传递给send_request的其他参数
            
        Yields:
            处理后的响应数据块
        """
        # 确保启用流式处理
        kwargs['stream'] = True
        
        # 发送请求
        response = self.send_request(method, url, **kwargs)
        
        if not response or not response.ok:
            logger.error(f"流式请求失败: 状态码 {response.status_code if response else 'N/A'}")
            return
        
        try:
            # 默认处理函数，尝试解析JSON
            def default_process(chunk):
                try:
                    # 尝试解码为字符串并解析JSON
                    chunk_str = chunk.decode('utf-8')
                    # 处理可能的多行JSON
                    lines = chunk_str.splitlines()
                    results = []
                    for line in lines:
                        line = line.strip()
                        # 处理SSE格式: data: {json}
                        if line.startswith('data:'):
                            line = line[5:].strip()
                        # 跳过空行
                        if not line:
                            continue
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            # 如果无法解析为完整JSON，返回原始字符串
                            return chunk_str
                except Exception:
                    # 返回原始chunk
                    return chunk
            
            # 使用提供的处理函数或默认函数
            process = process_func or default_process
            
            # 流式读取响应
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    processed_chunk = process(chunk)
                    yield processed_chunk
        except Exception as e:
            logger.error(f"处理流式响应时出错: {str(e)}")
            raise
        finally:
            # 确保关闭响应连接
            try:
                response.close()
            except:
                pass
    
    def send_batch_requests(self, 
                           method: str, 
                           urls: List[str],
                           params_list: Optional[List[Optional[Dict[str, Any]]]] = None,
                           data_list: Optional[List[Optional[Union[Dict[str, Any], str]]]] = None,
                           json_list: Optional[List[Optional[Dict[str, Any]]]] = None,
                           headers_list: Optional[List[Optional[Dict[str, str]]]] = None,
                           cookies_list: Optional[List[Optional[Dict[str, str]]]] = None,
                           files_list: Optional[List[Optional[Dict[str, Any]]]] = None,
                           timeout: Optional[int] = None,
                           verify: bool = True,
                           allow_redirects: bool = True,
                           use_ips: Optional[List[Optional[str]]] = None,
                           sequential: bool = True,
                           auth_strategy: Optional[str] = None,
                           auth_config: Optional[Dict[str, Any]] = None,
                           file_md5_list: Optional[List[Optional[str]]] = None,
                           **kwargs) -> List[Tuple[str, requests.Response]]:
        """
        批量发送HTTP请求
        
        Args:
            method: 请求方法
            urls: URL列表
            params_list: 参数列表，与URL列表一一对应
            data_list: 数据列表，与URL列表一一对应
            json_list: JSON数据列表，与URL列表一一对应
            headers_list: 请求头列表，与URL列表一一对应
            cookies_list: cookies列表，与URL列表一一对应
            files_list: 文件列表，与URL列表一一对应
            timeout: 超时时间
            verify: 是否验证SSL证书
            allow_redirects: 是否允许重定向
            use_ips: IP地址列表，与URL列表一一对应
            sequential: 是否顺序执行（False表示并行执行，需要额外线程池支持）
            **kwargs: 其他参数
            
        Returns:
            URL和响应对象的元组列表
        """
        results = []
        
        # 确保列表长度一致，缺少的部分用None填充
        list_length = len(urls)
        if params_list is None:
            params_list = [None] * list_length
        if data_list is None:
            data_list = [None] * list_length
        if json_list is None:
            json_list = [None] * list_length
        if headers_list is None:
            headers_list = [None] * list_length
        if cookies_list is None:
            cookies_list = [None] * list_length
        if files_list is None:
            files_list = [None] * list_length
        if use_ips is None:
            use_ips = [None] * list_length
        if file_md5_list is None:
            file_md5_list = [None] * list_length
        
        # 调整列表长度
        params_list = params_list[:list_length]
        data_list = data_list[:list_length]
        json_list = json_list[:list_length]
        headers_list = headers_list[:list_length]
        cookies_list = cookies_list[:list_length]
        files_list = files_list[:list_length]
        use_ips = use_ips[:list_length]
        file_md5_list = file_md5_list[:list_length]
        
        logger.info(f"开始批量发送请求，共{list_length}个请求")
        
        # 目前只实现顺序执行，并行执行需要额外的线程池支持
        for i, url in enumerate(urls):
            logger.info(f"执行第{i+1}/{list_length}个请求: {url}")
            # 预处理文件（如果有）
            processed_files = None
            if files_list[i]:
                processed_files = self.prepare_file_upload(files_list[i])
            
            response = self.send_request(
                method=method,
                url=url,
                params=params_list[i],
                data=data_list[i],
                json_data=json_list[i],
                headers=headers_list[i],
                cookies=cookies_list[i],
                files=processed_files,
                timeout=timeout,
                verify=verify,
                allow_redirects=allow_redirects,
                use_ip=use_ips[i],
                auth_strategy=auth_strategy,
                auth_config=auth_config,
                file_md5=file_md5_list[i],
                retry_on_file_error=self.retry_on_file_error,
                **kwargs
            )
            results.append((url, response))
        
        logger.info("批量请求完成")
        return results
    
    def send_multiple_paths(self, 
                           base_url: str,
                           paths: List[str],
                           method: str = 'GET',
                           params: Optional[Dict[str, Any]] = None,
                           data: Optional[Union[Dict[str, Any], str]] = None,
                           json_data: Optional[Dict[str, Any]] = None,
                           headers: Optional[Dict[str, str]] = None,
                           cookies: Optional[Dict[str, str]] = None,
                           files: Optional[Dict[str, Any]] = None,
                           timeout: Optional[int] = None,
                           verify: bool = True,
                           allow_redirects: bool = True,
                           use_ips: Optional[List[Optional[str]]] = None,
                           auth_strategy: Optional[str] = None,
                           auth_config: Optional[Dict[str, Any]] = None,
                           **kwargs) -> List[Tuple[str, requests.Response]]:
        """
        发送多个路径的请求（基于同一个基础URL）
        
        Args:
            base_url: 基础URL
            paths: 路径列表
            method: 请求方法
            params: URL查询参数（应用于所有请求）
            data: 请求体数据（应用于所有请求）
            json_data: JSON格式的请求体数据（应用于所有请求）
            headers: 请求头（应用于所有请求）
            cookies: 请求cookies（应用于所有请求）
            files: 文件上传数据（应用于所有请求）
            timeout: 超时时间
            verify: 是否验证SSL证书
            allow_redirects: 是否允许重定向
            use_ips: IP地址列表，与路径列表一一对应
            **kwargs: 其他参数
            
        Returns:
            完整URL和响应对象的元组列表
        """
        # 构建完整URL列表
        urls = []
        for path in paths:
            # 处理路径，确保格式正确
            if not path.startswith('/'):
                path = '/' + path
            if base_url.endswith('/'):
                full_url = base_url + path[1:]
            else:
                full_url = base_url + path
            urls.append(full_url)
        
        # 使用批量请求方法
        return self.send_batch_requests(
            method=method,
            urls=urls,
            params_list=[params] * len(urls),
            data_list=[data] * len(urls),
            json_list=[json_data] * len(urls),
            headers_list=[headers] * len(urls),
            cookies_list=[cookies] * len(urls),
            files_list=[files] * len(urls),
            timeout=timeout,
            verify=verify,
            allow_redirects=allow_redirects,
            use_ips=use_ips,
            auth_strategy=auth_strategy,
            auth_config=auth_config,
            retry_on_file_error=self.retry_on_file_error,
            **kwargs
        )
    
    def set_ip_list(self, ip_list: List[str]) -> None:
        """
        设置IP地址列表
        
        Args:
            ip_list: IP地址列表
        """
        self.ip_list = ip_list
    
    def set_proxy_pool(self, proxy_pool: Dict[str, str]) -> None:
        """
        设置代理池
        
        Args:
            proxy_pool: 代理池字典，格式为 {"http": "http://ip:port", "https": "https://ip:port"}
        """
        self.proxy_pool = proxy_pool
    
    def get(self, 
            url: str, 
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            cookies: Optional[Dict[str, str]] = None,
            **kwargs) -> Dict[str, Any]:
        """
        发送GET请求
        
        Args:
            url: 请求URL
            params: URL查询参数
            headers: 请求头
            cookies: cookies
            **kwargs: 其他参数
            
        Returns:
            包含响应信息的字典
        """
        full_url = self._prepare_url(url)
        
        # 处理动态参数
        if kwargs.pop('dynamic_params', False):
            if params:
                params = self._process_dynamic_params(params, kwargs.get('param_funcs'))
            if headers:
                headers = self._process_dynamic_params(headers, kwargs.get('param_funcs'))
            if cookies:
                cookies = self._process_dynamic_params(cookies, kwargs.get('param_funcs'))
        
        # 处理认证
        headers = self._prepare_auth_headers(
            method='GET',
            url=full_url,
            headers=headers,
            **kwargs
        )
        
        # 准备请求参数
        request_kwargs = {}
        if params:
            request_kwargs['params'] = params
        if headers:
            request_kwargs['headers'] = headers
        if cookies:
            request_kwargs['cookies'] = cookies
        request_kwargs.update(kwargs)
        
        # 使用request方法发送请求
        return self.request('GET', full_url, **request_kwargs)
    
    def post(self, 
             url: str, 
             data: Optional[Union[Dict[str, Any], str]] = None,
             json_data: Optional[Dict[str, Any]] = None,
             params: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None,
             cookies: Optional[Dict[str, str]] = None,
             files: Optional[Dict[str, Any]] = None,
             **kwargs) -> Dict[str, Any]:
        """
        发送POST请求
        
        Args:
            url: 请求URL
            data: 请求体数据
            json_data: JSON格式的请求体数据
            params: URL查询参数
            headers: 请求头
            cookies: cookies
            files: 文件上传数据
            **kwargs: 其他参数
            
        Returns:
            包含响应信息的字典
        """
        full_url = self._prepare_url(url)
        
        # 处理动态参数
        if kwargs.pop('dynamic_params', False):
            if params:
                params = self._process_dynamic_params(params, kwargs.get('param_funcs'))
            if data and isinstance(data, (dict, list)):
                data = self._process_dynamic_params(data, kwargs.get('param_funcs'))
            if json_data:
                json_data = self._process_dynamic_params(json_data, kwargs.get('param_funcs'))
            if headers:
                headers = self._process_dynamic_params(headers, kwargs.get('param_funcs'))
            if cookies:
                cookies = self._process_dynamic_params(cookies, kwargs.get('param_funcs'))
        
        # 处理文件
        processed_files = None
        if files:
            processed_files = self.prepare_file_upload(files)
        
        # 处理认证
        headers = self._prepare_auth_headers(
            method='POST',
            url=full_url,
            headers=headers,
            data=data,
            json_data=json_data,
            files=processed_files,
            **kwargs
        )
        
        # 准备请求参数
        request_kwargs = {}
        if data:
            request_kwargs['data'] = data
        if json_data:
            request_kwargs['json'] = json_data
        if params:
            request_kwargs['params'] = params
        if headers:
            request_kwargs['headers'] = headers
        if cookies:
            request_kwargs['cookies'] = cookies
        if processed_files:
            request_kwargs['files'] = processed_files
        request_kwargs.update(kwargs)
        
        # 使用request方法发送请求
        return self.request('POST', full_url, **request_kwargs)
    
    def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送PUT请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            包含响应信息的字典
        """
        full_url = self._prepare_url(url)
        return self.request('PUT', full_url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送DELETE请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            包含响应信息的字典
        """
        full_url = self._prepare_url(url)
        return self.request('DELETE', full_url, **kwargs)
    
    def patch(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送PATCH请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            包含响应信息的字典
        """
        full_url = self._prepare_url(url)
        return self.request('PATCH', full_url, **kwargs)
    
    def get_async(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送异步GET请求（当前版本不支持真正的异步，使用同步方式模拟）
        
        Args:
            url: 请求URL
            **kwargs: 其他参数
            
        Returns:
            包含响应信息的字典
        """
        logger.warning("当前版本不支持真正的异步请求，使用同步方式模拟")
        return self.get(url, **kwargs)
    
    def post_async(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送异步POST请求（当前版本不支持真正的异步，使用同步方式模拟）
        
        Args:
            url: 请求URL
            **kwargs: 其他参数
            
        Returns:
            包含响应信息的字典
        """
        logger.warning("当前版本不支持真正的异步请求，使用同步方式模拟")
        return self.post(url, **kwargs)
    
    def close(self) -> None:
        """
        关闭会话和资源
        """
        if hasattr(self, 'request_manager'):
            self.request_manager.close()
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=True)
    
    def __del__(self):
        """
        析构函数，确保会话和资源关闭
        """
        self.close()
    
    def set_ip_list(self, ip_list: List[str]) -> None:
        """
        设置IP地址列表
        
        Args:
            ip_list: IP地址列表
        """
        self.ip_list = ip_list
        
    def set_proxy_pool(self, proxy_pool: Dict[str, str]) -> None:
        """
        设置代理池
        
        Args:
            proxy_pool: 代理池字典
        """
        self.request_manager.set_proxy(proxy_pool)
    
    def set_default_headers(self, headers: Dict[str, str]) -> None:
        """
        设置默认请求头
        
        Args:
            headers: 默认请求头字典
        """
        self.request_manager.set_default_headers(headers)
    
    def get_performance_tester(self, path=None, base_url=None):
        """
        获取性能测试器实例
        
        Args:
            path: 测试路径（可选，默认为None，使用根路径）
            base_url: 测试基础URL（可选，默认使用客户端的base_url）
            
        Returns:
            PerformanceTester实例
        """
        return PerformanceTester(self, base_url=base_url, path=path or "")
    
    def run_performance_test(self, path, test_type='concurrency', **kwargs):
        """
        运行性能测试
        
        Args:
            path: 测试路径
            test_type: 测试类型，'concurrency'表示并发测试，'tps'表示TPS测试
            **kwargs: 测试参数
            
        Returns:
            测试报告
        """
        tester = self.get_performance_tester(path=path)
        
        if test_type.lower() == 'concurrency':
            report = tester.find_max_concurrency(**kwargs)
        elif test_type.lower() == 'tps':
            report = tester.find_max_tps(**kwargs)
        else:
            raise ValueError(f"不支持的测试类型: {test_type}")
        
        return report


# 为了向后兼容，保留RequestSend类
class RequestSend(HttpClient):
    """
    请求发送类（向后兼容）
    """
    
    def api_run(self, url, method, data=None, headers=None, cookies=None):
        """向后兼容原有的api_run方法"""
        # 打印日志
        logger.info("请求的url为{},类型为{}".format(url, type(url)))
        # 打印日志
        logger.info("请求的method为{},类型为{}".format(method, type(method)))
        # 打印日志
        logger.info("请求的data为{},类型为{}".format(data, type(data)))
        # 打印日志
        logger.info("请求的headers为{},类型为{}".format(headers, type(headers)))
        # 打印日志
        logger.info("请求的cookies为{},类型为{}".format(cookies, type(cookies)))
        
        # 根据不同方法和头信息调用对应的请求方法
        if method.lower() == "get":
            res = self.get(url, params=data, headers=headers, cookies=cookies)
        elif method.lower() == "post":
            if headers and headers.get("Content-Type") == "application/json":
                res = self.post(url, json_data=data, headers=headers, cookies=cookies)
            else:
                res = self.post(url, data=data, headers=headers, cookies=cookies)
        else:
            res = self.send_request(method, url, data=data, headers=headers, cookies=cookies)
        
        if res is None:
            return {'code': 0, 'headers': {}, 'body': {'hi': '请求失败'}, 'cookies': {}}
        
        # 获取响应信息
        code = res.status_code
        cookies_dict = res.cookies.get_dict()
        headers_dict = dict(res.headers)
        print("头信息是", headers_dict)
        
        # 构造返回结果
        dict1 = {}
        try:
            body = res.json()
        except:
            body = {"hi": "无数据"}
        
        dict1['code'] = code
        dict1['headers'] = headers_dict
        dict1['body'] = body
        dict1['cookies'] = cookies_dict
        
        return dict1
    
    def send(self, url, method, **kwargs):
        """向后兼容原有的send方法"""
        return self.api_run(url=url, method=method, **kwargs)


# 保持向后兼容的RequestsUtil类别名
RequestsUtil = HttpClient

# 测试代码
if __name__ == '__main__':
    # 测试多IP和多路径功能
    client = HttpClient(
        base_url="http://httpbin.org",
        ip_list=["127.0.0.1", "192.168.1.1"]  # 示例IP列表
    )
    
    # 测试单请求
    response = client.get("/get")
    print(f"单请求状态码: {response.status_code if response else 'None'}")
    
    # 测试多路径请求
    paths = ["/get", "/headers", "/status/200"]
    results = client.send_multiple_paths(
        base_url="http://httpbin.org",
        paths=paths,
        method="GET"
    )
    
    print("\n多路径请求结果:")
    for url, resp in results:
        print(f"URL: {url}, 状态码: {resp.status_code if resp else 'None'}")
    
    # 测试批量请求
    urls = ["http://httpbin.org/get", "http://httpbin.org/post"]
    batch_results = client.send_batch_requests(
        method="GET",
        urls=urls
    )
    
    print("\n批量请求结果:")
    for url, resp in batch_results:
        print(f"URL: {url}, 状态码: {resp.status_code if resp else 'None'}")
    
    # 测试文件上传功能（模拟）
    print("\n文件上传功能测试:")
    try:
        # 创建一个临时文件用于测试
        temp_file_path = "temp_test.txt"
        with open(temp_file_path, "w") as f:
            f.write("This is a test file for upload")
        
        # 测试单文件上传
        print("\n测试单文件上传:")
        # 注意：这里只是演示API调用，实际上httpbin.org的/post接口会接收文件但不会真正保存
        upload_response = client.post(
            "/post",
            files={"test_file": open(temp_file_path, "rb")}
        )
        print(f"上传状态码: {upload_response.status_code if upload_response else 'None'}")
        
        # 测试便捷上传方法
        print("\n测试便捷上传方法:")
        # 先关闭之前打开的文件
        if 'test_file' in locals():
            test_file.close()
        
        # 使用便捷方法上传
        # 注意：这里只是演示API调用格式
        print("upload_file方法API:")
        print("client.upload_file('/post', temp_file_path, file_param='file')")
        
        print("\nupload_multiple_files方法API:")
        print("client.upload_multiple_files('/post', {'file1': temp_file_path, 'file2': temp_file_path})")
        
    except Exception as e:
        print(f"文件上传测试出错: {str(e)}")
    finally:
        # 清理临时文件
        import os
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass