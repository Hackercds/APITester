#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果提取工具模块
提供从HTTP响应、JSON、文本等数据中提取信息的功能
支持JSONPath、XPath、正则表达式等多种提取方式
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from xml.etree import ElementTree as ET

# 尝试导入jsonpath_ng，如果不可用则使用简单实现
HAS_JSONPATH = False
try:
    import jsonpath_ng  # 需要安装: pip install jsonpath-ng
    import jsonpath_ng.ext as jsonpath_ext
    HAS_JSONPATH = True
except ImportError:
    logger = logging.getLogger(__name__)  # 先初始化logger
    logger.warning("jsonpath_ng未安装，将使用简单的JSON路径实现。某些高级功能可能不可用。")

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _simple_json_path_extract(source: Any, path: str) -> Any:
    """
    简单的JSON路径提取实现，当jsonpath_ng不可用时使用
    仅支持基本的点表示法，如 $.a.b[0].c
    
    Args:
        source: JSON数据 (字典、列表)
        path: 简单的JSON路径
        
    Returns:
        提取的值，如果路径无效返回None
    """
    if not path or not source:
        return None
    
    # 移除开头的$符号和点
    if path.startswith('$'):
        path = path[1:]
    if path.startswith('.'):
        path = path[1:]
    
    # 解析路径部分
    parts = re.split(r'\.|\[(\d+)\]', path)
    parts = [p for p in parts if p]  # 过滤空字符串
    
    current = source
    
    for part in parts:
        # 处理索引访问 [0] 格式
        if part.isdigit():
            idx = int(part)
            if isinstance(current, list) and 0 <= idx < len(current):
                current = current[idx]
            else:
                return None
        # 处理属性访问 .name 格式
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    
    return current


class ExtractError(Exception):
    """
    提取错误异常
    """
    pass


class ExtractionResult:
    """
    提取结果类
    封装提取操作的结果
    """
    
    def __init__(self, 
                 success: bool,
                 value: Any = None,
                 error: Optional[str] = None,
                 extract_method: Optional[str] = None,
                 extract_pattern: Optional[str] = None):
        """
        初始化提取结果
        
        Args:
            success: 是否提取成功
            value: 提取的值
            error: 错误信息
            extract_method: 提取方法
            extract_pattern: 提取模式
        """
        self.success = success
        self.value = value
        self.error = error
        self.extract_method = extract_method
        self.extract_pattern = extract_pattern
    
    def __str__(self) -> str:
        """
        字符串表示
        """
        if self.success:
            return f"ExtractionResult(success=True, value={self.value})"
        else:
            return f"ExtractionResult(success=False, error={self.error})"
    
    def __repr__(self) -> str:
        """
        正式表示
        """
        return self.__str__()
    
    def get(self, default: Any = None) -> Any:
        """
        获取提取值，如果失败则返回默认值
        
        Args:
            default: 默认值
            
        Returns:
            提取的值或默认值
        """
        return self.value if self.success else default


class Extractor:
    """
    提取器基类
    定义提取器的基本接口
    """
    
    def extract(self, source: Any, pattern: str) -> ExtractionResult:
        """
        从源数据中提取信息
        
        Args:
            source: 源数据
            pattern: 提取模式
            
        Returns:
            提取结果
        """
        raise NotImplementedError("子类必须实现extract方法")
    
    def validate_pattern(self, pattern: str) -> bool:
        """
        验证提取模式是否有效
        
        Args:
            pattern: 提取模式
            
        Returns:
            是否有效
        """
        return True


