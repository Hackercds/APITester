#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式接口测试增强工具模块

提供对流式接口（特别是大模型API）的高级测试功能，包括：
- 流式响应的实时验证和断言
- 性能监控和指标收集
- 流式数据的保存和重放
- 多种格式的流式数据处理
"""

import asyncio
import json
import logging
import time
from typing import (
    Optional, Dict, Any, Callable, List, Generator, AsyncGenerator,
    Tuple, Union
)

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StreamValidator:
    """
    流式响应验证器
    用于对流式返回的数据进行实时验证和断言
    """
    
    def __init__(self):
        """
        初始化流式响应验证器
        """
        self.assertions = []
        self.results = []
    
    def add_assertion(
        self,
        assertion_name: str,
        assertion_type: str,
        expected_value: Any,
        extract_func: Optional[Callable] = None
    ) -> None:
        """
        添加流式断言
        
        Args:
            assertion_name: 断言名称
            assertion_type: 断言类型，支持 'contains', 'equals', 'starts_with', 'ends_with', 'regex', 'length_gt', 'length_lt'
            expected_value: 期望的值
            extract_func: 从数据块中提取要验证的值的函数，如果为None则直接使用content字段
        """
        self.assertions.append({
            'name': assertion_name,
            'type': assertion_type,
            'expected': expected_value,
            'extract_func': extract_func or (lambda x: x.get('content', ''))
        })
    
    def validate_chunk(self, chunk: Dict[str, Any], full_content: str = "") -> List[Dict[str, Any]]:
        """
        验证单个数据块
        
        Args:
            chunk: 当前数据块
            full_content: 到目前为止的完整内容
            
        Returns:
            断言结果列表
        """
        chunk_results = []
        
        for assertion in self.assertions:
            try:
                # 提取要验证的值
                value = assertion['extract_func'](chunk)
                
                # 执行断言
                passed = False
                message = ""
                
                if assertion['type'] == 'contains':
                    passed = assertion['expected'] in str(value)
                    message = f"期望包含 '{assertion['expected']}'，实际值为 '{str(value)}'"
                    
                elif assertion['type'] == 'equals':
                    passed = value == assertion['expected']
                    message = f"期望等于 '{assertion['expected']}'，实际值为 '{str(value)}'"
                    
                elif assertion['type'] == 'starts_with':
                    passed = str(value).startswith(assertion['expected'])
                    message = f"期望以 '{assertion['expected']}' 开头，实际值为 '{str(value)}'"
                    
                elif assertion['type'] == 'ends_with':
                    passed = str(value).endswith(assertion['expected'])
                    message = f"期望以 '{assertion['expected']}' 结尾，实际值为 '{str(value)}'"
                    
                elif assertion['type'] == 'regex':
                    import re
                    passed = bool(re.search(assertion['expected'], str(value)))
                    message = f"期望匹配正则表达式 '{assertion['expected']}'，实际值为 '{str(value)}'"
                    
                elif assertion['type'] == 'length_gt':
                    passed = len(str(value)) > assertion['expected']
                    message = f"期望长度大于 {assertion['expected']}，实际长度为 {len(str(value))}"
                    
                elif assertion['type'] == 'length_lt':
                    passed = len(str(value)) < assertion['expected']
                    message = f"期望长度小于 {assertion['expected']}，实际长度为 {len(str(value))}"
                
                # 添加结果
                result = {
                    'name': assertion['name'],
                    'type': assertion['type'],
                    'expected': assertion['expected'],
                    'actual': value,
                    'passed': passed,
                    'message': message,
                    'chunk_index': len(self.results)
                }
                
                chunk_results.append(result)
                self.results.append(result)
                
            except Exception as e:
                # 断言执行出错
                error_result = {
                    'name': assertion['name'],
                    'type': assertion['type'],
                    'expected': assertion['expected'],
                    'actual': None,
                    'passed': False,
                    'message': f"断言执行错误: {str(e)}",
                    'chunk_index': len(self.results)
                }
                chunk_results.append(error_result)
                self.results.append(error_result)
        
        return chunk_results
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取所有断言的摘要
        
        Returns:
            断言摘要信息
        """
        passed_count = sum(1 for r in self.results if r['passed'])
        total_count = len(self.results)
        
        return {
            'total_assertions': total_count,
            'passed_assertions': passed_count,
            'failed_assertions': total_count - passed_count,
            'pass_rate': passed_count / total_count if total_count > 0 else 1.0,
            'all_passed': passed_count == total_count
        }
    
    def reset(self) -> None:
        """
        重置验证器状态
        """
        self.assertions = []
        self.results = []


