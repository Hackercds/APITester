# 接口自动化测试框架使用指南

## 目录

- [1. 框架概述](#1-框架概述)
- [2. 环境要求](#2-环境要求)
- [3. 框架安装](#3-框架安装)
- [4. 配置说明](#4-配置说明)
  - [4.1 环境变量配置](#41-环境变量配置)
  - [4.2 配置文件结构](#42-配置文件结构)
- [5. 核心功能介绍](#5-核心功能介绍)
  - [5.1 HTTP请求功能](#51-http请求功能)
  - [5.2 认证管理](#52-认证管理)
  - [5.3 数据生成器](#53-数据生成器)
  - [5.4 异步支持](#54-异步支持)
  - [5.5 并发测试](#55-并发测试)
  - [5.6 响应验证](#56-响应验证)
  - [5.7 数据库操作](#57-数据库操作)
  - [5.8 大模型API集成](#58-大模型api集成)
- [6. 测试用例编写](#6-测试用例编写)
  - [6.1 基础测试用例结构](#61-基础测试用例结构)
  - [6.2 常用测试用例类型](#62-常用测试用例类型)
  - [6.3 Pytest集成](#63-pytest集成)
  - [6.4 批量测试](#64-批量测试)
- [7. 文件组织结构](#7-文件组织结构)
- [8. 命令行工具](#8-命令行工具)
- [9. 最佳实践](#9-最佳实践)
- [10. 常见问题解答](#10-常见问题解答)

## 1. 框架概述

接口自动化测试框架是一个功能完备的API测试工具集，提供了从HTTP请求发送、响应验证、认证管理到并发测试等全方位支持。框架具有以下特点：

- 支持同步/异步HTTP请求
- 多种认证方式（Basic、Token、HMAC）
- 强大的响应验证和结果提取功能
- 并发测试支持
- 集成数据库操作
- 支持大模型API（OpenAI、Azure OpenAI等）
- 完整的日志记录
- 与Pytest无缝集成
- 命令行工具支持

## 2. 环境要求

- Python 3.7+
- pip 20.0+

## 3. 框架安装

### 3.1 基础安装

```bash
# 克隆仓库
cd d:\DDDD\接口自动化框架

# 安装依赖
pip install -r requirements.txt

# 安装框架（开发模式）
pip install -e .
```

### 3.2 完整安装（包含所有可选依赖）

```bash
pip install -e "[full]"
```

### 3.3 开发环境安装

```bash
pip install -e "[dev]"
```

## 4. 配置说明

### 4.1 环境变量配置

框架使用`.env`文件管理环境变量。复制`.env.example`并填写实际配置：

```bash
cp .env.example .env
```

`.env`文件包含以下主要配置项：

```dotenv
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=test_db

# API配置
API_BASE_URL=http://api.example.com
API_TIMEOUT=30

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/api_test.log

# 测试配置
DEFAULT_PROJECT=demo_project
```

### 4.2 配置文件结构

框架使用`config/settings.py`管理配置，通过`ConfigManager`类提供统一的配置访问：

```python
from config.settings import config_manager

# 获取API配置
api_config = config_manager.get_api_config()
base_url = api_config.get('base_url')

# 获取数据库配置
db_config = config_manager.get_db_config()

# 获取日志配置
log_config = config_manager.get_log_config()
```

## 5. 核心功能介绍

### 5.1 HTTP请求功能

框架提供多种HTTP请求方式，支持GET、POST、PUT、DELETE等方法：

```python
from utils.requestsutil import RequestsUtil

# 创建请求工具实例
request_util = RequestsUtil()

# 设置基础URL
request_util.set_base_url("https://httpbin.org")

# GET请求
response = request_util.get('/get', params={'test': 'value'})

# POST请求
response = request_util.post('/post', json={'name': 'test'})

# 带请求头的请求
response = request_util.get('/headers', headers={'Authorization': 'Bearer token'})
```

### 5.2 认证管理

框架支持多种认证方式，通过`AuthManager`统一管理：

```python
from utils.authutil import AuthManager

# 创建认证管理器
auth_manager = AuthManager()

# 添加Basic认证
auth_manager.add_basic_auth('user', 'password')

# 添加Token认证
auth_manager.add_token_auth('your_token')

# 添加HMAC认证
auth_manager.add_hmac_auth('access_key', 'secret_key')

# 应用认证到请求工具
request_util.set_auth_manager(auth_manager)
```

### 5.3 数据生成器

框架内置数据生成器，方便创建测试数据：

```python
from utils import DataGenerator

data_generator = DataGenerator()

# 生成随机邮箱
email = data_generator.generate('email')

# 生成随机手机号
mobile = data_generator.generate('mobile')

# 生成随机字符串
text = data_generator.generate('text', length=20)

# 生成随机数字
number = data_generator.generate('integer', min_val=10, max_val=100)
```

### 5.4 异步支持

框架提供异步HTTP请求功能：

```python
import asyncio
from utils.requestutil import RequestManager

async def test_async_request():
    # 创建请求管理器
    request_manager = RequestManager(timeout=10)
    
    # 异步GET请求
    response = await request_manager.get_async("https://httpbin.org/get")
    print(f"异步GET响应状态码: {response['status_code']}")
    
    # 异步POST请求
    response = await request_manager.post_async(
        "https://httpbin.org/post",
        json_data={"name": "async_test"}
    )
    
    # 关闭连接池
    request_manager.close()

# 运行异步测试
asyncio.run(test_async_request())
```

### 5.5 并发测试

框架支持并发执行多个测试任务：

```python
from utils.concurrencyutil import ConcurrentExecutor

def create_task(url):
    def task():
        try:
            # 这里放置任务逻辑
            return {'url': url, 'status': 'success'}
        except Exception as e:
            return {'url': url, 'error': str(e)}
    return task

# 创建多个测试任务
tasks = [
    create_task('https://httpbin.org/get?test=1'),
    create_task('https://httpbin.org/get?test=2'),
    create_task('https://httpbin.org/get?test=3')
]

# 并发执行
concurrent_executor = ConcurrentExecutor(max_workers=3)
results = concurrent_executor.execute_tasks(tasks)
print(f"并发测试结果: {results}")
```

### 5.6 响应验证

框架提供强大的响应验证功能：

```python
from api_auto_framework import ApiTestFramework

api = ApiTestFramework()

# 发送请求
response = api.send_request('GET', 'https://httpbin.org/get')

# 断言验证
assertions = [
    {"type": "status_code", "expected": 200},
    {"type": "json_path", "path": "$.url", "expected": "https://httpbin.org/get"}
]

success = api.assert_response(response, assertions)
print(f"断言结果: {'通过' if success else '失败'}")

# 结果提取
extract_rules = [
    {"name": "user_agent", "type": "json_path", "path": "$.headers.User-Agent"},
    {"name": "origin_ip", "type": "json_path", "path": "$.origin"}
]

extracted_data = api.extract(response, extract_rules)
print(f"提取的数据: {extracted_data}")
```

### 5.7 数据库操作

框架集成数据库操作功能：

```python
from utils.mysqlutil import DatabaseUtil

db_util = DatabaseUtil()

# 查询数据
data = db_util.query("SELECT * FROM users LIMIT 10")
print(f"查询结果: {data}")

# 执行SQL
result = db_util.execute("UPDATE users SET status = 'active' WHERE id = 1")
print(f"受影响行数: {result}")

# 事务操作
try:
    db_util.start_transaction()
    db_util.execute("INSERT INTO logs (message) VALUES ('Test log')")
    db_util.commit()
except Exception as e:
    db_util.rollback()
    print(f"事务失败: {str(e)}")

# 关闭连接
db_util.close()
```

### 5.8 大模型API集成

框架支持集成OpenAI、Azure OpenAI等大模型API：

```python
from utils.modelutils import OpenAIAPI

# 创建OpenAI API客户端
openai_api = OpenAIAPI(
    api_key='your_api_key',  # 替换为实际的API密钥
    model='gpt-3.5-turbo',
    timeout=30
)

# 发送聊天请求
response = openai_api.chat_completion(
    messages=[{"role": "user", "content": "Hello, world!"}],
    max_tokens=50
)

# 异步调用
async def async_chat_example():
    response = await openai_api.chat_completion_async(
        messages=[{"role": "user", "content": "Hello, async world!"}],
        max_tokens=50
    )
    return response
```

## 6. 测试用例编写

### 6.1 基础测试用例结构

框架提供`BaseTestCase`类作为所有测试用例的基类：

```python
from testcase.base_test_cases import BaseTestCase

class MyTest(BaseTestCase):
    def __init__(self, name="MyTest", description="我的测试"):
        super().__init__(name, description)
    
    def execute(self):
        # 实现测试逻辑
        # 发送请求
        response = self.http_client.get("https://httpbin.org/get")
        
        # 验证响应
        self.assert_status_code(response, 200)
        self.assert_json_contains(response, {"url": "https://httpbin.org/get"})

# 运行测试
test = MyTest()
result = test.run()
print(f"测试结果: {result['status']}")
```

### 6.2 常用测试用例类型

框架提供多种预定义的测试用例类型：

#### 认证测试

```python
from testcase.base_test_cases import AuthTest

# 创建认证测试
auth_test = AuthTest(
    name="LoginTest",
    description="登录认证测试",
    base_url="https://api.example.com",
    endpoint="/login",
    method="POST",
    auth_config={"type": "basic", "username": "user", "password": "pass"}
)

result = auth_test.run()
```

#### 请求体验证测试

```python
from testcase.base_test_cases import RequestBodyTest

# 创建请求体验证测试
body_test = RequestBodyTest(
    name="CreateUserTest",
    description="创建用户测试",
    base_url="https://api.example.com",
    endpoint="/users",
    method="POST",
    auth_config={"type": "token", "token": "your_token"}
)

result = body_test.run()
```

#### 必选字段测试

```python
from testcase.base_test_cases import RequiredFieldTest

# 创建必选字段测试
required_test = RequiredFieldTest(
    name="RequiredFieldsTest",
    description="必选字段验证测试",
    base_url="https://api.example.com",
    endpoint="/users",
    method="POST",
    auth_config={"type": "token", "token": "your_token"},
    required_fields=["name", "email", "password"],
    sample_data={"name": "Test User", "email": "test@example.com", "password": "password123"}
)

result = required_test.run()
```

### 6.3 Pytest集成

框架可以与Pytest无缝集成：

```python
import pytest
from utils.requestsutil import RequestsUtil
from utils.logutil import Logger
from config.settings import config_manager

# 初始化工具类
logger = Logger('api_test', level='INFO')
request_util = RequestsUtil()

class TestAPI:
    
    @pytest.fixture(scope='class')
    def setup_class(self):
        # 获取配置
        api_config = config_manager.get_api_config()
        base_url = api_config.get('base_url', 'https://httpbin.org')
        request_util.set_base_url(base_url)
        
        yield
        
        # 测试后清理
        logger.info('测试类执行完成')
    
    def test_get_example(self, setup_class):
        # 发送GET请求
        response = request_util.get('/get', params={'test': 'value'})
        
        # 验证响应
        assert response.status_code == 200
        assert response.json()['args']['test'] == 'value'

# 运行方式：pytest test_file.py -v
```

### 6.4 批量测试

框架支持批量执行多个测试用例：

```python
from testcase.base_test_cases import BatchTestCase, BaseTestCase

# 创建多个测试用例
class Test1(BaseTestCase):
    def execute(self):
        # 测试逻辑
        pass

class Test2(BaseTestCase):
    def execute(self):
        # 测试逻辑
        pass

# 创建批量测试
batch_test = BatchTestCase(
    name="BatchTest",
    description="批量测试",
    test_cases=[Test1(), Test2()],
    max_workers=2  # 并发数
)

# 运行批量测试
result = batch_test.run()

# 获取详细结果
detailed_results = batch_test.get_results()
```

## 7. 文件组织结构

推荐的项目文件组织结构：

```
d:\DDDD\接口自动化框架\
├── api_auto_framework/       # 框架核心模块
├── config/                   # 配置文件
│   ├── settings.py           # 配置管理
│   └── templates/            # 配置模板
├── docs/                     # 文档
├── examples/                 # 示例代码
├── logs/                     # 日志文件
├── reports/                  # 测试报告
├── testcase/                 # 测试用例
│   ├── base_test_cases.py    # 基础测试用例
│   ├── example.py            # 示例测试
│   └── my_tests/             # 自定义测试用例
├── tests/                    # Pytest测试
├── utils/                    # 工具类
│   ├── authutil.py           # 认证工具
│   ├── concurrencyutil.py    # 并发工具
│   ├── logutil.py            # 日志工具
│   ├── modelutils.py         # 模型工具
│   ├── mysqlutil.py          # 数据库工具
│   └── requestsutil.py       # HTTP请求工具
├── .env                      # 环境变量
├── .env.example              # 环境变量示例
├── README.md                 # 项目说明
├── requirements.txt          # 依赖列表
├── setup.py                  # 安装配置
```

## 8. 命令行工具

框架提供命令行工具`api-test`：

```bash
# 运行测试套件
api-test run --suite auth_suite --environment dev --report html

# 生成测试报告
api-test report --input ./results --output ./reports

# 查看版本
api-test version

# 查看帮助
api-test help
```

## 9. 最佳实践

### 9.1 测试用例编写规范

1. **使用描述性的测试名称**：清晰表达测试目的
2. **遵循单一职责原则**：每个测试用例只测试一个功能点
3. **使用数据驱动**：参数化测试用例，覆盖多种场景
4. **设置适当的超时**：避免测试无限等待
5. **清理测试数据**：使用`teardown`方法清理测试产生的数据
6. **记录关键信息**：使用日志记录重要的测试过程和结果

### 9.2 性能优化建议

1. **使用连接池**：复用HTTP连接
2. **合理设置并发数**：根据系统性能调整并发测试的线程数
3. **避免重复代码**：封装常用操作成工具方法
4. **使用异步请求**：对于I/O密集型任务，使用异步提高效率
5. **定期清理日志**：避免日志文件过大

## 10. 常见问题解答

### 10.1 如何设置代理？

```python
from utils.requestsutil import HttpClient

# 创建HTTP客户端并设置代理
http_client = HttpClient(
    proxy={
        'http': 'http://proxy.example.com:8080',
        'https': 'https://proxy.example.com:8080'
    }
)
```

### 10.2 如何处理SSL验证？

```python
# 忽略SSL验证
http_client = HttpClient(verify_ssl=False)
```

### 10.3 如何添加自定义请求头？

```python
headers = {
    'Authorization': 'Bearer token',
    'Content-Type': 'application/json',
    'X-Custom-Header': 'custom_value'
}

response = request_util.get('/endpoint', headers=headers)
```

### 10.4 如何处理异常？

```python
try:
    response = request_util.get('/endpoint')
    response.raise_for_status()  # 抛出HTTP错误
except requests.exceptions.HTTPError as e:
    print(f"HTTP错误: {e}")
except requests.exceptions.ConnectionError as e:
    print(f"连接错误: {e}")
except requests.exceptions.Timeout as e:
    print(f"超时错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

### 10.5 如何使用动态参数？

```python
from config.settings import DynamicParam

dynamic_params = DynamicParam()

# 设置参数
dynamic_params.set('user_id', '123456')

# 获取参数
user_id = dynamic_params.get('user_id')

# 在URL中使用
url = f"/users/{user_id}"
```

### 10.6 如何进行文件上传测试？

```python
files = {
    'file': open('test.txt', 'rb')
}

response = request_util.post('/upload', files=files)
```

### 10.7 如何生成测试报告？

使用命令行工具：

```bash
api-test report --input ./results --output ./reports --format html
```

### 10.8 如何调试测试用例？

1. **增加日志级别**：设置`LOG_LEVEL=DEBUG`
2. **使用断点**：在测试代码中添加断点
3. **打印中间结果**：输出关键变量值
4. **检查响应内容**：详细分析响应数据

---

## 附录：完整的测试用例示例

```python
"""示例API测试类"""
import pytest
from utils.requestsutil import RequestsUtil
from utils.logutil import Logger
from utils.mysqlutil import DatabaseUtil
from config.settings import config_manager, DynamicParam

# 初始化工具类
logger = Logger('example_test', level='INFO')
request_util = RequestsUtil()
db_util = DatabaseUtil()
dynamic_params = DynamicParam()

class TestExampleAPI:
    """示例API测试类"""
    
    @pytest.fixture(scope='class')
    def setup_class(self):
        """类级别的前置处理"""
        logger.info('开始执行示例测试类')
        
        # 获取配置
        api_config = config_manager.get_api_config()
        base_url = api_config.get('base_url', 'http://httpbin.org')
        request_util.set_base_url(base_url)
        
        # 测试环境初始化
        logger.info(f'测试环境: {base_url}')
        
        yield
        
        # 测试后清理
        logger.info('示例测试类执行完成')
    
    def test_get_example(self, setup_class):
        """测试GET请求示例"""
        logger.info('执行GET请求测试')
        
        # 发送GET请求
        response = request_util.get('/get', params={'test': 'value'})
        
        # 验证响应
        assert response.status_code == 200
        assert response.json()['args']['test'] == 'value'
        
        # 记录响应信息
        logger.info(f'GET响应状态码: {response.status_code}')
    
    def test_post_example(self, setup_class):
        """测试POST请求示例"""
        logger.info('执行POST请求测试')
        
        # 准备请求数据
        data = {
            'name': '测试用户',
            'age': 30,
            'email': 'test@example.com'
        }
        
        # 发送POST请求
        response = request_util.post('/post', json=data)
        
        # 验证响应
        assert response.status_code == 200
        assert response.json()['json']['name'] == '测试用户'
        
        # 存储动态参数供后续测试使用
        dynamic_params.set('user_id', '123456')
        
        logger.info(f'POST响应状态码: {response.status_code}')
```

---

*本文档基于接口自动化测试框架v1.0编写，如有更新，请参考最新版本。*