class JSONExtractor(Extractor):
    """
    JSON提取器
    支持使用JSONPath语法从JSON数据中提取信息
    当jsonpath_ng不可用时会回退到简单实现
    """
    
    def extract(self, source: Any, pattern: str) -> ExtractionResult:
        """
        使用JSONPath提取JSON数据
        
        Args:
            source: JSON数据 (字典、列表或JSON字符串)
            pattern: JSONPath表达式
            
        Returns:
            提取结果
        """
        try:
            # 验证JSONPath模式
            if not self.validate_pattern(pattern):
                return ExtractionResult(
                    success=False,
                    error=f"无效的JSONPath表达式: {pattern}",
                    extract_method="jsonpath",
                    extract_pattern=pattern
                )
            
            # 确保source是JSON对象
            if isinstance(source, str):
                try:
                    source = json.loads(source)
                except json.JSONDecodeError as e:
                    return ExtractionResult(
                        success=False,
                        error=f"无效的JSON字符串: {str(e)}",
                        extract_method="jsonpath",
                        extract_pattern=pattern
                    )
            
            # 根据是否有jsonpath_ng选择不同的提取方法
            if HAS_JSONPATH:
                # 使用jsonpath_ng库进行提取
                try:
                    jsonpath_expr = jsonpath_ng.parse(pattern)
                    matches = jsonpath_expr.find(source)
                    
                    if not matches:
                        return ExtractionResult(
                            success=False,
                            error=f"JSONPath表达式没有匹配结果: {pattern}",
                            extract_method="jsonpath",
                            extract_pattern=pattern
                        )
                    
                    # 处理提取结果
                    if len(matches) == 1:
                        # 单个结果，直接返回值
                        return ExtractionResult(
                            success=True,
                            value=matches[0].value,
                            extract_method="jsonpath",
                            extract_pattern=pattern
                        )
                except Exception as e:
                    # 如果jsonpath_ng解析失败，尝试使用简单实现
                    logger.warning(f"jsonpath_ng解析失败，尝试使用简单实现: {str(e)}")
            
            # 使用简单的JSON路径实现
            value = _simple_json_path_extract(source, pattern)
            if value is not None:
                return ExtractionResult(
                    success=True,
                    value=value,
                    extract_method="simple_json_path",
                    extract_pattern=pattern
                )
            else:
                return ExtractionResult(
                    success=False,
                    error=f"简单JSON路径表达式没有匹配结果: {pattern}",
                    extract_method="simple_json_path",
                    extract_pattern=pattern
                )
                
        except Exception as e:
            logger.error(f"JSON提取失败: {str(e)}")
            return ExtractionResult(
                success=False,
                error=f"提取失败: {str(e)}",
                extract_method="jsonpath",
                extract_pattern=pattern
            )
    
    def validate_pattern(self, pattern: str) -> bool:
        """
        验证JSONPath表达式是否有效
        
        Args:
            pattern: JSONPath表达式
            
        Returns:
            是否有效
        """
        try:
            jsonpath_ng.parse(pattern)
            return True
        except Exception:
            return False
    
    def extract_by_path(self, source: Any, path: str, default: Any = None) -> Any:
        """
        使用点分隔的路径提取JSON数据
        如: "user.name" 等价于 "$.user.name"
        
        Args:
            source: JSON数据
            path: 点分隔的路径
            default: 默认值
            
        Returns:
            提取的值或默认值
        """
        # 转换为JSONPath表达式
        jsonpath_expr = f"$.{path}" if not path.startswith('$') else path
        result = self.extract(source, jsonpath_expr)
        return result.get(default)


class XMLExtractor(Extractor):
    """
    XML提取器
    支持使用XPath语法从XML数据中提取信息
    """
    
    def extract(self, source: Any, pattern: str) -> ExtractionResult:
        """
        使用XPath提取XML数据
        
        Args:
            source: XML数据 (字符串或ElementTree)
            pattern: XPath表达式
            
        Returns:
            提取结果
        """
        try:
            # 验证XPath模式
            if not self.validate_pattern(pattern):
                return ExtractionResult(
                    success=False,
                    error=f"无效的XPath表达式: {pattern}",
                    extract_method="xpath",
                    extract_pattern=pattern
                )
            
            # 解析XML
            if isinstance(source, str):
                try:
                    root = ET.fromstring(source)
                except ET.ParseError as e:
                    return ExtractionResult(
                        success=False,
                        error=f"无效的XML字符串: {str(e)}",
                        extract_method="xpath",
                        extract_pattern=pattern
                    )
            elif isinstance(source, ET.Element):
                root = source
            else:
                return ExtractionResult(
                    success=False,
                    error=f"不支持的XML源类型: {type(source)}",
                    extract_method="xpath",
                    extract_pattern=pattern
                )
            
            # 执行XPath查询
            try:
                results = root.findall(pattern)
            except Exception as e:
                return ExtractionResult(
                    success=False,
                    error=f"XPath查询错误: {str(e)}",
                    extract_method="xpath",
                    extract_pattern=pattern
                )
            
            if not results:
                return ExtractionResult(
                    success=False,
                    error=f"XPath表达式没有匹配结果: {pattern}",
                    extract_method="xpath",
                    extract_pattern=pattern
                )
            
            # 处理提取结果
            extracted_values = []
            for result in results:
                if result.text is not None:
                    extracted_values.append(result.text.strip())
                else:
                    # 可以选择返回元素的字典表示
                    element_dict = {}
                    for key, value in result.attrib.items():
                        element_dict[f"@{key}"] = value
                    if len(element_dict) == 0:
                        extracted_values.append("")
                    else:
                        extracted_values.append(element_dict)
            
            # 如果只有一个结果，直接返回
            if len(extracted_values) == 1:
                return ExtractionResult(
                    success=True,
                    value=extracted_values[0],
                    extract_method="xpath",
                    extract_pattern=pattern
                )
            else:
                return ExtractionResult(
                    success=True,
                    value=extracted_values,
                    extract_method="xpath",
                    extract_pattern=pattern
                )
                
        except Exception as e:
            logger.error(f"XML提取失败: {str(e)}")
            return ExtractionResult(
                success=False,
                error=f"提取失败: {str(e)}",
                extract_method="xpath",
                extract_pattern=pattern
            )
    
    def validate_pattern(self, pattern: str) -> bool:
        """
        简单验证XPath表达式
        
        Args:
            pattern: XPath表达式
            
        Returns:
            是否有效
        """
        # 简单的XPath验证
        return isinstance(pattern, str) and pattern
    
    def extract_attribute(self, source: Any, element_path: str, attribute_name: str) -> ExtractionResult:
        """
        提取XML元素的属性值
        
        Args:
            source: XML数据
            element_path: 元素的XPath
            attribute_name: 属性名
            
        Returns:
            提取结果
        """
        xpath_expr = f"{element_path}/@{attribute_name}"
        result = self.extract(source, xpath_expr)
        return result