class StreamMetricsCollector:
    """
    流式响应性能指标收集器
    用于收集流式接口的性能数据，如响应时间、吞吐量等
    """
    
    def __init__(self):
        """
        初始化指标收集器
        """
        self.start_time = None
        self.end_time = None
        self.chunks = []
        self.total_bytes = 0
        self.first_chunk_time = None
        self.last_chunk_time = None
    
    def start(self) -> None:
        """
        开始收集指标
        """
        self.start_time = time.time()
        self.chunks = []
        self.total_bytes = 0
        self.first_chunk_time = None
        self.last_chunk_time = None
    
    def record_chunk(self, chunk: Dict[str, Any], raw_size: int = 0) -> None:
        """
        记录一个数据块
        
        Args:
            chunk: 数据块
            raw_size: 原始数据块大小（字节）
        """
        current_time = time.time()
        
        # 记录第一个块的时间
        if self.first_chunk_time is None:
            self.first_chunk_time = current_time
        
        # 更新最后一个块的时间
        self.last_chunk_time = current_time
        
        # 记录块信息
        chunk_info = {
            'timestamp': current_time,
            'content_length': len(chunk.get('content', '')),
            'raw_size': raw_size,
            'index': len(self.chunks)
        }
        
        self.chunks.append(chunk_info)
        self.total_bytes += raw_size
    
    def stop(self) -> None:
        """
        停止收集指标
        """
        self.end_time = time.time()
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取收集的指标
        
        Returns:
            性能指标字典
        """
        # 基础时间计算
        if self.start_time is None:
            return {"error": "指标收集未开始"}
        
        total_time = (self.end_time or time.time()) - self.start_time
        
        # 首次响应时间（TTFB - Time To First Byte）
        ttfb = None
        if self.first_chunk_time:
            ttfb = self.first_chunk_time - self.start_time
        
        # 块间隔统计
        chunk_intervals = []
        if len(self.chunks) > 1:
            for i in range(1, len(self.chunks)):
                interval = self.chunks[i]['timestamp'] - self.chunks[i-1]['timestamp']
                chunk_intervals.append(interval)
        
        avg_chunk_interval = sum(chunk_intervals) / len(chunk_intervals) if chunk_intervals else 0
        
        # 吞吐量计算
        throughput_bytes_per_second = self.total_bytes / total_time if total_time > 0 else 0
        throughput_chunks_per_second = len(self.chunks) / total_time if total_time > 0 else 0
        
        # 内容增长速度（每秒字符数）
        total_content_length = sum(chunk['content_length'] for chunk in self.chunks)
        content_speed = total_content_length / total_time if total_time > 0 else 0
        
        return {
            'total_time': total_time,
            'total_chunks': len(self.chunks),
            'total_bytes': self.total_bytes,
            'total_content_length': total_content_length,
            'ttfb': ttfb,
            'avg_chunk_interval': avg_chunk_interval,
            'throughput_bytes_per_second': throughput_bytes_per_second,
            'throughput_chunks_per_second': throughput_chunks_per_second,
            'content_generation_speed': content_speed,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'first_chunk_time': self.first_chunk_time,
            'last_chunk_time': self.last_chunk_time
        }
    
    def reset(self) -> None:
        """
        重置指标收集器
        """
        self.__init__()


class StreamRecorder:
    """
    流式响应记录器
    用于记录流式响应以便后续分析或重放
    """
    
    def __init__(self):
        """
        初始化记录器
        """
        self.records = []
        self.start_time = None
    
    def start(self) -> None:
        """
        开始记录
        """
        self.start_time = time.time()
        self.records = []
    
    def record(self, chunk: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        记录一个数据块
        
        Args:
            chunk: 数据块
            metadata: 附加的元数据
        """
        record = {
            'timestamp': time.time() - (self.start_time or time.time()),
            'chunk': chunk.copy(),
            'metadata': metadata or {}
        }
        self.records.append(record)
    
    def save_to_file(self, file_path: str) -> bool:
        """
        保存记录到文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否保存成功
        """
        try:
            data = {
                'start_time': self.start_time,
                'end_time': time.time(),
                'total_records': len(self.records),
                'records': self.records
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"流式记录已保存到 {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存流式记录失败: {str(e)}")
            return False
    
    def load_from_file(self, file_path: str) -> bool:
        """
        从文件加载记录
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否加载成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.start_time = data.get('start_time')
            self.records = data.get('records', [])
            
            logger.info(f"从 {file_path} 加载了 {len(self.records)} 条流式记录")
            return True
            
        except Exception as e:
            logger.error(f"加载流式记录失败: {str(e)}")
            return False
    
    def get_replay_generator(self) -> Generator[Dict[str, Any], None, None]:
        """
        获取用于重放的生成器
        
        Yields:
            重放的数据块
        """
        for record in self.records:
            yield record['chunk']
    
    async def get_async_replay_generator(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        获取异步重放生成器
        
        Yields:
            重放的数据块
        """
        previous_time = 0
        for record in self.records:
            # 等待与原始时间间隔相同的时间
            if previous_time > 0:
                await asyncio.sleep(record['timestamp'] - previous_time)
            
            previous_time = record['timestamp']
            yield record['chunk']
    
    def reset(self) -> None:
        """
        重置记录器
        """
        self.__init__()


