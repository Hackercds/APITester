#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
断言工具类，提供增强的断言验证功能
支持多种断言类型和自定义断言
"""

import json
import re
from typing import Any, Dict, List, Union, Optional, Callable
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class AssertionError(Exception):
    """自定义断言错误异常"""
    pass


class AssertionResult:
    """
    断言结果类，用于存储断言的详细信息
    """
    def __init__(self, success: bool, message: str = "", actual_value: Any = None, 
                 expected_value: Any = None, assertion_type: str = ""):
        self.success = success
        self.message = message
        self.actual_value = actual_value
        self.expected_value = expected_value
        self.assertion_type = assertion_type
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "message": self.message,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "assertion_type": self.assertion_type
        }


class AssertionManager:
    """
    断言管理器，提供丰富的断言方法
    """
    
    def __init__(self):
        # 存储自定义断言函数
        self._custom_assertions: Dict[str, Callable] = {}
        # 存储断言结果历史
        self._assertion_history: List[AssertionResult] = []
    
    def register_assertion(self, name: str, assertion_func: Callable) -> None:
        """
        注册自定义断言函数
        
        Args:
            name: 断言函数名称
            assertion_func: 断言函数，应返回(成功布尔值, 错误消息)元组
        """
        self._custom_assertions[name] = assertion_func
        logger.info(f"已注册自定义断言: {name}")
    
    def assert_equal(self, actual: Any, expected: Any, message: str = "", 
                    ignore_order: bool = False, approx: bool = False, tolerance: float = 0.01) -> AssertionResult:
        """
        断言相等，支持近似比较和顺序忽略
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            ignore_order: 是否忽略顺序（用于列表比较）
            approx: 是否进行近似比较（用于数值比较）
            tolerance: 近似比较的容差
            
        Returns:
            AssertionResult: 断言结果
        """
        success = True
        error_msg = message
        
        try:
            # 处理列表类型比较
            if isinstance(actual, list) and isinstance(expected, list):
                if ignore_order:
                    if len(actual) != len(expected):
                        success = False
                        error_msg = error_msg or f"列表长度不匹配: 期望 {len(expected)}，实际 {len(actual)}"
                    else:
                        # 尝试深度比较每个元素
                        from collections import Counter
                        # 处理不可哈希类型的情况
                        try:
                            success = Counter(actual) == Counter(expected)
                        except TypeError:
                            # 对于不可哈希类型，进行更复杂的比较
                            sorted_actual = sorted(actual, key=str)
                            sorted_expected = sorted(expected, key=str)
                            success = sorted_actual == sorted_expected
                        
                        if not success:
                            error_msg = error_msg or f"列表内容不匹配: 期望 {expected}，实际 {actual}"
                else:
                    # 保持顺序比较
                    success = actual == expected
                    if not success:
                        error_msg = error_msg or f"列表不匹配: 期望 {expected}，实际 {actual}"
            
            # 处理数值类型的近似比较
            elif approx and isinstance(actual, (int, float, Decimal)) and isinstance(expected, (int, float, Decimal)):
                success = abs(float(actual) - float(expected)) <= tolerance
                if not success:
                    error_msg = error_msg or f"数值不近似相等: 期望 {expected} ± {tolerance}，实际 {actual}"
            
            # 处理字典类型比较
            elif isinstance(actual, dict) and isinstance(expected, dict):
                # 检查expected中的所有键值对是否在actual中存在且相等
                success = True
                for key, value in expected.items():
                    if key not in actual:
                        success = False
                        error_msg = error_msg or f"字典缺少键: {key}"
                        break
                    
                    # 递归检查嵌套结构
                    if isinstance(value, dict) and isinstance(actual[key], dict):
                        sub_result = self.assert_equal(actual[key], value)
                        if not sub_result.success:
                            success = False
                            error_msg = error_msg or f"键 '{key}' 下的字典不匹配: {sub_result.message}"
                            break
                    elif isinstance(value, list) and isinstance(actual[key], list):
                        sub_result = self.assert_equal(actual[key], value, ignore_order=ignore_order)
                        if not sub_result.success:
                            success = False
                            error_msg = error_msg or f"键 '{key}' 下的列表不匹配: {sub_result.message}"
                            break
                    elif actual[key] != value:
                        success = False
                        error_msg = error_msg or f"字典值不匹配，键 '{key}': 期望 {value}，实际 {actual[key]}"
                        break
            
            # 处理其他类型
            else:
                success = actual == expected
                if not success:
                    error_msg = error_msg or f"不相等: 期望 {expected}，实际 {actual}"
                    
        except Exception as e:
            success = False
            error_msg = error_msg or f"断言比较过程中出错: {str(e)}"
        
        result = AssertionResult(
            success=success,
            message=error_msg,
            actual_value=actual,
            expected_value=expected,
            assertion_type="assert_equal"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_not_equal(self, actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """
        断言不相等
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        success = actual != expected
        error_msg = message or f"相等，但期望不相等: {actual}"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual,
            expected_value=expected,
            assertion_type="assert_not_equal"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_true(self, condition: Any, message: str = "") -> AssertionResult:
        """
        断言为True
        
        Args:
            condition: 条件
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        success = bool(condition)
        error_msg = message or f"条件为False，但期望为True"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=condition,
            expected_value=True,
            assertion_type="assert_true"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_false(self, condition: Any, message: str = "") -> AssertionResult:
        """
        断言为False
        
        Args:
            condition: 条件
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        success = not bool(condition)
        error_msg = message or f"条件为True，但期望为False"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=condition,
            expected_value=False,
            assertion_type="assert_false"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_in(self, item: Any, container: Any, message: str = "") -> AssertionResult:
        """
        断言item在container中
        
        Args:
            item: 要检查的项
            container: 容器
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        try:
            success = item in container
            error_msg = message or f"{item} 不在 {container} 中"
        except TypeError:
            success = False
            error_msg = message or f"无法检查 {item} 是否在 {container} 中（类型不支持）"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=container,
            expected_value=item,
            assertion_type="assert_in"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_not_in(self, item: Any, container: Any, message: str = "") -> AssertionResult:
        """
        断言item不在container中
        
        Args:
            item: 要检查的项
            container: 容器
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        try:
            success = item not in container
            error_msg = message or f"{item} 在 {container} 中，但期望不在"
        except TypeError:
            success = False
            error_msg = message or f"无法检查 {item} 是否在 {container} 中（类型不支持）"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=container,
            expected_value=item,
            assertion_type="assert_not_in"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_is_none(self, value: Any, message: str = "") -> AssertionResult:
        """
        断言为None
        
        Args:
            value: 要检查的值
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        success = value is None
        error_msg = message or f"值不为None: {value}"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=value,
            expected_value=None,
            assertion_type="assert_is_none"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_is_not_none(self, value: Any, message: str = "") -> AssertionResult:
        """
        断言不为None
        
        Args:
            value: 要检查的值
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        success = value is not None
        error_msg = message or "值为None，但期望不为None"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=value,
            expected_value="not None",
            assertion_type="assert_is_not_none"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_contains(self, actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """
        断言实际值包含期望值（适用于字符串、列表、字典）
        
        Args:
            actual: 实际值
            expected: 期望包含的值
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        success = True
        error_msg = message
        
        # 字符串包含
        if isinstance(actual, str) and isinstance(expected, str):
            success = expected in actual
            error_msg = error_msg or f"字符串不包含: 期望 '{expected}' 在 '{actual}' 中"
        
        # 列表包含
        elif isinstance(actual, list):
            success = expected in actual
            error_msg = error_msg or f"列表不包含: {expected} 不在 {actual} 中"
        
        # 字典包含键值对
        elif isinstance(actual, dict):
            if isinstance(expected, dict):
                # 检查expected中的所有键值对是否在actual中存在且相等
                for key, value in expected.items():
                    if key not in actual or actual[key] != value:
                        success = False
                        error_msg = error_msg or f"字典不包含键值对: {key}: {value}"
                        break
            else:
                # 检查expected是否是字典中的键
                success = expected in actual
                error_msg = error_msg or f"字典不包含键: {expected}"
        
        # 其他类型不支持
        else:
            success = False
            error_msg = error_msg or f"不支持的类型比较: {type(actual)} 和 {type(expected)}"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual,
            expected_value=expected,
            assertion_type="assert_contains"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_regex(self, actual: str, pattern: str, message: str = "") -> AssertionResult:
        """
        断言字符串匹配正则表达式
        
        Args:
            actual: 实际字符串
            pattern: 正则表达式
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        try:
            success = bool(re.search(pattern, str(actual)))
            error_msg = message or f"字符串 '{actual}' 不匹配正则表达式 '{pattern}'"
        except re.error:
            success = False
            error_msg = message or f"无效的正则表达式: {pattern}"
        except Exception as e:
            success = False
            error_msg = message or f"正则匹配出错: {str(e)}"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual,
            expected_value=pattern,
            assertion_type="assert_regex"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_status_code(self, response: Dict[str, Any], expected_code: int, message: str = "") -> AssertionResult:
        """
        断言响应状态码
        
        Args:
            response: 响应对象，包含status_code字段
            expected_code: 期望的状态码
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        actual_code = response.get('status_code')
        success = actual_code == expected_code
        
        error_msg = message
        if not success:
            # 获取响应内容以便更好地调试
            content = response.get('content', 'N/A')
            if isinstance(content, dict):
                content_str = json.dumps(content, ensure_ascii=False)
            else:
                content_str = str(content)
            
            error_msg = error_msg or f"状态码不匹配: 期望 {expected_code}，实际 {actual_code}\n响应内容: {content_str[:500]}..." if len(content_str) > 500 else f"状态码不匹配: 期望 {expected_code}，实际 {actual_code}\n响应内容: {content_str}"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual_code,
            expected_value=expected_code,
            assertion_type="assert_status_code"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_json_contains(self, response: Dict[str, Any], expected_data: Dict[str, Any], 
                            message: str = "", ignore_order: bool = False) -> AssertionResult:
        """
        断言JSON响应包含指定数据
        
        Args:
            response: 响应对象，包含content字段
            expected_data: 期望包含的数据
            message: 自定义错误消息
            ignore_order: 是否忽略列表顺序
            
        Returns:
            AssertionResult: 断言结果
        """
        content = response.get('content')
        
        # 尝试解析JSON字符串
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                error_msg = message or f"响应内容不是有效的JSON: {content}"
                result = AssertionResult(
                    success=False,
                    message=error_msg,
                    actual_value=content,
                    expected_value=expected_data,
                    assertion_type="assert_json_contains"
                )
                self._assertion_history.append(result)
                logger.error(error_msg)
                return result
        
        # 确保content是字典类型
        if not isinstance(content, dict):
            error_msg = message or f"响应内容不是JSON对象: {content}"
            result = AssertionResult(
                success=False,
                message=error_msg,
                actual_value=content,
                expected_value=expected_data,
                assertion_type="assert_json_contains"
            )
            self._assertion_history.append(result)
            logger.error(error_msg)
            return result
        
        # 递归检查期望的数据是否都在实际数据中
        def check_contains(actual: Any, expected: Any, path: str = "") -> tuple[bool, Optional[str]]:
            if isinstance(expected, dict):
                for key, value in expected.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if key not in actual:
                        return False, f"键 '{current_path}' 不存在"
                    
                    if isinstance(value, dict):
                        result, missing = check_contains(actual[key], value, current_path)
                        if not result:
                            return False, missing
                    elif isinstance(value, list) and isinstance(actual[key], list):
                        if ignore_order:
                            # 对于列表，检查每个元素是否都在actual列表中
                            for expected_item in value:
                                found = False
                                for actual_item in actual[key]:
                                    if isinstance(expected_item, (dict, list)):
                                        item_result, _ = check_contains(actual_item, expected_item)
                                        found = item_result
                                    else:
                                        found = actual_item == expected_item
                                    
                                    if found:
                                        break
                                
                                if not found:
                                    return False, f"列表 '{current_path}' 中缺少元素: {expected_item}"
                        else:
                            # 保持顺序比较
                            if len(expected) > len(actual[key]):
                                return False, f"列表 '{current_path}' 长度不匹配: 期望至少 {len(expected)}，实际 {len(actual[key])}"
                            
                            for i, expected_item in enumerate(expected):
                                item_path = f"{current_path}[{i}]"
                                if i < len(actual[key]):
                                    if isinstance(expected_item, (dict, list)):
                                        item_result, missing = check_contains(actual[key][i], expected_item, item_path)
                                        if not item_result:
                                            return False, missing
                                    elif actual[key][i] != expected_item:
                                        return False, f"{item_path}: 期望 {expected_item}，实际 {actual[key][i]}"
                    elif actual[key] != value:
                        return False, f"{current_path}: 期望 {value}，实际 {actual[key]}"
            elif isinstance(expected, list):
                # 如果expected是列表但actual不是列表
                if not isinstance(actual, list):
                    return False, f"路径 '{path}' 期望是列表，但实际是 {type(actual)}"
                    
                # 其他列表比较逻辑可以在这里扩展
                if ignore_order:
                    # 检查expected中的每个元素是否在actual中
                    for expected_item in expected:
                        found = False
                        for actual_item in actual:
                            if isinstance(expected_item, (dict, list)):
                                item_result, _ = check_contains(actual_item, expected_item)
                                found = item_result
                            else:
                                found = actual_item == expected_item
                            
                            if found:
                                break
                        
                        if not found:
                            return False, f"列表 '{path}' 中缺少元素: {expected_item}"
                else:
                    # 保持顺序比较
                    if len(expected) != len(actual):
                        return False, f"列表 '{path}' 长度不匹配: 期望 {len(expected)}，实际 {len(actual)}"
                    
                    for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
                        item_path = f"{path}[{i}]"
                        if isinstance(exp_item, (dict, list)):
                            item_result, missing = check_contains(act_item, exp_item, item_path)
                            if not item_result:
                                return False, missing
                        elif exp_item != act_item:
                            return False, f"{item_path}: 期望 {exp_item}，实际 {act_item}"
            else:
                # 基本类型比较
                if actual != expected:
                    return False, f"{path}: 期望 {expected}，实际 {actual}"
            
            return True, None
        
        result, missing = check_contains(content, expected_data)
        if not result:
            error_msg = message or f"JSON响应缺少或不匹配: {missing}"
        else:
            error_msg = ""
        
        assertion_result = AssertionResult(
            success=result,
            message=error_msg if not result else "",
            actual_value=content,
            expected_value=expected_data,
            assertion_type="assert_json_contains"
        )
        
        self._assertion_history.append(assertion_result)
        
        if not result:
            logger.error(error_msg)
        
        return assertion_result
    
    def assert_json_path(self, response: Dict[str, Any], json_path: str, expected_value: Any, 
                        message: str = "", ignore_order: bool = False, approx: bool = False, 
                        tolerance: float = 0.01) -> AssertionResult:
        """
        使用JSON Path断言响应中的特定值
        
        Args:
            response: 响应对象，包含content字段
            json_path: JSON Path表达式
            expected_value: 期望的值
            message: 自定义错误消息
            ignore_order: 是否忽略列表顺序
            approx: 是否进行近似比较
            tolerance: 近似比较的容差
            
        Returns:
            AssertionResult: 断言结果
        """
        content = response.get('content')
        
        # 尝试解析JSON字符串
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                error_msg = message or f"响应内容不是有效的JSON: {content}"
                result = AssertionResult(
                    success=False,
                    message=error_msg,
                    actual_value=content,
                    expected_value=expected_value,
                    assertion_type="assert_json_path"
                )
                self._assertion_history.append(result)
                logger.error(error_msg)
                return result
        
        # 简单的JSON Path解析实现
        # 支持基本的点表示法和数组索引
        def get_value_by_path(data: Any, path: str) -> Any:
            parts = path.strip().split('.')
            current = data
            
            for part in parts:
                # 处理数组索引
                array_match = re.match(r'(\w+)\[(\d+)\]', part)
                if array_match:
                    array_name, index = array_match.groups()
                    if isinstance(current, dict) and array_name in current:
                        array = current[array_name]
                        if isinstance(array, list) and 0 <= int(index) < len(array):
                            current = array[int(index)]
                        else:
                            return None
                    else:
                        return None
                # 处理普通字段
                elif isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            
            return current
        
        actual_value = get_value_by_path(content, json_path)
        
        # 如果没找到值
        if actual_value is None:
            # 检查是否真的不存在，还是值就是None
            if not self._path_exists(content, json_path):
                error_msg = message or f"JSON Path '{json_path}' 在响应中不存在"
                result = AssertionResult(
                    success=False,
                    message=error_msg,
                    actual_value=None,
                    expected_value=expected_value,
                    assertion_type="assert_json_path"
                )
                self._assertion_history.append(result)
                logger.error(error_msg)
                return result
        
        # 使用assert_equal进行值比较
        compare_result = self.assert_equal(
            actual_value, 
            expected_value, 
            message=message,
            ignore_order=ignore_order,
            approx=approx,
            tolerance=tolerance
        )
        
        # 更新断言类型
        compare_result.assertion_type = "assert_json_path"
        
        return compare_result
    
    def _path_exists(self, data: Any, path: str) -> bool:
        """
        检查JSON Path是否存在
        """
        parts = path.strip().split('.')
        current = data
        
        for part in parts:
            # 处理数组索引
            array_match = re.match(r'(\w+)\[(\d+)\]', part)
            if array_match:
                array_name, index = array_match.groups()
                if isinstance(current, dict) and array_name in current:
                    array = current[array_name]
                    if isinstance(array, list) and 0 <= int(index) < len(array):
                        current = array[int(index)]
                    else:
                        return False
                else:
                    return False
            # 处理普通字段
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        
        return True
    
    def assert_length(self, actual: Any, expected_length: int, message: str = "") -> AssertionResult:
        """
        断言长度
        
        Args:
            actual: 实际值（支持len()的对象）
            expected_length: 期望的长度
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        try:
            actual_length = len(actual)
            success = actual_length == expected_length
            error_msg = message or f"长度不匹配: 期望 {expected_length}，实际 {actual_length}"
        except (TypeError, AttributeError):
            success = False
            error_msg = message or f"无法获取 {actual} 的长度"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual,
            expected_value=expected_length,
            assertion_type="assert_length"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_greater_than(self, actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """
        断言大于
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        try:
            success = actual > expected
            error_msg = message or f"不大于: 期望 {actual} > {expected}"
        except (TypeError, ValueError):
            success = False
            error_msg = message or f"无法比较 {actual} 和 {expected}"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual,
            expected_value=expected,
            assertion_type="assert_greater_than"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_less_than(self, actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """
        断言小于
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        try:
            success = actual < expected
            error_msg = message or f"不小于: 期望 {actual} < {expected}"
        except (TypeError, ValueError):
            success = False
            error_msg = message or f"无法比较 {actual} 和 {expected}"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual,
            expected_value=expected,
            assertion_type="assert_less_than"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_greater_or_equal(self, actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """
        断言大于等于
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        try:
            success = actual >= expected
            error_msg = message or f"不大于等于: 期望 {actual} >= {expected}"
        except (TypeError, ValueError):
            success = False
            error_msg = message or f"无法比较 {actual} 和 {expected}"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual,
            expected_value=expected,
            assertion_type="assert_greater_or_equal"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_less_or_equal(self, actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """
        断言小于等于
        
        Args:
            actual: 实际值
            expected: 期望值
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        try:
            success = actual <= expected
            error_msg = message or f"不小于等于: 期望 {actual} <= {expected}"
        except (TypeError, ValueError):
            success = False
            error_msg = message or f"无法比较 {actual} 和 {expected}"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual,
            expected_value=expected,
            assertion_type="assert_less_or_equal"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_between(self, actual: Any, min_value: Any, max_value: Any, message: str = "") -> AssertionResult:
        """
        断言在范围内
        
        Args:
            actual: 实际值
            min_value: 最小值
            max_value: 最大值
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        try:
            success = min_value <= actual <= max_value
            error_msg = message or f"不在范围内: 期望 {min_value} <= {actual} <= {max_value}"
        except (TypeError, ValueError):
            success = False
            error_msg = message or f"无法比较 {actual} 和范围 [{min_value}, {max_value}]"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual,
            expected_value=f"[{min_value}, {max_value}]",
            assertion_type="assert_between"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_type(self, actual: Any, expected_type: type, message: str = "") -> AssertionResult:
        """
        断言类型
        
        Args:
            actual: 实际值
            expected_type: 期望的类型
            message: 自定义错误消息
            
        Returns:
            AssertionResult: 断言结果
        """
        success = isinstance(actual, expected_type)
        error_msg = message or f"类型不匹配: 期望 {expected_type.__name__}，实际 {type(actual).__name__}"
        
        result = AssertionResult(
            success=success,
            message=error_msg if not success else "",
            actual_value=actual,
            expected_value=expected_type.__name__,
            assertion_type="assert_type"
        )
        
        self._assertion_history.append(result)
        
        if not success:
            logger.error(error_msg)
        
        return result
    
    def assert_custom(self, name: str, *args, **kwargs) -> AssertionResult:
        """
        执行自定义断言
        
        Args:
            name: 自定义断言名称
            *args: 传递给自定义断言的位置参数
            **kwargs: 传递给自定义断言的关键字参数
            
        Returns:
            AssertionResult: 断言结果
        """
        if name not in self._custom_assertions:
            error_msg = f"未找到自定义断言: {name}"
            result = AssertionResult(
                success=False,
                message=error_msg,
                actual_value=None,
                expected_value=None,
                assertion_type="assert_custom"
            )
            self._assertion_history.append(result)
            logger.error(error_msg)
            return result
        
        try:
            success, message = self._custom_assertions[name](*args, **kwargs)
            result = AssertionResult(
                success=success,
                message=message if not success else "",
                actual_value=None,
                expected_value=None,
                assertion_type=f"assert_custom_{name}"
            )
            
            self._assertion_history.append(result)
            
            if not success:
                logger.error(message)
            
            return result
        except Exception as e:
            error_msg = f"执行自定义断言 '{name}' 时出错: {str(e)}"
            result = AssertionResult(
                success=False,
                message=error_msg,
                actual_value=None,
                expected_value=None,
                assertion_type="assert_custom"
            )
            self._assertion_history.append(result)
            logger.error(error_msg)
            return result
    
    def run_assertions(self, assertions: List[Dict[str, Any]], response: Dict[str, Any]) -> List[AssertionResult]:
        """
        批量执行断言
        
        Args:
            assertions: 断言配置列表
            response: 响应对象
            
        Returns:
            List[AssertionResult]: 断言结果列表
        """
        results = []
        
        for assertion in assertions:
            assertion_type = assertion.get("type")
            
            if assertion_type == "status_code":
                result = self.assert_status_code(
                    response, 
                    assertion.get("expected"),
                    message=assertion.get("message", "")
                )
            elif assertion_type == "json_contains":
                result = self.assert_json_contains(
                    response,
                    assertion.get("expected"),
                    message=assertion.get("message", ""),
                    ignore_order=assertion.get("ignore_order", False)
                )
            elif assertion_type == "json_path":
                result = self.assert_json_path(
                    response,
                    assertion.get("path"),
                    assertion.get("expected"),
                    message=assertion.get("message", ""),
                    ignore_order=assertion.get("ignore_order", False),
                    approx=assertion.get("approx", False),
                    tolerance=assertion.get("tolerance", 0.01)
                )
            elif assertion_type == "contains":
                # 假设assertion["field"]是响应中的字段路径
                # 简化实现，实际可能需要更复杂的字段提取逻辑
                content = response.get("content", {})
                actual_value = content
                if isinstance(assertion.get("field"), str):
                    # 简单的点符号解析
                    for part in assertion["field"].split("."):
                        if isinstance(actual_value, dict) and part in actual_value:
                            actual_value = actual_value[part]
                        else:
                            actual_value = None
                            break
                
                result = self.assert_contains(
                    actual_value,
                    assertion.get("expected"),
                    message=assertion.get("message", "")
                )
            elif assertion_type == "regex":
                # 类似contains的字段提取
                content = response.get("content", {})
                actual_value = content
                if isinstance(assertion.get("field"), str):
                    for part in assertion["field"].split("."):
                        if isinstance(actual_value, dict) and part in actual_value:
                            actual_value = actual_value[part]
                        else:
                            actual_value = None
                            break
                
                result = self.assert_regex(
                    actual_value,
                    assertion.get("pattern"),
                    message=assertion.get("message", "")
                )
            elif assertion_type.startswith("custom_"):
                # 执行自定义断言
                custom_name = assertion_type[7:]  # 移除"custom_"前缀
                result = self.assert_custom(
                    custom_name,
                    response,
                    assertion.get("expected"),
                    **{k: v for k, v in assertion.items() if k not in ["type", "expected"]}
                )
            else:
                # 不支持的断言类型
                result = AssertionResult(
                    success=False,
                    message=f"不支持的断言类型: {assertion_type}",
                    actual_value=None,
                    expected_value=None,
                    assertion_type=assertion_type
                )
                logger.error(result.message)
            
            results.append(result)
        
        return results
    
    def get_assertion_history(self) -> List[Dict[str, Any]]:
        """
        获取断言历史记录
        
        Returns:
            List[Dict[str, Any]]: 断言历史列表
        """
        return [result.to_dict() for result in self._assertion_history]
    
    def clear_history(self) -> None:
        """
        清除断言历史记录
        """
        self._assertion_history = []


# 全局断言管理器实例
assert_manager = AssertionManager()


def register_assertion(name: str, assertion_func: Callable) -> None:
    """
    注册自定义断言函数的便捷方法
    
    Args:
        name: 断言函数名称
        assertion_func: 断言函数
    """
    assert_manager.register_assertion(name, assertion_func)


def verify_assertions(response: Dict[str, Any], assertions: List[Dict[str, Any]]) -> bool:
    """
    验证断言的便捷方法
    
    Args:
        response: 响应对象
        assertions: 断言配置列表
        
    Returns:
        bool: 是否所有断言都通过
    """
    results = assert_manager.run_assertions(assertions, response)
    return all(result.success for result in results)


# 示例用法
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 模拟响应
    mock_response = {
        "status_code": 200,
        "content": {
            "code": 0,
            "message": "success",
            "data": {
                "user_id": 123,
                "username": "test_user",
                "roles": ["admin", "user"],
                "profile": {
                    "age": 30,
                    "email": "test@example.com"
                }
            }
        }
    }
    
    # 基本断言示例
    print("=== 基本断言示例 ===")
    result1 = assert_manager.assert_status_code(mock_response, 200)
    print(f"状态码断言: {'通过' if result1.success else '失败'}")
    
    # JSON包含断言
    result2 = assert_manager.assert_json_contains(
        mock_response, 
        {"code": 0, "message": "success"}
    )
    print(f"JSON包含断言: {'通过' if result2.success else '失败'}")
    
    # JSON Path断言
    result3 = assert_manager.assert_json_path(
        mock_response, 
        "data.user_id", 
        123
    )
    print(f"JSON Path断言: {'通过' if result3.success else '失败'}")
    
    # 注册自定义断言
    def custom_assertion_example(response, expected):
        # 检查响应中的特定条件
        content = response.get('content', {})
        user_id = content.get('data', {}).get('user_id')
        success = isinstance(user_id, int) and user_id > 0
        message = f"用户ID无效: {user_id}" if not success else ""
        return success, message
    
    register_assertion("valid_user_id", custom_assertion_example)
    
    # 使用自定义断言
    result4 = assert_manager.assert_custom("valid_user_id", mock_response)
    print(f"自定义断言: {'通过' if result4.success else '失败'}")
    
    # 批量断言
    print("\n=== 批量断言示例 ===")
    assertions = [
        {"type": "status_code", "expected": 200},
        {"type": "json_contains", "expected": {"message": "success"}},
        {"type": "json_path", "path": "data.username", "expected": "test_user"},
        {"type": "custom_valid_user_id", "expected": True}
    ]
    
    all_passed = verify_assertions(mock_response, assertions)
    print(f"所有断言是否通过: {all_passed}")
    
    # 打印断言历史
    print("\n=== 断言历史 ===")
    history = assert_manager.get_assertion_history()
    for i, item in enumerate(history):
        print(f"{i+1}. {item['assertion_type']}: {'通过' if item['success'] else '失败'}")
        if not item['success']:
            print(f"   错误: {item['message']}")