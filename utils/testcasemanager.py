import json
import yaml
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import pandas as pd

class TestCaseManager:
    """
    测试用例管理类，提供测试用例的创建、读取、更新、删除以及导入导出功能
    """
    def __init__(self, storage_dir: str = "./test_cases"):
        """
        初始化测试用例管理器
        
        Args:
            storage_dir: 测试用例存储目录
        """
        self.storage_dir = storage_dir
        self.test_cases = {}
        self.test_suites = {}
        
        # 确保存储目录存在
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        
        # 加载已有的测试用例
        self._load_existing_cases()
    
    def _load_existing_cases(self):
        """
        加载存储目录中已有的测试用例
        """
        try:
            # 加载JSON格式的测试用例
            json_cases_path = os.path.join(self.storage_dir, "test_cases.json")
            if os.path.exists(json_cases_path):
                with open(json_cases_path, 'r', encoding='utf-8') as f:
                    self.test_cases = json.load(f)
            
            # 加载测试套件配置
            suites_path = os.path.join(self.storage_dir, "test_suites.json")
            if os.path.exists(suites_path):
                with open(suites_path, 'r', encoding='utf-8') as f:
                    self.test_suites = json.load(f)
        except Exception as e:
            print(f"加载现有测试用例时出错: {e}")
    
    def save_cases(self):
        """
        保存测试用例到文件
        """
        try:
            # 保存测试用例
            json_cases_path = os.path.join(self.storage_dir, "test_cases.json")
            with open(json_cases_path, 'w', encoding='utf-8') as f:
                json.dump(self.test_cases, f, ensure_ascii=False, indent=2)
            
            # 保存测试套件
            suites_path = os.path.join(self.storage_dir, "test_suites.json")
            with open(suites_path, 'w', encoding='utf-8') as f:
                json.dump(self.test_suites, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存测试用例时出错: {e}")
            return False
    
    def create_test_case(self, case_id: str, case_data: Dict[str, Any]) -> bool:
        """
        创建新的测试用例
        
        Args:
            case_id: 测试用例ID
            case_data: 测试用例数据
        
        Returns:
            bool: 是否创建成功
        """
        try:
            # 添加元数据
            case_data['created_at'] = datetime.now().isoformat()
            case_data['updated_at'] = datetime.now().isoformat()
            case_data['status'] = case_data.get('status', 'active')
            
            self.test_cases[case_id] = case_data
            return self.save_cases()
        except Exception as e:
            print(f"创建测试用例时出错: {e}")
            return False
    
    def get_test_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        获取测试用例
        
        Args:
            case_id: 测试用例ID
        
        Returns:
            Dict or None: 测试用例数据或None
        """
        return self.test_cases.get(case_id)
    
    def update_test_case(self, case_id: str, case_data: Dict[str, Any]) -> bool:
        """
        更新测试用例
        
        Args:
            case_id: 测试用例ID
            case_data: 要更新的测试用例数据
        
        Returns:
            bool: 是否更新成功
        """
        if case_id not in self.test_cases:
            return False
        
        try:
            # 更新测试用例，但保留创建时间
            created_at = self.test_cases[case_id].get('created_at')
            case_data['created_at'] = created_at
            case_data['updated_at'] = datetime.now().isoformat()
            
            self.test_cases[case_id] = case_data
            return self.save_cases()
        except Exception as e:
            print(f"更新测试用例时出错: {e}")
            return False
    
    def delete_test_case(self, case_id: str) -> bool:
        """
        删除测试用例
        
        Args:
            case_id: 测试用例ID
        
        Returns:
            bool: 是否删除成功
        """
        if case_id not in self.test_cases:
            return False
        
        try:
            del self.test_cases[case_id]
            
            # 同时从测试套件中移除
            for suite_id, suite in self.test_suites.items():
                if case_id in suite.get('cases', []):
                    suite['cases'].remove(case_id)
            
            return self.save_cases()
        except Exception as e:
            print(f"删除测试用例时出错: {e}")
            return False
    
    def list_test_cases(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        列出测试用例，支持过滤
        
        Args:
            filters: 过滤条件
        
        Returns:
            List: 测试用例列表
        """
        result = []
        
        for case_id, case_data in self.test_cases.items():
            # 添加case_id到数据中
            case_with_id = case_data.copy()
            case_with_id['id'] = case_id
            
            # 应用过滤条件
            if filters:
                match = True
                for key, value in filters.items():
                    if key not in case_with_id or case_with_id[key] != value:
                        match = False
                        break
                if match:
                    result.append(case_with_id)
            else:
                result.append(case_with_id)
        
        return result
    
    def create_test_suite(self, suite_id: str, suite_name: str, case_ids: List[str]) -> bool:
        """
        创建测试套件
        
        Args:
            suite_id: 测试套件ID
            suite_name: 测试套件名称
            case_ids: 测试用例ID列表
        
        Returns:
            bool: 是否创建成功
        """
        try:
            # 验证测试用例是否存在
            for case_id in case_ids:
                if case_id not in self.test_cases:
                    print(f"测试用例 {case_id} 不存在")
                    return False
            
            self.test_suites[suite_id] = {
                'name': suite_name,
                'cases': case_ids,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            return self.save_cases()
        except Exception as e:
            print(f"创建测试套件时出错: {e}")
            return False
    
    def get_test_suite(self, suite_id: str) -> Optional[Dict[str, Any]]:
        """
        获取测试套件
        
        Args:
            suite_id: 测试套件ID
        
        Returns:
            Dict or None: 测试套件数据或None
        """
        suite = self.test_suites.get(suite_id)
        if suite:
            # 获取完整的测试用例数据
            suite_with_cases = suite.copy()
            cases_data = []
            for case_id in suite.get('cases', []):
                if case_id in self.test_cases:
                    case_data = self.test_cases[case_id].copy()
                    case_data['id'] = case_id
                    cases_data.append(case_data)
            suite_with_cases['cases_data'] = cases_data
            return suite_with_cases
        return None
    
    def search_test_cases(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索测试用例
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            List: 符合条件的测试用例列表
        """
        result = []
        pattern = re.compile(keyword, re.IGNORECASE)
        
        for case_id, case_data in self.test_cases.items():
            case_with_id = case_data.copy()
            case_with_id['id'] = case_id
            
            # 搜索所有字符串字段
            for key, value in case_with_id.items():
                if isinstance(value, str) and pattern.search(value):
                    result.append(case_with_id)
                    break
        
        return result
    
    # 导入导出功能
    def import_from_json(self, file_path: str) -> bool:
        """
        从JSON文件导入测试用例
        
        Args:
            file_path: JSON文件路径
        
        Returns:
            bool: 是否导入成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            # 检查是否是测试用例列表
            if isinstance(imported_data, list):
                for case_data in imported_data:
                    case_id = case_data.pop('id', f"imported_{len(self.test_cases) + 1}")
                    self.create_test_case(case_id, case_data)
            # 检查是否是单个测试用例
            elif isinstance(imported_data, dict) and 'test_cases' not in imported_data:
                case_id = imported_data.pop('id', f"imported_{len(self.test_cases) + 1}")
                self.create_test_case(case_id, imported_data)
            # 检查是否是完整的导出格式
            elif isinstance(imported_data, dict) and 'test_cases' in imported_data:
                # 导入测试用例
                for case_id, case_data in imported_data['test_cases'].items():
                    self.create_test_case(case_id, case_data)
                
                # 导入测试套件
                if 'test_suites' in imported_data:
                    for suite_id, suite_data in imported_data['test_suites'].items():
                        self.test_suites[suite_id] = suite_data
                    self.save_cases()
            
            return True
        except Exception as e:
            print(f"从JSON导入测试用例时出错: {e}")
            return False
    
    def import_from_yaml(self, file_path: str) -> bool:
        """
        从YAML文件导入测试用例
        
        Args:
            file_path: YAML文件路径
        
        Returns:
            bool: 是否导入成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = yaml.safe_load(f)
            
            # 处理逻辑与JSON类似
            if isinstance(imported_data, list):
                for case_data in imported_data:
                    case_id = case_data.pop('id', f"imported_{len(self.test_cases) + 1}")
                    self.create_test_case(case_id, case_data)
            elif isinstance(imported_data, dict) and 'test_cases' not in imported_data:
                case_id = imported_data.pop('id', f"imported_{len(self.test_cases) + 1}")
                self.create_test_case(case_id, imported_data)
            elif isinstance(imported_data, dict) and 'test_cases' in imported_data:
                for case_id, case_data in imported_data['test_cases'].items():
                    self.create_test_case(case_id, case_data)
                
                if 'test_suites' in imported_data:
                    for suite_id, suite_data in imported_data['test_suites'].items():
                        self.test_suites[suite_id] = suite_data
                    self.save_cases()
            
            return True
        except Exception as e:
            print(f"从YAML导入测试用例时出错: {e}")
            return False
    
    def import_from_excel(self, file_path: str) -> bool:
        """
        从Excel文件导入测试用例
        
        Args:
            file_path: Excel文件路径
        
        Returns:
            bool: 是否导入成功
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            # 将DataFrame转换为字典列表
            cases_data = df.to_dict('records')
            
            for case_data in cases_data:
                # 清理NaN值
                clean_data = {k: v for k, v in case_data.items() if pd.notna(v)}
                
                # 获取或生成测试用例ID
                case_id = clean_data.pop('id', None)
                if not case_id:
                    case_id = clean_data.pop('case_id', f"imported_{len(self.test_cases) + 1}")
                
                # 将字符串格式的列表、字典转换为实际对象
                for key, value in clean_data.items():
                    if isinstance(value, str):
                        # 尝试转换为JSON
                        if (value.startswith('{') and value.endswith('}')) or \
                           (value.startswith('[') and value.endswith(']')):
                            try:
                                clean_data[key] = json.loads(value)
                            except:
                                pass
                
                self.create_test_case(case_id, clean_data)
            
            return True
        except Exception as e:
            print(f"从Excel导入测试用例时出错: {e}")
            return False
    
    def export_to_json(self, file_path: str, case_ids: Optional[List[str]] = None) -> bool:
        """
        导出测试用例到JSON文件
        
        Args:
            file_path: 导出文件路径
            case_ids: 要导出的测试用例ID列表，None表示导出全部
        
        Returns:
            bool: 是否导出成功
        """
        try:
            export_data = {
                'test_cases': {},
                'test_suites': self.test_suites,
                'export_time': datetime.now().isoformat()
            }
            
            # 导出指定的测试用例或全部测试用例
            if case_ids:
                for case_id in case_ids:
                    if case_id in self.test_cases:
                        export_data['test_cases'][case_id] = self.test_cases[case_id]
            else:
                export_data['test_cases'] = self.test_cases
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"导出测试用例到JSON时出错: {e}")
            return False
    
    def export_to_yaml(self, file_path: str, case_ids: Optional[List[str]] = None) -> bool:
        """
        导出测试用例到YAML文件
        
        Args:
            file_path: 导出文件路径
            case_ids: 要导出的测试用例ID列表，None表示导出全部
        
        Returns:
            bool: 是否导出成功
        """
        try:
            export_data = {
                'test_cases': {},
                'test_suites': self.test_suites,
                'export_time': datetime.now().isoformat()
            }
            
            if case_ids:
                for case_id in case_ids:
                    if case_id in self.test_cases:
                        export_data['test_cases'][case_id] = self.test_cases[case_id]
            else:
                export_data['test_cases'] = self.test_cases
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
            
            return True
        except Exception as e:
            print(f"导出测试用例到YAML时出错: {e}")
            return False
    
    def export_to_excel(self, file_path: str, case_ids: Optional[List[str]] = None) -> bool:
        """
        导出测试用例到Excel文件
        
        Args:
            file_path: 导出文件路径
            case_ids: 要导出的测试用例ID列表，None表示导出全部
        
        Returns:
            bool: 是否导出成功
        """
        try:
            # 准备要导出的测试用例
            cases_to_export = []
            
            if case_ids:
                for case_id in case_ids:
                    if case_id in self.test_cases:
                        case_data = self.test_cases[case_id].copy()
                        case_data['id'] = case_id
                        cases_to_export.append(case_data)
            else:
                for case_id, case_data in self.test_cases.items():
                    data = case_data.copy()
                    data['id'] = case_id
                    cases_to_export.append(data)
            
            # 转换复杂数据类型为字符串
            for case in cases_to_export:
                for key, value in case.items():
                    if isinstance(value, (dict, list)):
                        case[key] = json.dumps(value, ensure_ascii=False)
            
            # 创建DataFrame并导出到Excel
            df = pd.DataFrame(cases_to_export)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 写入Excel文件
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Test Cases')
                
                # 如果有测试套件，也导出
                if self.test_suites:
                    suites_data = []
                    for suite_id, suite in self.test_suites.items():
                        suite_data = suite.copy()
                        suite_data['id'] = suite_id
                        suite_data['cases'] = json.dumps(suite.get('cases', []), ensure_ascii=False)
                        suites_data.append(suite_data)
                    
                    if suites_data:
                        df_suites = pd.DataFrame(suites_data)
                        df_suites.to_excel(writer, index=False, sheet_name='Test Suites')
            
            return True
        except Exception as e:
            print(f"导出测试用例到Excel时出错: {e}")
            return False

# 创建全局测试用例管理器实例
test_case_manager = TestCaseManager()

# 示例用法
def main():
    # 创建测试用例
    test_case = {
        "name": "登录接口测试",
        "description": "测试用户登录功能",
        "url": "http://api.example.com/login",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": {"username": "test_user", "password": "test_pass"},
        "assertions": [
            {"type": "status_code", "expected": 200},
            {"type": "json_path", "path": "$.token", "expected": "not_null"}
        ],
        "priority": "high"
    }
    
    # 创建测试用例
    case_manager = TestCaseManager()
    case_manager.create_test_case("login_test_001", test_case)
    
    # 创建测试套件
    case_manager.create_test_suite("auth_suite", "认证测试套件", ["login_test_001"])
    
    # 导出测试用例
    export_dir = os.path.join(os.getcwd(), "exports")
    os.makedirs(export_dir, exist_ok=True)
    
    case_manager.export_to_json(os.path.join(export_dir, "test_cases.json"))
    case_manager.export_to_yaml(os.path.join(export_dir, "test_cases.yaml"))
    case_manager.export_to_excel(os.path.join(export_dir, "test_cases.xlsx"))
    
    print("测试用例管理示例完成")

if __name__ == "__main__":
    main()