class RegexExtractor(Extractor):
    """
    正则表达式提取器
    使用正则表达式从文本中提取信息
    """
    
    def extract(self, source: Any, pattern: str) -> ExtractionResult:
        """
        使用正则表达式提取文本
        
        Args:
            source: 源文本
            pattern: 正则表达式
            
        Returns:
            提取结果
        """
        try:
            # 验证正则表达式
            if not self.validate_pattern(pattern):
                return ExtractionResult(
                    success=False,
                    error=f"无效的正则表达式: {pattern}",
                    extract_method="regex",
                    extract_pattern=pattern
                )
            
            # 确保源是字符串
            if not isinstance(source, str):
                source = str(source)
            
            # 编译正则表达式
            try:
                regex = re.compile(pattern, re.DOTALL)
            except re.error as e:
                return ExtractionResult(
                    success=False,
                    error=f"正则表达式编译错误: {str(e)}",
                    extract_method="regex",
                    extract_pattern=pattern
                )
            
            # 执行匹配
            matches = regex.findall(source)
            
            if not matches:
                return ExtractionResult(
                    success=False,
                    error=f"正则表达式没有匹配结果: {pattern}",
                    extract_method="regex",
                    extract_pattern=pattern
                )
            
            # 处理提取结果
            # 如果使用了捕获组，可能需要特殊处理
            if len(matches) == 1 and isinstance(matches[0], tuple):
                # 单个元组结果，可能是多个捕获组
                if len(matches[0]) == 1:
                    # 只有一个捕获组，直接返回值
                    return ExtractionResult(
                        success=True,
                        value=matches[0][0],
                        extract_method="regex",
                        extract_pattern=pattern
                    )
                else:
                    # 多个捕获组，返回元组
                    return ExtractionResult(
                        success=True,
                        value=matches[0],
                        extract_method="regex",
                        extract_pattern=pattern
                    )
            else:
                # 多个匹配或单个非元组匹配
                if len(matches) == 1:
                    return ExtractionResult(
                        success=True,
                        value=matches[0],
                        extract_method="regex",
                        extract_pattern=pattern
                    )
                else:
                    # 检查是否所有匹配都是元组
                    if all(isinstance(match, tuple) for match in matches):
                        # 如果有多个捕获组结果，返回列表
                        return ExtractionResult(
                            success=True,
                            value=matches,
                            extract_method="regex",
                            extract_pattern=pattern
                        )
                    else:
                        # 简单的字符串匹配列表
                        return ExtractionResult(
                            success=True,
                            value=matches,
                            extract_method="regex",
                            extract_pattern=pattern
                        )
                        
        except Exception as e:
            logger.error(f"正则表达式提取失败: {str(e)}")
            return ExtractionResult(
                success=False,
                error=f"提取失败: {str(e)}",
                extract_method="regex",
                extract_pattern=pattern
            )
    
    def validate_pattern(self, pattern: str) -> bool:
        """
        验证正则表达式是否有效
        
        Args:
            pattern: 正则表达式
            
        Returns:
            是否有效
        """
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False
    
    def extract_first(self, source: str, pattern: str, default: Any = None) -> Any:
        """
        提取第一个匹配的结果
        
        Args:
            source: 源文本
            pattern: 正则表达式
            default: 默认值
            
        Returns:
            第一个匹配的值或默认值
        """
        result = self.extract(source, pattern)
        if result.success:
            value = result.value
            if isinstance(value, list):
                return value[0] if value else default
            return value
        return default
    
    def extract_group(self, source: str, pattern: str, group_index: int = 1, default: Any = None) -> Any:
        """
        提取指定捕获组的结果
        
        Args:
            source: 源文本
            pattern: 正则表达式
            group_index: 捕获组索引
            default: 默认值
            
        Returns:
            指定捕获组的值或默认值
        """
        try:
            regex = re.compile(pattern, re.DOTALL)
            match = regex.search(source)
            if match:
                return match.group(group_index)
            return default
        except Exception:
            return default


