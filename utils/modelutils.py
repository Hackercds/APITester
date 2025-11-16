#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大模型接口支持模块
提供大模型API的封装、流式响应处理、响应解析等功能
"""

import json
import logging
import time
from typing import Optional, Dict, Any, Union, Callable, List, Generator, AsyncGenerator
import re
import asyncio
from .requestsutil import HttpClient as RequestManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StreamingResponseHandler:
    """流式响应处理器基类"""
    
    def handle_chunk(self, chunk: str) -> str:
        """处理单个数据块"""
        return chunk
    
    def finalize(self) -> str:
        """最终处理，返回结果"""
        return ""


class ModelResponseParser:
    """
    大模型响应解析器
    处理不同格式的大模型API响应
    """
    
    @staticmethod
    def parse_openai_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析OpenAI兼容格式的响应
        
        Args:
            response: 原始响应数据
            
        Returns:
            解析后的响应数据
        """
        parsed = {
            'success': response.get('status_code') == 200 and not response.get('error'),
            'raw': response
        }
        
        if not parsed['success']:
            parsed['error'] = response.get('error', {}).get('message', str(response.get('error')))
            parsed['error_type'] = response.get('error', {}).get('type', 'unknown')
            return parsed
        
        # 处理响应内容
        json_data = response.get('json')
        if json_data:
            parsed['model'] = json_data.get('model')
            parsed['created'] = json_data.get('created')
            parsed['id'] = json_data.get('id')
            
            # 处理choices
            choices = json_data.get('choices', [])
            parsed['choices'] = choices
            
            # 提取文本响应
            if choices:
                if 'message' in choices[0]:
                    # 聊天完成格式
                    parsed['content'] = choices[0]['message'].get('content', '')
                    parsed['role'] = choices[0]['message'].get('role', 'assistant')
                elif 'text' in choices[0]:
                    # 补全格式
                    parsed['content'] = choices[0].get('text', '')
                
                # 检查是否为流式结束
                parsed['finish_reason'] = choices[0].get('finish_reason')
                parsed['is_finished'] = parsed['finish_reason'] is not None
            
            # 处理使用统计
            usage = json_data.get('usage', {})
            parsed['usage'] = {
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            }
        
        return parsed
    
    @staticmethod
    def parse_streaming_chunk(chunk: Union[str, bytes, Dict[str, Any]], 
                           format_type: str = 'openai') -> Dict[str, Any]:
        """
        解析流式响应数据块
        
        Args:
            chunk: 数据块
            format_type: 格式类型 (openai, azure, custom)
            
        Returns:
            解析后的数据块信息
        """
        parsed_chunk = {
            'raw': chunk,
            'is_finished': False,
            'content': '',
            'delta': '',
            'finish_reason': None
        }
        
        try:
            # 处理不同类型的输入
            if isinstance(chunk, bytes):
                chunk = chunk.decode('utf-8')
            
            if isinstance(chunk, str):
                # 处理可能的SSE格式
                lines = chunk.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            parsed_chunk['is_finished'] = True
                            parsed_chunk['finish_reason'] = 'done'
                            break
                        
                        # 尝试解析JSON
                        try:
                            json_data = json.loads(data)
                            if format_type == 'openai' or format_type == 'azure':
                                if 'choices' in json_data and json_data['choices']:
                                    choice = json_data['choices'][0]
                                    
                                    if 'delta' in choice:
                                        delta = choice['delta']
                                        parsed_chunk['delta'] = delta
                                        if 'content' in delta:
                                            parsed_chunk['content'] = delta['content']
                                        parsed_chunk['role'] = delta.get('role', 'assistant')
                                    
                                    parsed_chunk['finish_reason'] = choice.get('finish_reason')
                                    if parsed_chunk['finish_reason']:
                                        parsed_chunk['is_finished'] = True
                        except json.JSONDecodeError:
                            logger.debug(f"无法解析JSON数据块: {data}")
            
            elif isinstance(chunk, dict):
                # 已经是字典格式，直接处理
                if format_type == 'openai' or format_type == 'azure':
                    if 'choices' in chunk and chunk['choices']:
                        choice = chunk['choices'][0]
                        
                        if 'delta' in choice:
                            delta = choice['delta']
                            parsed_chunk['delta'] = delta
                            if 'content' in delta:
                                parsed_chunk['content'] = delta['content']
                            parsed_chunk['role'] = delta.get('role', 'assistant')
                        
                        parsed_chunk['finish_reason'] = choice.get('finish_reason')
                        if parsed_chunk['finish_reason']:
                            parsed_chunk['is_finished'] = True
        
        except Exception as e:
            logger.error(f"解析流式数据块时出错: {str(e)}")
        
        return parsed_chunk


