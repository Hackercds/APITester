"""
基础工具类，提供参数提取、替换等通用功能
"""
import json
import re
from typing import Any, Dict, List, Union
from string import Template


class BaseUtil:
    """基础工具类"""
    
    # 参数匹配正则表达式
    PARAM_PATTERN = r'\${(.*?)}'
    
    @staticmethod
    def find_params(data: Union[Dict, List, str]) -> List[str]:
        """
        从数据中提取参数占位符
        
        Args:
            data: 待提取参数的数据（字典、列表或字符串）
            
        Returns:
            List[str]: 提取到的参数名列表
        """
        # 将数据转换为字符串
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data)
        elif isinstance(data, str):
            data_str = data
        else:
            raise TypeError(f"Unsupported data type: {type(data)}")
        
        # 使用正则表达式提取参数
        return re.findall(BaseUtil.PARAM_PATTERN, data_str)
    
    @staticmethod
    def replace_params(original_data: Union[Dict, List, str], 
                      replace_data: Dict[str, Any]) -> Union[Dict, List, str]:
        """
        替换数据中的参数占位符
        
        Args:
            original_data: 原始数据（字典、列表或字符串）
            replace_data: 参数替换字典
            
        Returns:
            Union[Dict, List, str]: 替换后的原始类型数据
        """
        # 保存原始数据类型
        original_type = type(original_data)
        
        # 将数据转换为字符串
        if isinstance(original_data, (dict, list)):
            data_str = json.dumps(original_data)
        elif isinstance(original_data, str):
            data_str = original_data
        else:
            raise TypeError(f"Unsupported data type: {type(original_data)}")
        
        # 使用Template进行参数替换
        template = Template(data_str)
        replaced_str = template.safe_substitute(replace_data)
        
        # 如果原始数据是字典或列表，需要转换回原始类型
        if isinstance(original_data, (dict, list)):
            try:
                return json.loads(replaced_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse replaced data: {e}")
        
        return replaced_str
    
    @staticmethod
    def deep_get(data: Dict, keys: str, default: Any = None) -> Any:
        """
        深度获取字典嵌套值
        
        Args:
            data: 字典数据
            keys: 点分隔的键路径，如 'user.info.name'
            default: 默认值
            
        Returns:
            Any: 获取的值或默认值
        """
        keys_list = keys.split('.')
        result = data
        
        for key in keys_list:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return default
        
        return result


# 为了向后兼容，保留原有的函数名称
find = BaseUtil.find_params


def replace(ori_data, replace_data):
    """向后兼容的替换函数"""
    return BaseUtil.replace_params(ori_data, replace_data)


# 测试代码
if __name__ == '__main__':
    # 测试参数提取
    params = BaseUtil.find_params({"id": "${id_name}", "title": "test", "data": ["${item1}", "${item2}"]})
    print(f"提取的参数: {params}")
    
    # 测试参数替换
    original = {"authorization": "Bearer ${token}", "user": {"name": "${username}"}}
    replace_dict = {'token': 'abc123', 'username': 'testuser'}
    replaced = BaseUtil.replace_params(original, replace_dict)
    print(f"替换后的结果: {replaced}")
    
    # 测试深度获取
    data = {"user": {"info": {"name": "John", "age": 30}}}
    name = BaseUtil.deep_get(data, "user.info.name")
    print(f"深度获取的值: {name}")