class StreamProcessorPipeline:
    """
    流式数据处理管道
    用于构建多个处理器的链式调用，简化流式数据的复杂处理流程
    """
    
    def __init__(self):
        """
        初始化处理管道
        """
        self.processors = []
    
    def add_processor(self, processor: Callable) -> 'StreamProcessorPipeline':
        """
        添加处理器到管道
        
        Args:
            processor: 处理函数，接收数据块返回处理后的数据块
            
        Returns:
            处理管道实例，支持链式调用
        """
        if not callable(processor):
            raise TypeError("处理器必须是可调用对象")
        
        self.processors.append(processor)
        return self
    
    def process_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个数据块
        
        Args:
            chunk: 输入数据块
            
        Returns:
            处理后的数据块
        """
        processed_chunk = chunk.copy()
        
        for processor in self.processors:
            try:
                processed_chunk = processor(processed_chunk)
                if processed_chunk is None:
                    processed_chunk = chunk.copy()
            except Exception as e:
                logger.error(f"处理器 {processor.__name__ if hasattr(processor, '__name__') else str(processor)} 执行出错: {str(e)}")
        
        return processed_chunk
    
    async def process_chunk_async(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步处理单个数据块
        
        Args:
            chunk: 输入数据块
            
        Returns:
            处理后的数据块
        """
        processed_chunk = chunk.copy()
        
        for processor in self.processors:
            try:
                # 支持异步处理器
                if asyncio.iscoroutinefunction(processor):
                    result = await processor(processed_chunk)
                else:
                    result = processor(processed_chunk)
                    
                if result is not None:
                    processed_chunk = result
            except Exception as e:
                logger.error(f"处理器 {processor.__name__ if hasattr(processor, '__name__') else str(processor)} 执行出错: {str(e)}")
        
        return processed_chunk
    
    def reset(self) -> None:
        """
        重置处理管道
        """
        self.processors = []