class ModelResponseHandler(StreamingResponseHandler):
    """
    大模型响应处理器
    专门处理大模型API的流式响应
    """
    
    def __init__(self, 
                 chunk_size: int = 1024,
                 format_type: str = 'openai',
                 process_chunk: Optional[Callable] = None,
                 collect_content: bool = True):
        """
        初始化大模型响应处理器
        
        Args:
            chunk_size: 读取块大小
            format_type: 模型响应格式 (openai, azure, custom)
            process_chunk: 处理每个块的回调函数
            collect_content: 是否收集完整内容
        """
        super().__init__(chunk_size=chunk_size, process_chunk=None, decode_json=False)
        self.format_type = format_type
        self.custom_process_chunk = process_chunk
        self.collect_content = collect_content
        self.full_content = ""
        self.response_parser = ModelResponseParser()
    
    def _create_stream_generator(self, response: Any) -> Generator[Dict[str, Any], None, None]:
        """
        创建大模型流式响应生成器
        
        Args:
            response: 请求响应对象
            
        Yields:
            处理后的每个数据块
        """
        try:
            for chunk in response.iter_content(chunk_size=self.chunk_size, decode_unicode=True):
                if chunk:
                    # 解析数据块
                    parsed_chunk = self.response_parser.parse_streaming_chunk(chunk, self.format_type)
                    
                    # 收集内容
                    if self.collect_content and parsed_chunk['content']:
                        self.full_content += parsed_chunk['content']
                    
                    # 添加完整内容到块信息中
                    parsed_chunk['full_content'] = self.full_content
                    
                    # 调用自定义处理函数
                    if self.custom_process_chunk:
                        try:
                            parsed_chunk = self.custom_process_chunk(parsed_chunk)
                        except Exception as e:
                            logger.error(f"自定义处理数据块时出错: {str(e)}")
                    
                    yield parsed_chunk
                    
                    # 检查是否结束
                    if parsed_chunk['is_finished']:
                        break
        except Exception as e:
            logger.error(f"处理大模型流式响应时出错: {str(e)}")
            raise
        finally:
            response.close()


