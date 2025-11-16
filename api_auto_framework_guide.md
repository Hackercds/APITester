# API自动化测试框架使用指南

## 目录
- [1. 框架概述](#1-框架概述)
- [2. 安装方法](#2-安装方法)
- [3. 环境要求](#3-环境要求)
- [4. 配置步骤](#4-配置步骤)
- [5. 测试用例结构](#5-测试用例结构)
- [6. 测试用例导入方式](#6-测试用例导入方式)
- [7. 手动创建测试用例](#7-手动创建测试用例)
- [8. 运行测试用例](#8-运行测试用例)
- [9. 框架核心功能](#9-框架核心功能)
- [10. 文件组织规范](#10-文件组织规范)
- [11. 最佳实践](#11-最佳实践)
- [12. 常见问题](#12-常见问题)

## 1. 框架概述

API自动化测试框架是一个功能全面的接口测试工具，支持HTTP/HTTPS请求、同步/异步API测试、大模型API测试、数据库操作、参数关联等特性。框架基于Python开发，使用pytest作为测试运行器，提供了灵活的测试用例管理和执行功能。

### 主要特性：
- 支持各种HTTP方法（GET、POST、PUT、DELETE等）
- 提供同步和异步API测试能力
- 内置多种认证方式（Basic Auth、Token Auth、HMAC等）
- 支持参数化测试和数据驱动
- 提供丰富的断言方法
- 支持测试用例关联和动态参数
- 支持数据库操作和验证
- 提供完整的日志记录和报告生成
- 支持性能测试和并发测试
- 支持大模型API测试

## 2. 安装方法

框架提供两种安装方式：源码安装和直接使用。

### 2.1 源码安装

```bash
# 克隆或下载项目源码
cd d:\DDDD\接口自动化框架

# 安装依赖
pip install -r requirements.txt

# 安装框架本身
pip install -e .
```

### 2.2 直接使用

如果不需要安装到系统中，可以直接在项目目录下使用：

```bash
# 进入项目目录
cd d:\DDDD\接口自动化框架

# 安装依赖
pip install -r requirements.txt
```

## 3. 环境要求

- **Python版本**：Python 3.8 或更高版本
- **依赖包**：
  - requests>=2.32.0
  - aiohttp>=3.10.0
  - pytest>=8.1.1
  - pytest-html>=4.1.1
  - pymysql>=1.1.0
  - sqlalchemy>=2.0.23
  - PyYAML>=6.0.1
  - pandas>=2.1.0
  - openai>=1.2.0 (可选，用于大模型API测试)
  - azure-ai-openai>=1.0.0 (可选，用于Azure大模型API测试)

## 4. 配置步骤

### 4.1 环境变量配置

框架使用`.env`文件管理环境变量。复制`.env.example`文件并根据实际情况修改：

```bash
# 复制配置文件示例
copy .env.example .env
```

编辑`.env`文件，配置以下内容：

```dotenv
# 数据库连接信息
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456
DB_NAME=test_db

# API配置
API_BASE_URL=http://httpbin.org
API_TIMEOUT=30
API_RETRY_COUNT=3
API_RETRY_DELAY=1

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=./logs

# 测试配置
DEFAULT_PROJECT=okr-api
MAX_WORKERS=10
```

### 4.2 配置文件说明

框架主要通过`config/settings.py`管理配置。配置项包括：

- 路径配置：日志、测试报告、临时文件路径
- 数据库配置：连接参数、超时设置
- 日志配置：级别、格式、输出方式
- API配置：基础URL、超时、重试参数
- 测试配置：并发数、默认项目等

## 5. 测试用例结构

框架支持多种测试用例定义方式，主要包括：

### 5.1 基于类的测试用例

继承`BaseTestCase`类，实现测试逻辑：

```python
from testcase.base_test_cases import BaseTestCase

class MyAPITest(BaseTestCase):
    def __init__(self, name="MyAPI测试", description="测试我的API功能"):
        super().__init__(name, description)
    
    def execute(self):
        # 发送请求
        response = self.http_client.get("/api/endpoint")
        
        # 验证响应
        self.assert_status_code(response, 200)
        self.assert_json_contains(response, {"status": "success"})
```

### 5.2 基于Pytest的测试用例

使用Pytest装饰器定义测试用例：

```python
import pytest
from utils.requestsutil import RequestsUtil

class TestMyAPI:
    @pytest.fixture(scope='class')
    def setup_class(self):
        self.request_util = RequestsUtil(base_url="http://httpbin.org")
    
    def test_get_endpoint(self, setup_class):
        response = self.request_util.get("/get")
        assert response.status_code == 200
```

### 5.3 数据驱动测试用例

使用参数化装饰器进行数据驱动测试：

```python
@pytest.mark.parametrize('status_code, description', [
    (200, 'OK'),
    (400, 'Bad Request'),
    (404, 'Not Found')
])
def test_status_codes(status_code, description):
    response = request_util.get(f'/status/{status_code}')
    assert response.status_code == status_code
```

## 6. 测试用例导入方式

框架支持多种测试用例导入方式：

### 6.1 从JSON文件导入

使用`TestCaseManager`从JSON文件导入测试用例：

```python
from utils.testcasemanager import TestCaseManager

manager = TestCaseManager()
manager.import_from_json("test_cases.json")
```

### 6.2 从YAML文件导入

```python
manager.import_from_yaml("test_cases.yaml")
```

### 6.3 从Excel文件导入

```python
manager.import_from_excel("test_cases.xlsx")
```

### 6.4 从数据库加载

框架支持从数据库加载测试用例，这是最常用的方式：

```python
from utils.readmysql import RdTestcase

# 初始化测试用例读取器
case_reader = RdTestcase()

# 加载特定项目的测试用例
case_list = case_reader.is_run_data('okr-api')
```

## 7. 手动创建测试用例

### 7.1 创建基本测试用例

```python
# 方式1：直接使用TestCaseManager创建
test_case_data = {
    "title": "测试用户登录",
    "url": "/api/login",
    "method": "POST",
    "headers": '{"Content-Type": "application/json"}',
    "request_body": '{"username": "test", "password": "123456"}',
    "expected_code": 200,
    "relation": "token=headers.authorization"
}

manager.create_test_case("login_001", test_case_data)

# 方式2：编写Pytest测试用例文件
# 创建 test_my_api.py 文件
```

### 7.2 测试用例模板

#### 基础HTTP测试模板

```python
import pytest
from utils.requestsutil import RequestsUtil
from utils.logutil import Logger

logger = Logger('my_api_test')
request_util = RequestsUtil(base_url="http://httpbin.org")

class TestMyAPI:
    @pytest.fixture(scope='class')
    def setup_class(self):
        logger.info('开始执行测试')
        yield
        logger.info('测试执行完成')
    
    def test_get_request(self, setup_class):
        # 发送GET请求
        response = request_util.get('/get', params={'key': 'value'})
        
        # 验证响应
        assert response.status_code == 200
        assert 'key' in response.json()['args']
        
        logger.info('GET请求测试通过')
    
    def test_post_request(self, setup_class):
        # 发送POST请求
        data = {'name': 'test', 'value': 123}
        response = request_util.post('/post', json=data)
        
        # 验证响应
        assert response.status_code == 200
        assert response.json()['json']['name'] == 'test'
        
        logger.info('POST请求测试通过')

if __name__ == '__main__':
    pytest.main(['-v', __file__])
```

#### 带参数关联的测试模板

```python
import pytest
from utils.requestsutil import RequestsUtil
from config.settings import DynamicParam

request_util = RequestsUtil()
dynamic_params = DynamicParam()

class TestWithCorrelation:
    def test_login_and_get_user_info(self):
        # 1. 登录获取token
        login_data = {'username': 'test', 'password': '123456'}
        login_response = request_util.post('/login', json=login_data)
        
        # 提取token并存储
        token = login_response.json().get('token')
        dynamic_params.set('auth_token', token)
        
        # 2. 使用token获取用户信息
        headers = {'Authorization': f'Bearer ${auth_token}'}  # 使用${变量名}格式引用动态参数
        user_response = request_util.get('/user/info', headers=headers)
        
        # 验证响应
        assert user_response.status_code == 200
```

## 8. 运行测试用例

### 8.1 使用Pytest运行

```bash
# 运行特定文件
pytest testcase/example.py -v

# 运行特定目录
pytest testcase/ -v

# 生成HTML报告
pytest testcase/ -v --html=report.html
```

### 8.2 使用测试运行器

框架提供了专门的测试运行器：

```python
from testcase.test_runner import TestRunner

# 初始化测试运行器
runner = TestRunner(project_name='okr-api')

# 加载并运行测试用例
case_list = runner.load_test_cases()
for case in case_list:
    result = runner.process_test_case(case)
    print(f"测试结果: {result['status']}")

# 生成报告
report = runner.generate_report()
```

### 8.3 使用命令行工具

框架提供了命令行入口：

```bash
# 使用api-test命令运行测试
api-test --project okr-api --report report.html
```

## 9. 框架核心功能

### 9.1 HTTP请求功能

框架提供了功能强大的HTTP客户端，支持各种请求方式：

```python
from utils.requestsutil import HttpClient

# 初始化HTTP客户端
client = HttpClient(base_url="http://httpbin.org")

# 发送GET请求
response = client.get("/get", params={"key": "value"})

# 发送POST请求
response = client.post("/post", json={"name": "test"})

# 发送带认证的请求
response = client.get("/protected", auth=("user", "pass"))
```

### 9.2 参数关联功能

框架支持测试用例间的参数关联，使用`${变量名}`格式引用动态参数：

```python
from common import BaseUtil
from config.settings import DynamicParam

dynamic_params = DynamicParam()

# 存储动态参数
dynamic_params.set("token", "abc123")

# 在请求中使用动态参数
headers = {"Authorization": "Bearer ${token}"}
processed_headers = BaseUtil.replace_params(headers, dynamic_params.get_all())
```

### 9.3 数据库操作

框架提供了数据库操作工具：

```python
from utils.mysqlutil import DatabaseUtil

db_util = DatabaseUtil()

# 执行查询
results = db_util.query("SELECT * FROM users WHERE id = %s", (1,))

# 执行更新
db_util.execute("UPDATE users SET name = %s WHERE id = %s", ("test", 1))

# 事务处理
with db_util.get_connection() as conn:
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name) VALUES (%s)", ("new_user",))
        cursor.execute("UPDATE stats SET count = count + 1")
        conn.commit()
    except:
        conn.rollback()
```

### 9.4 日志功能

框架提供了灵活的日志记录功能：

```python
from utils.logutil import Logger

# 初始化日志记录器
logger = Logger("my_test", level="INFO")

# 记录日志
logger.info("测试开始")
logger.debug("调试信息")
logger.warning("警告信息")
logger.error("错误信息")
```

## 10. 文件组织规范

框架推荐的文件组织结构：

```
接口自动化框架/
├── common/                # 通用组件和工具
│   ├── Base.py           # 基础工具类
│   ├── decorators.py     # 装饰器
│   └── exceptions.py     # 自定义异常
├── config/                # 配置文件
│   ├── __init__.py
│   └── settings.py       # 配置管理
├── testcase/              # 测试用例
│   ├── __init__.py
│   ├── base_test_cases.py # 基础测试用例类
│   ├── example.py        # 示例测试用例
│   ├── test_run.py       # 测试运行入口
│   └── test_runner.py    # 测试运行器
├── utils/                 # 工具类
│   ├── __init__.py
│   ├── requestsutil.py   # HTTP请求工具
│   ├── logutil.py        # 日志工具
│   ├── mysqlutil.py      # 数据库工具
│   └── testcasemanager.py # 测试用例管理
├── .env                   # 环境变量
├── .env.example          # 环境变量示例
├── requirements.txt      # 依赖包
├── setup.py              # 安装配置
└── README.md             # 说明文档
```

## 11. 最佳实践

### 11.1 测试用例设计

- **独立性**：每个测试用例应尽量独立，避免强依赖
- **可维护性**：使用描述性的测试用例名称
- **数据隔离**：测试数据与测试代码分离
- **断言明确**：使用明确的断言，包含详细的失败信息

### 11.2 参数化和数据驱动

- 对相同接口的不同场景使用参数化测试
- 将测试数据存储在外部文件或数据库中
- 使用动态参数处理接口依赖

### 11.3 错误处理和重试

- 使用装饰器处理重试逻辑
- 对预期的错误进行适当的捕获和断言
- 记录详细的错误信息以便调试

```python
from common.decorators import retry

@retry(max_attempts=3, delay=1)
def test_flaky_endpoint():
    response = request_util.get("/flaky-endpoint")
    assert response.status_code == 200
```

### 11.4 报告和监控

- 生成详细的测试报告
- 监控测试执行状态
- 分析测试结果和趋势

## 12. 常见问题

### 12.1 动态参数不生效

**问题**：在请求中使用`${变量名}`格式的动态参数，但没有被正确替换

**解决方案**：
1. 确保已正确设置动态参数：`dynamic_params.set("变量名", "值")`
2. 检查参数引用格式是否正确：`${变量名}`
3. 确保在发送请求前进行了参数替换

### 12.2 数据库连接失败

**问题**：无法连接到数据库

**解决方案**：
1. 检查`.env`文件中的数据库配置是否正确
2. 确保数据库服务正在运行
3. 检查网络连接和防火墙设置

### 12.3 测试用例执行顺序

**问题**：需要确保测试用例按特定顺序执行

**解决方案**：
1. 使用pytest的依赖标记：`@pytest.mark.dependency(depends=["test_other"])`
2. 对于有强依赖的测试，考虑在一个测试方法中执行多个步骤
3. 使用BatchTestCase类管理测试用例执行顺序

### 12.4 性能问题

**问题**：测试执行速度慢

**解决方案**：
1. 减少不必要的请求和断言
2. 使用适当的并发执行（注意线程安全）
3. 对频繁使用的数据进行缓存
4. 使用`@cache_result`装饰器缓存函数结果