class HeaderExtractor(Extractor):
    """
    HTTP头部提取器
    从HTTP响应头中提取信息
    """
    
    def extract(self, source: Dict[str, str], pattern: str) -> ExtractionResult:
        """
        从HTTP头部字典中提取信息
        
        Args:
            source: HTTP头部字典
            pattern: 头部名称
            
        Returns:
            提取结果
        """
        try:
            # 验证头部名称
            if not self.validate_pattern(pattern):
                return ExtractionResult(
                    success=False,
                    error=f"无效的头部名称: {pattern}",
                    extract_method="header",
                    extract_pattern=pattern
                )
            
            # 确保source是字典
            if not isinstance(source, dict):
                return ExtractionResult(
                    success=False,
                    error=f"不支持的头部源类型: {type(source)}",
                    extract_method="header",
                    extract_pattern=pattern
                )
            
            # 头部名称通常不区分大小写
            header_name = pattern.lower()
            
            # 查找头部
            for key, value in source.items():
                if key.lower() == header_name:
                    return ExtractionResult(
                        success=True,
                        value=value,
                        extract_method="header",
                        extract_pattern=pattern
                    )
            
            # 未找到头部
            return ExtractionResult(
                success=False,
                error=f"头部不存在: {pattern}",
                extract_method="header",
                extract_pattern=pattern
            )
            
        except Exception as e:
            logger.error(f"头部提取失败: {str(e)}")
            return ExtractionResult(
                success=False,
                error=f"提取失败: {str(e)}",
                extract_method="header",
                extract_pattern=pattern
            )
    
    def validate_pattern(self, pattern: str) -> bool:
        """
        验证头部名称是否有效
        
        Args:
            pattern: 头部名称
            
        Returns:
            是否有效
        """
        return isinstance(pattern, str) and pattern