class AdvancedStreamTester:
    """
    高级流式接口测试器
    集成了验证、指标收集和记录功能，提供一站式流式接口测试体验
    """
    
    def __init__(self):
        """
        初始化高级流式测试器
        """
        self.validator = StreamValidator()
        self.metrics_collector = StreamMetricsCollector()
        self.recorder = StreamRecorder()
        self.processor_pipeline = StreamProcessorPipeline()
        
        # 处理状态
        self.full_content = ""
        self.is_started = False
        self.start_time = None
    
    def add_assertion(
        self,
        assertion_name: str,
        assertion_type: str,
        expected_value: Any,
        extract_func: Optional[Callable] = None
    ) -> 'AdvancedStreamTester':
        """
        添加流式断言
        
        Args:
            assertion_name: 断言名称
            assertion_type: 断言类型
            expected_value: 期望的值
            extract_func: 提取函数
            
        Returns:
            测试器实例，支持链式调用
        """
        self.validator.add_assertion(assertion_name, assertion_type, expected_value, extract_func)
        return self
    
    def add_processor(self, processor: Callable) -> 'AdvancedStreamTester':
        """
        添加数据处理器
        
        Args:
            processor: 处理函数
            
        Returns:
            测试器实例，支持链式调用
        """
        self.processor_pipeline.add_processor(processor)
        return self
    
    def start(self) -> 'AdvancedStreamTester':
        """
        开始测试
        
        Returns:
            测试器实例，支持链式调用
        """
        if not self.is_started:
            self.metrics_collector.start()
            self.recorder.start()
            self.full_content = ""
            self.start_time = time.time()
            self.is_started = True
        
        return self
    
    def process_chunk(self, chunk: Dict[str, Any], raw_size: int = 0) -> Dict[str, Any]:
        """
        处理一个数据块
        
        Args:
            chunk: 数据块
            raw_size: 原始数据大小
            
        Returns:
            处理后的数据块
        """
        # 确保已开始测试
        if not self.is_started:
            self.start()
        
        # 更新完整内容
        if 'content' in chunk:
            self.full_content += chunk['content']
            chunk['full_content'] = self.full_content
        
        # 使用处理管道处理数据
        processed_chunk = self.processor_pipeline.process_chunk(chunk)
        
        # 验证数据
        assertion_results = self.validator.validate_chunk(processed_chunk, self.full_content)
        processed_chunk['assertion_results'] = assertion_results
        
        # 收集指标
        self.metrics_collector.record_chunk(processed_chunk, raw_size)
        
        # 记录数据
        self.recorder.record(processed_chunk, {
            'assertion_results_count': len(assertion_results),
            'assertion_passed_count': sum(1 for r in assertion_results if r['passed'])
        })
        
        return processed_chunk
    
    async def process_chunk_async(self, chunk: Dict[str, Any], raw_size: int = 0) -> Dict[str, Any]:
        """
        异步处理一个数据块
        
        Args:
            chunk: 数据块
            raw_size: 原始数据大小
            
        Returns:
            处理后的数据块
        """
        # 确保已开始测试
        if not self.is_started:
            self.start()
        
        # 更新完整内容
        if 'content' in chunk:
            self.full_content += chunk['content']
            chunk['full_content'] = self.full_content
        
        # 使用处理管道处理数据
        processed_chunk = await self.processor_pipeline.process_chunk_async(chunk)
        
        # 验证数据
        assertion_results = self.validator.validate_chunk(processed_chunk, self.full_content)
        processed_chunk['assertion_results'] = assertion_results
        
        # 收集指标
        self.metrics_collector.record_chunk(processed_chunk, raw_size)
        
        # 记录数据
        self.recorder.record(processed_chunk, {
            'assertion_results_count': len(assertion_results),
            'assertion_passed_count': sum(1 for r in assertion_results if r['passed'])
        })
        
        return processed_chunk
    
    def stop(self) -> Dict[str, Any]:
        """
        停止测试并返回结果
        
        Returns:
            测试结果摘要
        """
        if self.is_started:
            self.metrics_collector.stop()
            self.is_started = False
        
        # 生成测试结果摘要
        return {
            'assertion_summary': self.validator.get_summary(),
            'performance_metrics': self.metrics_collector.get_metrics(),
            'total_chunks_processed': len(self.recorder.records),
            'full_content_length': len(self.full_content),
            'execution_time': time.time() - (self.start_time or time.time()),
            'all_assertions_passed': self.validator.get_summary()['all_passed']
        }
    
    def save_recording(self, file_path: str) -> bool:
        """
        保存测试记录
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否保存成功
        """
        return self.recorder.save_to_file(file_path)
    
    def reset(self) -> None:
        """
        重置测试器状态
        """
        self.validator.reset()
        self.metrics_collector.reset()
        self.recorder.reset()
        self.processor_pipeline.reset()
        self.full_content = ""
        self.is_started = False
        self.start_time = None