class AsyncModelResponseHandler:
    """
    异步大模型响应处理器
    """
    
    def __init__(self, 
                 format_type: str = 'openai',
                 process_chunk: Optional[Callable] = None,
                 collect_content: bool = True):
        """
        初始化异步大模型响应处理器
        
        Args:
            format_type: 模型响应格式
            process_chunk: 处理每个块的回调函数
            collect_content: 是否收集完整内容
        """
        self.format_type = format_type
        self.process_chunk = process_chunk
        self.collect_content = collect_content
        self.full_content = ""
        self.response_parser = ModelResponseParser()
    
    async def handle_async_stream(self, 
                                 stream: AsyncGenerator[Any, None]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理异步流式响应
        
        Args:
            stream: 异步流生成器
            
        Yields:
            处理后的每个数据块
        """
        try:
            async for chunk in stream:
                # 解析数据块
                parsed_chunk = self.response_parser.parse_streaming_chunk(chunk, self.format_type)
                
                # 收集内容
                if self.collect_content and parsed_chunk['content']:
                    self.full_content += parsed_chunk['content']
                
                # 添加完整内容到块信息中
                parsed_chunk['full_content'] = self.full_content
                
                # 调用自定义处理函数
                if self.process_chunk:
                    try:
                        parsed_chunk = self.process_chunk(parsed_chunk)
                    except Exception as e:
                        logger.error(f"自定义处理数据块时出错: {str(e)}")
                
                yield parsed_chunk
                
                # 检查是否结束
                if parsed_chunk['is_finished']:
                    break
        except Exception as e:
            logger.error(f"处理异步大模型流式响应时出错: {str(e)}")
            raise


class ModelAPI:
    """
    大模型API封装类
    提供对各种大模型API的统一访问接口
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 timeout: int = 60,
                 retry_count: int = 3,
                 format_type: str = 'openai'):
        """
        初始化大模型API
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 默认模型名称
            timeout: 请求超时时间（秒）
            retry_count: 重试次数
            format_type: 响应格式类型 (openai, azure, custom)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.format_type = format_type
        
        # 创建请求管理器
        headers = {
            'Content-Type': 'application/json',
        }
        
        # 添加API密钥到请求头
        if api_key:
            if format_type == 'openai' or format_type == 'azure':
                headers['Authorization'] = f'Bearer {api_key}'
            else:
                headers['X-API-Key'] = api_key
        
        self.request_manager = RequestManager(
            timeout=timeout,
            retry_count=retry_count,
            retry_status_forcelist=(429, 500, 502, 503, 504),
            default_headers=headers
        )
        
        self.response_parser = ModelResponseParser()
    
    def _prepare_chat_request(self, 
                             messages: List[Dict[str, str]],
                             model: Optional[str] = None,
                             temperature: float = 0.7,
                             max_tokens: Optional[int] = None,
                             **kwargs) -> Dict[str, Any]:
        """
        准备聊天请求参数
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大令牌数
            **kwargs: 其他参数
            
        Returns:
            请求参数
        """
        request_data = {
            'model': model or self.model,
            'messages': messages,
            'temperature': temperature
        }
        
        if max_tokens is not None:
            request_data['max_tokens'] = max_tokens
        
        # 添加其他参数
        request_data.update(kwargs)
        
        return request_data
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]],
                       model: Optional[str] = None,
                       temperature: float = 0.7,
                       max_tokens: Optional[int] = None,
                       stream: bool = False,
                       process_chunk: Optional[Callable] = None,
                       **kwargs) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        聊天完成接口
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否使用流式响应
            process_chunk: 流式响应数据块处理函数
            **kwargs: 其他参数
            
        Returns:
            同步响应或流式生成器
        """
        # 准备请求URL
        url = f"{self.base_url}/chat/completions" if self.base_url else "https://api.openai.com/v1/chat/completions"
        
        # 准备请求参数
        request_data = self._prepare_chat_request(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # 设置流式响应
        request_data['stream'] = stream
        
        if stream:
            # 使用大模型响应处理器
            model_handler = ModelResponseHandler(
                format_type=self.format_type,
                process_chunk=process_chunk
            )
            
            # 发送请求
            response = self.request_manager.post(
                url,
                json_data=request_data,
                stream=True,
                stream_handler=model_handler
            )
            
            # 返回流式生成器
            return response['stream']
        else:
            # 发送同步请求
            response = self.request_manager.post(url, json_data=request_data)
            
            # 解析响应
            return self.response_parser.parse_openai_response(response)
    
    async def chat_completion_async(self, 
                                   messages: List[Dict[str, str]],
                                   model: Optional[str] = None,
                                   temperature: float = 0.7,
                                   max_tokens: Optional[int] = None,
                                   stream: bool = False,
                                   process_chunk: Optional[Callable] = None,
                                   **kwargs) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        异步聊天完成接口
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否使用流式响应
            process_chunk: 流式响应数据块处理函数
            **kwargs: 其他参数
            
        Returns:
            异步响应或异步流式生成器
        """
        # 准备请求URL
        url = f"{self.base_url}/chat/completions" if self.base_url else "https://api.openai.com/v1/chat/completions"
        
        # 准备请求参数
        request_data = self._prepare_chat_request(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        if not stream:
            # 发送异步请求
            response = await self.request_manager.post_async(url, json_data=request_data)
            
            # 解析响应
            return self.response_parser.parse_openai_response(response)
        else:
            # 设置流式响应
            request_data['stream'] = True
            
            # 获取流式响应
            raw_stream = self.request_manager.request_stream_async(
                'POST',
                url,
                json_data=request_data,
                decode_json=False
            )
            
            # 创建异步模型响应处理器
            async_handler = AsyncModelResponseHandler(
                format_type=self.format_type,
                process_chunk=process_chunk
            )
            
            # 返回处理后的异步流
            return async_handler.handle_async_stream(raw_stream)
    
    def text_completion(self, 
                       prompt: str,
                       model: Optional[str] = None,
                       temperature: float = 0.7,
                       max_tokens: Optional[int] = 16,
                       stream: bool = False,
                       process_chunk: Optional[Callable] = None,
                       **kwargs) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        文本补全接口
        
        Args:
            prompt: 提示文本
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否使用流式响应
            process_chunk: 流式响应数据块处理函数
            **kwargs: 其他参数
            
        Returns:
            同步响应或流式生成器
        """
        # 准备请求URL
        url = f"{self.base_url}/completions" if self.base_url else "https://api.openai.com/v1/completions"
        
        # 准备请求参数
        request_data = {
            'model': model or self.model,
            'prompt': prompt,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': stream
        }
        request_data.update(kwargs)
        
        if stream:
            # 使用大模型响应处理器
            model_handler = ModelResponseHandler(
                format_type=self.format_type,
                process_chunk=process_chunk
            )
            
            # 发送请求
            response = self.request_manager.post(
                url,
                json_data=request_data,
                stream=True,
                stream_handler=model_handler
            )
            
            # 返回流式生成器
            return response['stream']
        else:
            # 发送同步请求
            response = self.request_manager.post(url, json_data=request_data)
            
            # 解析响应
            return self.response_parser.parse_openai_response(response)
    
    def close(self) -> None:
        """
        关闭请求管理器
        """
        self.request_manager.close()


class OpenAIAPI(ModelAPI):
    """
    OpenAI API封装类
    """
    
    def __init__(self, 
                 api_key: str,
                 base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-3.5-turbo",
                 **kwargs):
        """
        初始化OpenAI API
        
        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL
            model: 默认模型名称
            **kwargs: 其他参数
        """
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            format_type='openai',
            **kwargs
        )