class ResponseExtractor:
    """
    HTTP响应提取器
    从HTTP响应中提取各种信息
    """
    
    def __init__(self):
        """
        初始化响应提取器
        """
        self.json_extractor = JSONExtractor()
        self.regex_extractor = RegexExtractor()
        self.header_extractor = HeaderExtractor()
        self.xml_extractor = XMLExtractor()
    
    def extract_from_response(self, 
                            response: Dict[str, Any],
                            extract_config: Union[str, Dict[str, Any]]) -> ExtractionResult:
        """
        从HTTP响应中提取信息
        
        Args:
            response: HTTP响应字典，包含status_code、headers、text、json等字段
            extract_config: 提取配置，可以是字符串(自动判断类型)或字典(指定提取方法)
            
        Returns:
            提取结果
        """
        try:
            # 处理字符串配置
            if isinstance(extract_config, str):
                # 自动判断提取类型
                if extract_config.startswith('$') or '.' in extract_config:
                    # JSONPath或点路径
                    json_data = response.get('json') or response.get('text')
                    if json_data:
                        return self.json_extractor.extract(json_data, extract_config)
                    return ExtractionResult(
                        success=False,
                        error="响应不包含JSON数据",
                        extract_method="auto",
                        extract_pattern=extract_config
                    )
                elif extract_config.startswith('//') or extract_config.startswith('/'):
                    # XPath
                    text_data = response.get('text')
                    if text_data:
                        return self.xml_extractor.extract(text_data, extract_config)
                    return ExtractionResult(
                        success=False,
                        error="响应不包含文本数据",
                        extract_method="auto",
                        extract_pattern=extract_config
                    )
                elif extract_config.startswith('header.'):
                    # 头部提取
                    header_name = extract_config[7:]  # 去掉 'header.'
                    headers = response.get('headers', {})
                    return self.header_extractor.extract(headers, header_name)
                elif extract_config.startswith('status') or extract_config == 'status_code':
                    # 状态码
                    return ExtractionResult(
                        success=True,
                        value=response.get('status_code'),
                        extract_method="status_code",
                        extract_pattern=extract_config
                    )
                else:
                    # 尝试正则表达式
                    text_data = response.get('text', '')
                    return self.regex_extractor.extract(text_data, extract_config)
            
            # 处理字典配置
            elif isinstance(extract_config, dict):
                method = extract_config.get('method', '').lower()
                pattern = extract_config.get('pattern')
                
                if not method or not pattern:
                    return ExtractionResult(
                        success=False,
                        error="提取配置缺少method或pattern",
                        extract_method=method or "unknown"
                    )
                
                # 根据方法提取
                if method == 'jsonpath' or method == 'json':
                    json_data = response.get('json') or response.get('text')
                    if json_data:
                        return self.json_extractor.extract(json_data, pattern)
                    return ExtractionResult(
                        success=False,
                        error="响应不包含JSON数据",
                        extract_method=method,
                        extract_pattern=pattern
                    )
                
                elif method == 'regex' or method == 'regular_expression':
                    text_data = response.get('text', '')
                    return self.regex_extractor.extract(text_data, pattern)
                
                elif method == 'header':
                    headers = response.get('headers', {})
                    return self.header_extractor.extract(headers, pattern)
                
                elif method == 'xpath' or method == 'xml':
                    text_data = response.get('text')
                    if text_data:
                        return self.xml_extractor.extract(text_data, pattern)
                    return ExtractionResult(
                        success=False,
                        error="响应不包含文本数据",
                        extract_method=method,
                        extract_pattern=pattern
                    )
                
                elif method == 'status_code' or method == 'status':
                    return ExtractionResult(
                        success=True,
                        value=response.get('status_code'),
                        extract_method=method,
                        extract_pattern=pattern
                    )
                
                elif method == 'length' or method == 'size':
                    # 提取响应长度
                    if pattern == 'text':
                        value = len(response.get('text', ''))
                    elif pattern == 'json':
                        json_data = response.get('json', {})
                        value = len(json.dumps(json_data))
                    else:
                        return ExtractionResult(
                            success=False,
                            error=f"不支持的长度提取类型: {pattern}",
                            extract_method=method,
                            extract_pattern=pattern
                        )
                    
                    return ExtractionResult(
                        success=True,
                        value=value,
                        extract_method=method,
                        extract_pattern=pattern
                    )
                
                else:
                    return ExtractionResult(
                        success=False,
                        error=f"不支持的提取方法: {method}",
                        extract_method=method,
                        extract_pattern=pattern
                    )
            
            # 不支持的配置类型
            return ExtractionResult(
                success=False,
                error=f"不支持的提取配置类型: {type(extract_config)}"
            )
            
        except Exception as e:
            logger.error(f"响应提取失败: {str(e)}")
            return ExtractionResult(
                success=False,
                error=f"提取失败: {str(e)}"
            )
    
    def batch_extract(self, 
                     response: Dict[str, Any],
                     extract_configs: Dict[str, Union[str, Dict[str, Any]]]) -> Dict[str, ExtractionResult]:
        """
        批量从HTTP响应中提取信息
        
        Args:
            response: HTTP响应
            extract_configs: 提取配置字典，键为结果名称，值为提取配置
            
        Returns:
            提取结果字典
        """
        results = {}
        
        for name, config in extract_configs.items():
            results[name] = self.extract_from_response(response, config)
        
        return results
    
    def extract_cookie(self, response: Dict[str, Any], cookie_name: str) -> ExtractionResult:
        """
        从响应中提取Cookie
        
        Args:
            response: HTTP响应
            cookie_name: Cookie名称
            
        Returns:
            提取结果
        """
        try:
            # 尝试从headers中提取
            headers = response.get('headers', {})
            
            # 检查Set-Cookie头部
            set_cookie = headers.get('Set-Cookie', '')
            if set_cookie:
                # 使用正则表达式提取Cookie值
                pattern = rf'{cookie_name}=([^;]+)'
                result = self.regex_extractor.extract(set_cookie, pattern)
                if result.success:
                    return result
            
            # 未找到Cookie
            return ExtractionResult(
                success=False,
                error=f"Cookie不存在: {cookie_name}",
                extract_method="cookie",
                extract_pattern=cookie_name
            )
            
        except Exception as e:
            logger.error(f"Cookie提取失败: {str(e)}")
            return ExtractionResult(
                success=False,
                error=f"提取失败: {str(e)}",
                extract_method="cookie",
                extract_pattern=cookie_name
            )