# 预定义的实用处理器函数
def create_json_extractor(field_path: str) -> Callable:
    """
    创建一个JSON字段提取器
    
    Args:
        field_path: 字段路径，如 "data.result.items[0].name"
        
    Returns:
        提取函数
    """
    def extractor(chunk: Dict[str, Any]) -> Any:
        value = chunk
        parts = field_path.split('.')
        
        for part in parts:
            # 处理数组索引
            if '[' in part and ']' in part:
                array_name, index = part.split('[')
                index = int(index.replace(']', ''))
                if array_name in value and isinstance(value[array_name], list) and 0 <= index < len(value[array_name]):
                    value = value[array_name][index]
                else:
                    return None
            else:
                # 处理普通字段
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
        
        return value
    
    return extractor


def create_content_filter(min_length: int = 0, max_length: int = float('inf')) -> Callable:
    """
    创建内容过滤器，只保留指定长度范围内的内容
    
    Args:
        min_length: 最小长度
        max_length: 最大长度
        
    Returns:
        过滤函数
    """
    def filter_func(chunk: Dict[str, Any]) -> Dict[str, Any]:
        if 'content' in chunk:
            content_length = len(chunk['content'])
            if min_length <= content_length <= max_length:
                return chunk
            else:
                # 创建新块，移除或截断内容
                filtered_chunk = chunk.copy()
                if content_length > max_length:
                    filtered_chunk['content'] = chunk['content'][:max_length]
                    filtered_chunk['truncated'] = True
                else:
                    filtered_chunk['content'] = ''
                return filtered_chunk
        return chunk
    
    return filter_func


if __name__ == "__main__":
    # 演示示例
    print("=== 流式接口测试增强工具演示 ===")
    
    # 创建测试器实例
    tester = AdvancedStreamTester()
    
    # 添加断言
    tester.add_assertion(
        "内容包含关键词",
        "contains",
        "测试"
    ).add_assertion(
        "内容长度",
        "length_gt",
        10
    )
    
    # 添加处理器
    def add_timestamp(chunk):
        chunk['processed_at'] = time.time()
        return chunk
    
    tester.add_processor(add_timestamp)
    
    # 模拟处理流式数据
    tester.start()
    
    mock_chunks = [
        {"content": "这是第一", "id": 1},
        {"content": "个测试数据", "id": 2},
        {"content": "块，用于演示", "id": 3},
        {"content": "流式接口测试", "id": 4},
    ]
    
    print("处理模拟的流式数据块:")
    for chunk in mock_chunks:
        result = tester.process_chunk(chunk, len(str(chunk)))
        print(f"  处理后: {result}")
    
    # 停止测试并获取结果
    results = tester.stop()
    print("\n测试结果摘要:")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    
    # 保存记录
    tester.save_recording("stream_test_recording.json")
    print("\n演示完成！")