class AzureOpenAIAPI(ModelAPI):
    """
    Azure OpenAI API封装类
    """
    
    def __init__(self, 
                 api_key: str,
                 endpoint: str,
                 deployment_name: str,
                 api_version: str = "2023-05-15",
                 **kwargs):
        """
        初始化Azure OpenAI API
        
        Args:
            api_key: Azure API密钥
            endpoint: Azure API端点
            deployment_name: 部署名称
            api_version: API版本
            **kwargs: 其他参数
        """
        # 构建Azure API URL
        base_url = f"{endpoint}/openai/deployments/{deployment_name}"
        
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=deployment_name,
            format_type='azure',
            **kwargs
        )
        
        # 添加Azure特定的请求头
        self.request_manager.set_default_headers({
            'api-key': api_key,
            'Content-Type': 'application/json'
        })
        
        self.api_version = api_version
    
    def _prepare_chat_request(self, 
                             messages: List[Dict[str, str]],
                             model: Optional[str] = None,
                             temperature: float = 0.7,
                             max_tokens: Optional[int] = None,
                             **kwargs) -> Dict[str, Any]:
        """
        准备Azure聊天请求参数
        """
        # Azure不使用model参数，而是使用deployment_name
        request_data = {
            'messages': messages,
            'temperature': temperature
        }
        
        if max_tokens is not None:
            request_data['max_tokens'] = max_tokens
        
        # 添加其他参数
        request_data.update(kwargs)
        
        return request_data
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]],
                       temperature: float = 0.7,
                       max_tokens: Optional[int] = None,
                       stream: bool = False,
                       process_chunk: Optional[Callable] = None,
                       **kwargs) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        Azure聊天完成接口
        """
        # 准备请求URL，添加api-version参数
        url = f"{self.base_url}/chat/completions?api-version={self.api_version}"
        
        # 准备请求参数
        request_data = self._prepare_chat_request(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # 设置流式响应
        request_data['stream'] = stream
        
        if stream:
            # 使用大模型响应处理器
            model_handler = ModelResponseHandler(
                format_type=self.format_type,
                process_chunk=process_chunk
            )
            
            # 发送请求
            response = self.request_manager.post(
                url,
                json_data=request_data,
                stream=True,
                stream_handler=model_handler
            )
            
            # 返回流式生成器
            return response['stream']
        else:
            # 发送同步请求
            response = self.request_manager.post(url, json_data=request_data)
            
            # 解析响应
            return self.response_parser.parse_openai_response(response)


class CustomModelAPI(ModelAPI):
    """
    自定义大模型API封装类
    用于适配各种非标准格式的大模型API
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 base_url: str = "",
                 chat_endpoint: str = "/chat/completions",
                 headers: Optional[Dict[str, str]] = None,
                 format_type: str = 'custom',
                 **kwargs):
        """
        初始化自定义大模型API
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            chat_endpoint: 聊天接口路径
            headers: 自定义请求头
            format_type: 格式类型
            **kwargs: 其他参数
        """
        # 初始化请求头
        default_headers = {
            'Content-Type': 'application/json'
        }
        
        # 添加自定义请求头
        if headers:
            default_headers.update(headers)
        
        # 添加API密钥
        if api_key and 'Authorization' not in default_headers:
            default_headers['Authorization'] = f'Bearer {api_key}'
        
        # 创建请求管理器
        self.request_manager = RequestManager(
            timeout=kwargs.get('timeout', 60),
            retry_count=kwargs.get('retry_count', 3),
            retry_status_forcelist=(429, 500, 502, 503, 504),
            default_headers=default_headers
        )
        
        self.base_url = base_url.rstrip('/')
        self.chat_endpoint = chat_endpoint.lstrip('/')
        self.format_type = format_type
        self.response_parser = ModelResponseParser()
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]],
                       request_transformer: Optional[Callable] = None,
                       response_transformer: Optional[Callable] = None,
                       stream: bool = False,
                       process_chunk: Optional[Callable] = None,
                       **kwargs) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        自定义聊天完成接口
        
        Args:
            messages: 消息列表
            request_transformer: 请求转换器函数，用于将标准格式转换为API所需格式
            response_transformer: 响应转换器函数，用于将API响应转换为标准格式
            stream: 是否使用流式响应
            process_chunk: 流式响应数据块处理函数
            **kwargs: 其他参数
            
        Returns:
            同步响应或流式生成器
        """
        # 准备请求URL
        url = f"{self.base_url}/{self.chat_endpoint}"
        
        # 准备请求参数
        request_data = {
            'messages': messages,
            'stream': stream,
            **kwargs
        }
        
        # 转换请求格式
        if request_transformer:
            request_data = request_transformer(request_data)
        
        if stream:
            # 使用大模型响应处理器
            model_handler = ModelResponseHandler(
                format_type=self.format_type,
                process_chunk=process_chunk
            )
            
            # 发送请求
            response = self.request_manager.post(
                url,
                json_data=request_data,
                stream=True,
                stream_handler=model_handler
            )
            
            # 返回流式生成器
            return response['stream']
        else:
            # 发送同步请求
            response = self.request_manager.post(url, json_data=request_data)
            
            # 转换响应格式
            if response_transformer and response.get('json'):
                response['json'] = response_transformer(response['json'])
            
            # 解析响应
            return self.response_parser.parse_openai_response(response)


class ModelStreamProcessor:
    """
    大模型流式响应处理器
    提供各种流式响应的处理功能
    """
    
    @staticmethod
    def create_pretty_printer(prefix: str = "") -> Callable:
        """
        创建一个漂亮的打印处理器
        
        Args:
            prefix: 每行前缀
            
        Returns:
            处理函数
        """
        def printer(chunk: Dict[str, Any]) -> Dict[str, Any]:
            if chunk['content']:
                print(f"{prefix}{chunk['content']}", end="", flush=True)
            if chunk['is_finished']:
                print()  # 换行
            return chunk
        return printer
    
    @staticmethod
    def create_content_collector() -> tuple:
        """
        创建内容收集器
        
        Returns:
            (收集器函数, 获取内容函数) 的元组
        """
        full_content = [""]  # 使用列表作为可变对象
        
        def collector(chunk: Dict[str, Any]) -> Dict[str, Any]:
            full_content[0] += chunk.get('content', '')
            return chunk
        
        def get_content() -> str:
            return full_content[0]
        
        return collector, get_content
    
    @staticmethod
    def create_json_parser() -> Callable:
        """
        创建JSON解析器
        
        Returns:
            处理函数
        """
        buffer = [""]  # 用于存储不完整的JSON
        
        def json_parser(chunk: Dict[str, Any]) -> Dict[str, Any]:
            content = chunk.get('content', '')
            if content:
                # 尝试解析JSON
                try:
                    # 合并缓冲区和当前内容
                    json_str = buffer[0] + content
                    parsed = json.loads(json_str)
                    chunk['parsed_json'] = parsed
                    buffer[0] = ""  # 清空缓冲区
                except json.JSONDecodeError:
                    # JSON不完整，保存到缓冲区
                    buffer[0] = json_str
            return chunk
        
        return json_parser
    
    @staticmethod
    def create_time_measurer() -> tuple:
        """
        创建时间测量器
        
        Returns:
            (测量器函数, 获取统计信息函数) 的元组
        """
        start_time = time.time()
        chunks = []
        
        def time_measurer(chunk: Dict[str, Any]) -> Dict[str, Any]:
            current_time = time.time()
            chunk['elapsed_time'] = current_time - start_time
            chunk['chunk_index'] = len(chunks)
            chunks.append(chunk)
            return chunk
        
        def get_stats() -> Dict[str, Any]:
            if not chunks:
                return {'total_time': 0, 'chunk_count': 0}
            
            total_time = chunks[-1].get('elapsed_time', 0)
            total_content = "".join([c.get('content', '') for c in chunks])
            
            return {
                'total_time': total_time,
                'chunk_count': len(chunks),
                'content_length': len(total_content),
                'avg_speed': len(total_content) / total_time if total_time > 0 else 0
            }
        
        return time_measurer, get_stats


# 便捷函数
def create_model_api(api_type: str = 'openai', **kwargs) -> ModelAPI:
    """
    创建模型API实例
    
    Args:
        api_type: API类型 (openai, azure, custom)
        **kwargs: 相关参数
        
    Returns:
        ModelAPI实例
    """
    if api_type == 'openai':
        return OpenAIAPI(**kwargs)
    elif api_type == 'azure':
        return AzureOpenAIAPI(**kwargs)
    elif api_type == 'custom':
        return CustomModelAPI(**kwargs)
    else:
        raise ValueError(f"不支持的API类型: {api_type}")


def process_stream(stream: Generator[Dict[str, Any], None, None], 
                  processors: List[Callable]) -> Generator[Dict[str, Any], None, None]:
    """
    处理流式响应
    
    Args:
        stream: 流式生成器
        processors: 处理器函数列表
        
    Yields:
        处理后的每个数据块
    """
    for chunk in stream:
        processed_chunk = chunk
        for processor in processors:
            processed_chunk = processor(processed_chunk)
        yield processed_chunk


# 示例用法
if __name__ == "__main__":
    # 示例: 创建大模型API并使用流式响应
    print("=== 大模型API示例 ===")
    
    # 创建自定义模型API（不实际调用）
    model_api = CustomModelAPI(
        base_url="https://api.example.com/v1",
        timeout=30
    )
    
    # 准备消息
    messages = [
        {"role": "system", "content": "你是一个助手。"},
        {"role": "user", "content": "你好，请介绍一下自己。"}
    ]
    
    print("模拟流式响应处理:")
    
    # 定义模拟的流式响应数据
    mock_chunks = [
        "data: {\"id\": \"chatcmpl-123\", \"object\": \"chat.completion.chunk\", \"created\": 1677858242, \"model\": \"gpt-3.5-turbo\", \"choices\": [{\"index\": 0, \"delta\": {\"role\": \"assistant\"}, \"finish_reason\": null}]}\n\n",
        "data: {\"id\": \"chatcmpl-123\", \"object\": \"chat.completion.chunk\", \"created\": 1677858242, \"model\": \"gpt-3.5-turbo\", \"choices\": [{\"index\": 0, \"delta\": {\"content\": \"你好！\"}, \"finish_reason\": null}]}\n\n",
        "data: {\"id\": \"chatcmpl-123\", \"object\": \"chat.completion.chunk\", \"created\": 1677858242, \"model\": \"gpt-3.5-turbo\", \"choices\": [{\"index\": 0, \"delta\": {\"content\": \"我是一个AI助手。\"}, \"finish_reason\": null}]}\n\n",
        "data: {\"id\": \"chatcmpl-123\", \"object\": \"chat.completion.chunk\", \"created\": 1677858242, \"model\": \"gpt-3.5-turbo\", \"choices\": [{\"index\": 0, \"delta\": {\"content\": \"有什么可以帮助你的吗？\"}, \"finish_reason\": null}]}\n\n",
        "data: {\"id\": \"chatcmpl-123\", \"object\": \"chat.completion.chunk\", \"created\": 1677858242, \"model\": \"gpt-3.5-turbo\", \"choices\": [{\"index\": 0, \"delta\": {}, \"finish_reason\": \"stop\"}]}\n\n",
        "data: [DONE]\n\n"
    ]
    
    # 创建处理器
    pretty_printer = ModelStreamProcessor.create_pretty_printer("AI: ")
    collector, get_content = ModelStreamProcessor.create_content_collector()
    time_measurer, get_stats = ModelStreamProcessor.create_time_measurer()
    
    # 处理模拟数据
    for chunk in mock_chunks:
        parsed = ModelResponseParser.parse_streaming_chunk(chunk)
        pretty_printer(parsed)
        collector(parsed)
        time_measurer(parsed)
    
    # 打印收集的内容和统计信息
    print(f"\n收集的完整内容: {get_content()}")
    print(f"处理统计: {get_stats()}")
    
    # 关闭API
    model_api.close()
    
    print("\n大模型API示例完成")