class ExtractionManager:
    """
    提取管理器
    管理和协调多种提取器
    """
    
    def __init__(self):
        """
        初始化提取管理器
        """
        self.extractors = {
            'json': JSONExtractor(),
            'jsonpath': JSONExtractor(),
            'regex': RegexExtractor(),
            'header': HeaderExtractor(),
            'xml': XMLExtractor(),
            'xpath': XMLExtractor()
        }
        self.response_extractor = ResponseExtractor()
        self.extraction_history = []
    
    def register_extractor(self, name: str, extractor: Extractor) -> None:
        """
        注册自定义提取器
        
        Args:
            name: 提取器名称
            extractor: 提取器实例
        """
        if not isinstance(extractor, Extractor):
            raise TypeError("提取器必须是Extractor的子类")
        
        self.extractors[name] = extractor
    
    def extract(self, 
               source: Any,
               extractor_name: str,
               pattern: str) -> ExtractionResult:
        """
        使用指定提取器提取信息
        
        Args:
            source: 源数据
            extractor_name: 提取器名称
            pattern: 提取模式
            
        Returns:
            提取结果
        """
        if extractor_name not in self.extractors:
            result = ExtractionResult(
                success=False,
                error=f"未知的提取器: {extractor_name}",
                extract_method=extractor_name,
                extract_pattern=pattern
            )
        else:
            extractor = self.extractors[extractor_name]
            result = extractor.extract(source, pattern)
        
        # 记录提取历史
        self.extraction_history.append({
            'source_type': type(source).__name__,
            'extractor': extractor_name,
            'pattern': pattern,
            'result': result
        })
        
        return result
    
    def extract_from_response(self, 
                            response: Dict[str, Any],
                            extract_config: Union[str, Dict[str, Any]]) -> ExtractionResult:
        """
        从HTTP响应中提取信息
        
        Args:
            response: HTTP响应
            extract_config: 提取配置
            
        Returns:
            提取结果
        """
        result = self.response_extractor.extract_from_response(response, extract_config)
        
        # 记录提取历史
        self.extraction_history.append({
            'source_type': 'HTTPResponse',
            'extractor': 'response',
            'pattern': str(extract_config),
            'result': result
        })
        
        return result
    
    def batch_extract_from_response(self, 
                                   response: Dict[str, Any],
                                   extract_configs: Dict[str, Union[str, Dict[str, Any]]]) -> Dict[str, Any]:
        """
        批量从HTTP响应中提取信息，并返回提取的值（而非完整结果对象）
        
        Args:
            response: HTTP响应
            extract_configs: 提取配置字典
            
        Returns:
            提取的值字典
        """
        results = {}
        
        for name, config in extract_configs.items():
            extraction_result = self.extract_from_response(response, config)
            results[name] = extraction_result.value if extraction_result.success else None
        
        return results
    
    def get_extraction_history(self) -> List[Dict[str, Any]]:
        """
        获取提取历史
        
        Returns:
            提取历史列表
        """
        return self.extraction_history
    
    def clear_extraction_history(self) -> None:
        """
        清除提取历史
        """
        self.extraction_history = []
    
    def create_extraction_template(self, 
                                 name: str,
                                 extractor_name: str,
                                 pattern: str,
                                 description: Optional[str] = None) -> Dict[str, str]:
        """
        创建提取模板
        
        Args:
            name: 模板名称
            extractor_name: 提取器名称
            pattern: 提取模式
            description: 描述
            
        Returns:
            提取模板
        """
        template = {
            'name': name,
            'method': extractor_name,
            'pattern': pattern
        }
        
        if description:
            template['description'] = description
        
        return template


# 便捷函数
def extract_json(source: Any, pattern: str) -> Any:
    """
    便捷函数：从JSON中提取数据
    
    Args:
        source: JSON数据
        pattern: JSONPath表达式
        
    Returns:
        提取的值
    """
    extractor = JSONExtractor()
    result = extractor.extract(source, pattern)
    return result.value


def extract_regex(source: str, pattern: str) -> Any:
    """
    便捷函数：使用正则表达式提取数据
    
    Args:
        source: 源文本
        pattern: 正则表达式
        
    Returns:
        提取的值
    """
    extractor = RegexExtractor()
    result = extractor.extract(source, pattern)
    return result.value


def extract_header(headers: Dict[str, str], header_name: str) -> Any:
    """
    便捷函数：从HTTP头部提取数据
    
    Args:
        headers: HTTP头部字典
        header_name: 头部名称
        
    Returns:
        提取的值
    """
    extractor = HeaderExtractor()
    result = extractor.extract(headers, header_name)
    return result.value


def extract_from_response(response: Dict[str, Any], extract_config: Union[str, Dict[str, Any]]) -> Any:
    """
    便捷函数：从HTTP响应中提取数据
    
    Args:
        response: HTTP响应
        extract_config: 提取配置
        
    Returns:
        提取的值
    """
    extractor = ResponseExtractor()
    result = extractor.extract_from_response(response, extract_config)
    return result.value


# 全局提取管理器实例
extraction_manager = ExtractionManager()


# 示例用法
if __name__ == "__main__":
    print("=== 结果提取工具示例 ===")
    
    # 模拟HTTP响应
    mock_response = {
        'status_code': 200,
        'headers': {
            'Content-Type': 'application/json',
            'X-Request-ID': 'req-123456',
            'Set-Cookie': 'session_id=abc123; path=/; expires=Wed, 13 Jan 2023 22:23:01 GMT'
        },
        'text': '{"user": {"id": 123, "name": "张三", "email": "zhangsan@example.com"}, "data": [1, 2, 3, 4, 5]}',
        'json': {
            'user': {
                'id': 123,
                'name': '张三',
                'email': 'zhangsan@example.com'
            },
            'data': [1, 2, 3, 4, 5]
        }
    }
    
    # 示例1: 使用JSONPath提取
    print("\n示例1: 使用JSONPath提取用户名称")
    json_result = extract_json(mock_response['json'], '$.user.name')
    print(f"结果: {json_result}")
    
    # 示例2: 使用正则表达式提取ID
    print("\n示例2: 使用正则表达式提取请求ID")
    regex_result = extract_regex(mock_response['headers']['X-Request-ID'], r'req-(\\d+)')
    print(f"结果: {regex_result}")
    
    # 示例3: 从头部提取
    print("\n示例3: 从头部提取内容类型")
    header_result = extract_header(mock_response['headers'], 'Content-Type')
    print(f"结果: {header_result}")
    
    # 示例4: 使用响应提取器自动判断
    print("\n示例4: 使用响应提取器自动判断提取方式")
    # JSONPath
    auto_result1 = extract_from_response(mock_response, '$.user.id')
    print(f"提取用户ID: {auto_result1}")
    
    # 头部
    auto_result2 = extract_from_response(mock_response, 'header.X-Request-ID')
    print(f"提取请求ID: {auto_result2}")
    
    # 状态码
    auto_result3 = extract_from_response(mock_response, 'status_code')
    print(f"提取状态码: {auto_result3}")
    
    # 示例5: 使用配置字典
    print("\n示例5: 使用配置字典提取")
    config_result = extract_from_response(mock_response, {
        'method': 'jsonpath',
        'pattern': '$.data[*]'
    })
    print(f"提取数据数组: {config_result}")
    
    # 示例6: 批量提取
    print("\n示例6: 批量提取")
    batch_results = extraction_manager.batch_extract_from_response(mock_response, {
        'username': '$.user.name',
        'user_id': '$.user.id',
        'content_type': 'header.Content-Type',
        'status': 'status_code'
    })
    print(f"批量提取结果: {batch_results}")
    
    # 示例7: 提取Cookie
    print("\n示例7: 提取Cookie")
    cookie_result = extraction_manager.response_extractor.extract_cookie(mock_response, 'session_id')
    print(f"提取Cookie: {cookie_result.value if cookie_result.success else cookie_result.error}")
    
    print("\n结果提取工具示例完成")