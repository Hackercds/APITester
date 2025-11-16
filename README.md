# 接口自动化测试框架

一个功能强大、灵活可扩展的API接口自动化测试框架，支持同步/异步HTTP请求、大模型API测试、流式响应处理和全面的错误处理机制。

## 最新更新（v1.0.2）

- **日志系统升级**：实现按日期/会话生成多个日志文件，支持自动轮转和备份
- 修复了框架验证脚本中的HttpClient类不存在问题
- 优化了RequestManager类的配置管理
- 升级了pip包配置，支持开发和完整功能分组依赖
- 更新了所有依赖包到最新兼容版本
- 新增websocket-client和pandas等网络与数据处理支持
- 完善了项目包结构，添加了必要的__init__.py文件
- 清理项目并创建标准.gitignore文件，便于GitHub上传

## 主要特性

- **完整的HTTP请求支持**：支持GET、POST、PUT、DELETE等所有HTTP方法
- **同步与异步API**：同时提供同步和异步接口，满足不同场景需求
- **大模型API测试**：内置OpenAI、Azure OpenAI等大模型API客户端
- **流式响应处理**：支持HTTP长连接和大模型流式输出测试
- **强大的响应验证**：提供丰富的断言和验证机制
- **详细的错误处理**：全面捕获和处理各类API错误情况
- **灵活的配置管理**：支持多环境配置和参数化测试
- **高级日志系统**：支持按日期/会话生成多个日志文件，自动轮转（每6小时）和备份（保留10个），彩色控制台输出
- **可扩展的插件系统**：易于扩展和定制

## 框架概述

这是一个功能全面、灵活通用的接口自动化测试框架，专为测试人员设计，提供了并发控制、性能测试、动态鉴权、测试用例管理、结果提取、大模型接口支持和丰富的随机数据生成功能。框架采用模块化设计，易于扩展和维护，适用于各种规模的API测试场景。

## 安装

### 从源码安装

```bash
# 克隆仓库
# git clone https://github.com/Hackercds/APITester.git
# cd 接口自动化框架

# 安装依赖
pip install -r requirements.txt

# 以开发模式安装
pip install -e .
```

### 直接使用

也可以直接在当前目录使用，无需安装：

```bash
# 添加项目根目录到PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

## 日志系统使用指南

### 日志文件组织结构

框架采用多级目录结构组织日志文件，便于管理和查看：

```
logs/
└── 20251117/                    # 按日期组织的目录
    ├── framework/              # 框架日志目录
    │   └── framework_20251117_023439_4460.log  # 框架日志文件（日期_时间戳_随机数）
    └── user/                   # 用户日志目录
        └── user_20251117_023439_4074.log       # 用户日志文件（日期_时间戳_随机数）
```

### 日志系统配置

日志系统支持以下主要配置：

- **自动轮转**：每6小时自动分割日志文件
- **文件大小限制**：单个日志文件最大10MB
- **备份保留**：保留最近10个日志文件
- **彩色输出**：控制台输出支持彩色高亮
- **日志级别**：支持DEBUG、INFO、WARNING、ERROR、CRITICAL

### 使用日志系统

```python
from utils.logutil import get_logger

# 获取默认的框架日志记录器
logger = get_logger()

# 或者指定日志名称和类型
logger = get_logger(name="my_test", log_type="user", level=logging.INFO)

# 记录不同级别的日志
logger.debug("这是调试信息")
logger.info("这是普通信息")
logger.warning("这是警告信息")
logger.error("这是错误信息")
logger.critical("这是严重错误信息")

# 记录异常
try:
    1/0
except Exception as e:
    logger.exception("发生异常:", exc_info=e)
```

## 快速开始

### 1. 基本HTTP请求测试

```python
from api_auto_framework.utils.requestutil import RequestManager

# 创建请求管理器
manager = RequestManager(
    base_url="https://api.example.com",
    timeout=30
)

# 添加请求头
manager.add_header("Authorization", "Bearer your_api_key")
manager.add_header("Content-Type", "application/json")

# 发送GET请求
response = manager.get(
    endpoint="/users",
    params={"page": 1, "limit": 10}
)

# 验证响应
assert response.status_code == 200
assert response.success is True
print(f"获取到 {len(response.data['items'])} 条数据")

# 发送POST请求
user_data = {
    "username": "testuser",
    "email": "test@example.com"
}
response = manager.post(
    endpoint="/users",
    json=user_data
)

assert response.status_code == 201
print(f"创建的用户ID: {response.data['id']}")
```

### 2. 异步HTTP请求

```python
import asyncio
from api_auto_framework.utils.requestutil import RequestManager

async def async_test():
    # 创建请求管理器
    manager = RequestManager(
        base_url="https://api.example.com",
        timeout=30
    )
    
    # 发送异步GET请求
    response = await manager.get_async(endpoint="/products")
    print(f"获取到 {len(response.data)} 个产品")
    
    # 并发发送多个请求
    tasks = [
        manager.get_async(endpoint=f"/products/{i}")
        for i in range(1, 6)
    ]
    
    results = await asyncio.gather(*tasks)
    for i, result in enumerate(results):
        print(f"产品 {i+1}: {result.data['name']}")

# 运行异步测试
asyncio.run(async_test())
```

## 主要功能特性

- **灵活的认证管理**：支持Basic Auth、Token、OAuth2、HMAC等多种认证方式，支持动态参数和路径特定密钥
- **强大的断言验证**：支持多种断言类型，包括JSON路径、正则表达式、状态码等，支持自定义断言和批量断言
- **便捷的结果提取**：支持JSONPath、XPath、正则表达式、HTTP头部等多种数据提取方式
- **大模型接口支持**：内置对OpenAI、Azure OpenAI等大模型API的支持，特别优化了流式接口处理
- **丰富的随机数据生成**：提供各种随机数据生成工具，支持基于分词表的文本生成
- **多环境配置管理**：支持多环境配置、配置文件加载和环境变量覆盖，易于跨环境使用
- **并发控制与速率限制**：支持TPS/QPS精确控制，多种并发策略
- **性能测试**：自动爬坡算法查找系统极限性能，详细的性能指标报告
- **测试用例管理**：完整的CRUD操作，支持JSON/YAML/Excel导入导出
- **定时任务**：基于cron表达式的灵活调度，支持任务状态跟踪和错误重试
- **异常处理**：全面的异常捕获和错误报告，支持HTML/JSON格式导出
- **测试套件**：批量执行测试用例，生成综合测试报告

## 安装说明

### 环境要求

- Python 3.8+

### 命令行环境注意事项

在Windows系统中，安装时可能会遇到编码相关问题，建议注意以下几点：

1. **命令行环境选择**：
   - 在PowerShell中可能会遇到`UnicodeDecodeError: 'gbk' codec can't decode byte 0x80 in position 10: illegal multibyte sequence`错误
   - 推荐在Windows CMD命令提示符中执行安装命令，通常可以避免编码问题

2. **安装方式**：
   ```bash
   # 在CMD中执行以下命令
   pip install -e . --no-cache-dir
   ```

3. **常见问题解决**：
   - 如果遇到编码错误，尝试切换到CMD环境
   - 确保Python环境的默认编码设置为UTF-8
   - 可以考虑直接使用依赖包而不进行安装：`pip install -r requirements.txt`然后将项目目录添加到PYTHONPATH
- 依赖包：requirements.txt中列出

### 安装步骤

1. 克隆项目代码

```bash
git clone <项目仓库地址>
cd 接口自动化框架
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

## 目录结构

```
接口自动化框架/
├── common/               # 公共工具和常量
│   ├── constants.py      # 常量定义
│   └── utils.py          # 公共工具函数
├── config/               # 配置文件
│   ├── config.py         # 主配置文件
│   └── environments.py   # 环境配置
├── testcase/             # 测试用例
│   ├── base_test_cases.py # 基础测试用例类
│   └── __init__.py
├── utils/                # 核心功能模块
│   ├── assertutil.py     # 断言验证工具
│   ├── authutil.py       # 鉴权管理工具
│   ├── configutil.py     # 配置管理工具
│   ├── concurrencyutil.py # 并发控制工具
│   ├── exceptionutil.py  # 异常处理工具
│   ├── extractutil.py    # 结果提取工具
│   ├── modelutils.py     # 大模型接口工具
│   ├── randomutil.py     # 随机数据生成工具
│   ├── requestutil.py    # HTTP请求工具
│   ├── scheduleutil.py   # 定时任务工具
│   └── testcasemanager.py # 测试用例管理工具
├── reports/              # 报告输出目录
├── examples/             # 示例代码
├── main.py               # 框架入口
└── requirements.txt      # 依赖包列表
```

## 核心模块使用指南

### 1. 配置管理 (configutil.py)

**功能说明**：管理框架配置，支持多环境配置、配置文件加载和环境变量覆盖

**基本使用**：

```python
from utils.configutil import ConfigManager, load_config, get_config

# 创建配置管理器
config_manager = ConfigManager()

# 加载配置
config_manager.load_config('config/default.json')
config_manager.load_env_config('development')  # 加载开发环境配置

# 获取配置
base_url = config_manager.get('api.base_url')
api_key = config_manager.get('api.api_key', default='default_key')

# 使用便捷函数
load_config('config/default.json')
api_timeout = get_config('api.timeout', default=30)
```

**配置文件示例**：

```json
{
  "environments": {
    "development": {
      "api": {
        "base_url": "http://dev-api.example.com",
        "timeout": 10
      }
    },
    "production": {
      "api": {
        "base_url": "https://api.example.com",
        "timeout": 5
      }
    }
  },
  "default": {
    "api": {
      "version": "v1",
      "retry_count": 3
    }
  }
}
```

### 2. 鉴权管理 (authutil.py)

**功能说明**：提供多种认证方式，支持动态参数和灵活的认证策略

**基本使用**：

```python
from utils.authutil import AuthManager, BasicAuth, TokenAuth, OAuth2Auth, HMACAuth

# 创建基本认证
basic_auth = BasicAuth(username='user', password='pass')

# 创建Token认证
token_auth = TokenAuth(token='bearer_token_here')

# 创建OAuth2认证
oauth2_auth = OAuth2Auth(
    client_id='client_id',
    client_secret='client_secret',
    token_url='https://auth.example.com/token',
    scope='read write'
)

# 创建HMAC认证
hmac_auth = HMACAuth(
    access_key='access_key',
    secret_key='secret_key',
    algorithm='SHA256'
)

# 使用认证管理器
auth_manager = AuthManager(default_auth=token_auth)

# 添加请求认证
import requests
response = requests.get(
    'https://api.example.com/data',
    headers=auth_manager.get_headers()
)
```

**动态认证示例**：

```python
from utils.authutil import DynamicAuthProvider

# 创建动态认证提供者
def get_token_func():
    # 实现获取token的逻辑
    return {'token': 'dynamic_token'}

dynamic_provider = DynamicAuthProvider(get_token_func, refresh_interval=3600)

dynamic_auth = TokenAuth(provider=dynamic_provider)
```

### 3. HTTP请求 (requestutil.py)

**功能说明**：提供增强的HTTP请求功能，支持异步请求、重试、流式响应等

**基本使用**：

```python
from utils.requestutil import RequestManager, DefaultResponseHandler

# 创建请求管理器
request_manager = RequestManager(
    base_url='https://api.example.com',
    timeout=10,
    retry_count=3,
    retry_status_codes=[500, 502, 503]
)

# 发送GET请求
response = request_manager.get('/api/data', params={'id': 123})

# 发送POST请求
response = request_manager.post('/api/create', json={'name': 'test'})

# 使用自定义响应处理器
class CustomHandler(DefaultResponseHandler):
    def handle_response(self, response):
        # 自定义响应处理逻辑
        result = super().handle_response(response)
        result['custom_field'] = 'custom_value'
        return result

request_manager.set_response_handler(CustomHandler())
```

**异步请求示例**：

```python
import asyncio
from utils.requestutil import AsyncRequestManager

async def main():
    async_manager = AsyncRequestManager(
        base_url='https://api.example.com',
        timeout=10
    )
    
    # 发送异步请求
    response = await async_manager.get_async('/api/data')
    
    # 并发请求
    tasks = [
        async_manager.get_async(f'/api/items/{i}')
        for i in range(5)
    ]
    responses = await asyncio.gather(*tasks)

# 运行异步代码
asyncio.run(main())
```
```

### 4. 断言验证 (assertutil.py)

**功能说明**：提供多种断言类型，支持自定义断言和批量断言执行

**基本使用**：

```python
from utils.assertutil import AssertionManager, assert_equal, assert_contains

# 创建断言管理器
assert_manager = AssertionManager()

# 添加断言
response_data = {'status': 'success', 'data': {'id': 123}}
assert_manager.add_assertion('状态成功', 'equal', response_data['status'], 'success')
assert_manager.add_assertion('ID存在', 'contains', response_data, 'data.id')

# 执行所有断言
results = assert_manager.execute_all()
for result in results:
    print(f"{result.name}: {'通过' if result.success else '失败'}")

# 使用便捷函数
assert_equal(response_data['status'], 'success', '状态应该是success')
assert_contains(response_data, 'data.id', '响应应该包含id字段')
```

**自定义断言示例**：

```python
from utils.assertutil import AssertionManager

# 创建自定义断言函数
def assert_positive(value, message=None):
    """断言值为正数"""
    message = message or f"断言 {value} 是正数"
    try:
        assert float(value) > 0, f"{value} 不是正数"
        return True, message
    except (AssertionError, TypeError, ValueError) as e:
        return False, str(e)

# 注册自定义断言
AssertionManager.register_assertion('positive', assert_positive)

# 使用自定义断言
assert_manager = AssertionManager()
assert_manager.add_assertion('值为正数', 'positive', 100)
results = assert_manager.execute_all()
```

### 5. 结果提取 (extractutil.py)

**功能说明**：支持从HTTP响应中提取数据，支持多种提取方式

**基本使用**：

```python
from utils.extractutil import ResponseExtractor, JSONExtractor, RegexExtractor

# 假设的响应数据
response_content = 'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{"id": 123, "name": "Test", "data": {"items": [1, 2, 3]}}'

# 创建响应提取器
response_extractor = ResponseExtractor(response_content)

# 提取JSON数据
id_value = response_extractor.extract_json('$.id')
items = response_extractor.extract_json('$.data.items[*]')

# 提取状态码
status_code = response_extractor.extract_status_code()

# 提取响应头
content_type = response_extractor.extract_header('Content-Type')

# 使用正则表达式提取
regex_extractor = RegexExtractor()
matched = regex_extractor.extract(response_content, r'"name": "(.*?)"')
```

**批量提取示例**：

```python
from utils.extractutil import ExtractionManager

# 创建提取管理器	extraction_manager = ExtractionManager()

# 添加多个提取规则	extraction_manager.add_extraction('user_id', 'json', '$.data.user.id')
extraction_manager.add_extraction('user_name', 'json', '$.data.user.name')
extraction_manager.add_extraction('status', 'regex', r'"status": "(.*?)"')

# 执行批量提取
response_data = '{"data": {"user": {"id": 456, "name": "John"}, "status": "active"}}'
results = extraction_manager.execute_all(response_data)

print(results)  # {'user_id': 456, 'user_name': 'John', 'status': 'active'}
```

### 6. 大模型接口 (modelutils.py)

**功能说明**：提供对大模型API的支持，优化了流式接口处理

**基本使用**：

```python
from utils.modelutils import OpenAIAPI, AsyncModelResponseHandler

# 创建OpenAI API客户端
openai_api = OpenAIAPI(
    api_key='your_api_key',
    model='gpt-4'
)

# 发送同步请求
response = openai_api.chat_completions(
    messages=[{"role": "user", "content": "Hello, world!"}],
    max_tokens=100
)
print(response['choices'][0]['message']['content'])

# 使用流式响应
for chunk in openai_api.chat_completions(
    messages=[{"role": "user", "content": "Write a short story"}],
    stream=True
):
    if 'content' in chunk['choices'][0]['delta']:
        print(chunk['choices'][0]['delta']['content'], end='', flush=True)

# 异步流式处理
async def process_stream():
    handler = AsyncModelResponseHandler()
    async for chunk in openai_api.chat_completions_async(
        messages=[{"role": "user", "content": "Explain quantum computing"}],
        stream=True
    ):
        text = handler.process_chunk(chunk)
        if text:
            print(text, end='', flush=True)
```

### 7. 大模型API测试

```python
import asyncio
from utils.modelutils import OpenAIAPI

async def test_chat_completion():
    # 创建模型API客户端
    api = OpenAIAPI(
        api_key="your_api_key",
        timeout=60
    )
    
    # 准备消息
    messages = [
        {"role": "system", "content": "你是一位助手。"},
        {"role": "user", "content": "请简要介绍Python语言。"}
    ]
    
    # 发送聊天完成请求
    response = await api.chat_completions_async(
        messages=messages,
        model="gpt-3.5-turbo",
        max_tokens=200
    )
    
    print("响应内容:", response['choices'][0]['message']['content'])

# 运行测试
asyncio.run(test_chat_completion())
```

### 8. 流式响应测试

```python
import asyncio
from utils.modelutils import OpenAIAPI
from utils.assertutil import AssertionManager

async def test_streaming():
    # 创建模型API客户端
    api = OpenAIAPI(api_key="your_api_key")
    
    # 创建断言管理器
    assert_manager = AssertionManager()
    assert_manager.add_assertion("响应内容长度", "length_gt", 0)
    
    # 准备消息
    messages = [
        {"role": "user", "content": "请生成一个简短的故事。"}
    ]
    
    # 存储完整响应
    full_response = ""
    
    # 发送流式请求
    print("流式响应:")
    async for chunk in api.chat_completions_async(
        messages=messages,
        model="gpt-3.5-turbo",
        stream=True
    ):
        if chunk.get('choices') and chunk['choices'][0].get('delta'):
            content = chunk['choices'][0]['delta'].get('content', '')
            if content:
                print(content, end="", flush=True)
                full_response += content
    
    print("\n")
    
    # 执行断言验证
    results = assert_manager.execute_all()
    print(f"测试结果: {'通过' if all(r.success for r in results) else '失败'}")
    print(f"响应内容总长度: {len(full_response)} 字符")

# 运行测试
asyncio.run(test_streaming())
```

## 完整文档与使用指南

### 框架目录结构

```
接口自动化框架/
├── api_auto_framework/      # 框架主包
│   ├── common/              # 通用工具和常量
│   ├── config/              # 配置管理
│   ├── utils/               # 核心工具类
│   │   ├── __init__.py
│   │   ├── requestutil.py   # HTTP请求工具
│   │   ├── modelutils.py    # 大模型API工具
│   │   ├── streamutil.py    # 流式响应处理
│   │   ├── assertutil.py    # 断言工具
│   │   └── datautil.py      # 数据处理工具
│   └── __init__.py
├── examples/                # 使用示例
│   ├── async_streaming_examples.py
│   └── basic_examples.py
├── templates/               # 测试用例模板
│   └── test_case_template.py
├── tests/                   # 测试用例
│   ├── __init__.py
│   ├── example_tests.py
│   └── error_handling_tests.py
├── config/                  # 配置文件
│   ├── default.yaml
│   └── dev.yaml
├── requirements.txt         # 依赖列表
├── setup.py                 # 打包配置
└── README.md                # 项目文档
```

### 使用最佳实践

1. **测试用例组织**
   - 将相似功能的测试用例组织到同一个测试类中
   - 使用pytest的fixture功能管理测试数据和前置条件
   - 为每个API端点创建专门的测试方法

2. **性能测试技巧**
   - 使用并发请求测试API的并发处理能力
   - 监控响应时间分布，识别性能瓶颈
   - 对大模型API测试，关注首次token延迟和生成速度

3. **错误处理策略**
   - 全面测试各种错误场景，包括4xx和5xx状态码
   - 验证错误信息的准确性和完整性
   - 测试超时处理和重试机制

4. **数据管理**
   - 使用参数化测试覆盖多种输入场景
   - 为测试创建专用的测试数据集
   - 清理测试过程中产生的临时数据

### 扩展框架功能

1. **添加新的认证方式**
   ```python
   from api_auto_framework.utils.auth import BaseAuth
   
   class CustomAuth(BaseAuth):
       def __init__(self, api_key, user_id):
           self.api_key = api_key
           self.user_id = user_id
       
       def get_auth_headers(self):
           return {
               "X-API-Key": self.api_key,
               "X-User-ID": self.user_id
           }
   ```

2. **自定义响应验证器**
   ```python
   from api_auto_framework.utils.assertutil import BaseValidator
   
   class CustomValidator(BaseValidator):
       def validate(self, response):
           # 自定义验证逻辑
           result = super().validate(response)
           
           # 验证特定业务规则
           if response.data.get("status") != "active":
               self.add_error("状态错误：期望状态为active")
           
           return result
   ```

3. **创建插件**
   - 在 `api_auto_framework/plugins/` 目录下创建新的插件模块
   - 实现插件接口，注册到框架中

### 常见问题解答

**Q: 如何配置不同环境的测试？**
A: 使用环境变量或不同的配置文件，如`config/dev.yaml`、`config/prod.yaml`，并在启动时指定使用哪个配置文件。

**Q: 如何处理API认证？**
A: 使用`RequestManager`的认证功能，支持Bearer Token、Basic Auth等多种认证方式。

**Q: 如何测试大文件上传？**
A: 使用`upload_file`方法，框架会自动处理文件上传流程。

**Q: 如何调试测试用例？**
A: 使用`pytest -v`查看详细输出，或添加`print`语句调试。也可以使用`--pdb`参数启动调试器。

**Q: 如何生成测试报告？**
A: 框架支持集成pytest-html、allure等测试报告工具。

## 总结

这个接口自动化框架提供了全面的API测试功能，包括同步/异步请求、大模型API支持、流式响应处理和强大的验证机制。通过合理使用框架的各种功能，可以有效提高API测试的效率和质量，确保API服务的稳定性和可靠性。

### 7. 随机数据生成 (randomutil.py)

**功能说明**：提供各种随机数据生成功能，支持模型分词表生成和测试数据创建

**基本使用**：

```python
from utils.randomutil import DataGenerator, generate, generate_dict

# 创建数据生成器
generator = DataGenerator()

# 生成基本数据
random_string = generator.generate('string', length=10)
random_int = generator.generate('integer', min_value=1, max_value=100)
random_email = generator.generate('email')
random_date = generator.generate('date', format='%Y-%m-%d')

# 生成结构化数据
user_schema = {
    'id': {'type': 'integer', 'kwargs': {'min_value': 1000, 'max_value': 9999}},
    'username': {'type': 'string', 'kwargs': {'length': 8}},
    'email': {'type': 'email'},
    'created_at': {'type': 'datetime'}
}
user_data = generator.generate_dict(user_schema)

# 使用便捷函数
random_phone = generate('mobile')
```

**模型分词表生成示例**：

```python
from utils.randomutil import DataGenerator, load_word_list, generate_model_input

# 加载自定义分词表
custom_words = ['测试', '接口', '自动化', '框架', '性能', '验证', '响应', '请求']
load_word_list('custom_words', custom_words)

# 生成基于分词表的文本
model_input = generate_model_input(
    word_list_name='custom_words',
    min_length=50,
    max_length=100,
    language='chinese'
)
print(f"模型输入文本: {model_input}")

# 从文件加载分词表
generator = DataGenerator()
generator.load_word_list_from_file(
    'vocab_from_file',
    'vocabulary.txt',
    encoding='utf-8'
)
```

### 8. 性能测试模块 (requestutil.py - PerformanceTester)

```python
from utils.requestsutil import PerformanceTester

# 创建性能测试器
perf_tester = PerformanceTester(
    url="http://api.example.com/test",
    method="GET",
    max_concurrency=100,
    ramp_strategy="exponential"  # 可选: linear, exponential, binary
)

# 查找最大TPS
max_tps_result = perf_tester.find_max_tps(
    error_threshold=0.01,  # 1%错误率阈值
    response_time_threshold=1000  # 1000ms响应时间阈值
)

print(f"最大TPS: {max_tps_result['max_tps']}")
print(f"最佳并发数: {max_tps_result['optimal_concurrency']}")

# 生成HTML报告
report_path = perf_tester.generate_report(format="html")
print(f"报告已生成: {report_path}")
```

### 3. 并发控制模块 (concurrencyutil.py)

```python
from utils.concurrencyutil import ConcurrentExecutor, RateLimiter

# 创建速率限制器 (每秒10个请求)
rate_limiter = RateLimiter(tps=10)

# 创建并发执行器
with ConcurrentExecutor(max_workers=5, rate_limiter=rate_limiter) as executor:
    # 提交多个任务
    futures = []
    for i in range(20):
        futures.append(executor.submit(my_function, i))
    
    # 获取结果
    for future in futures:
        result = future.result()
        print(result)
```

### 4. 测试用例管理 (testcasemanager.py)

```python
from utils.testcasemanager import test_case_manager

# 创建测试用例
test_case = {
    "name": "用户登录测试",
    "url": "http://api.example.com/login",
    "method": "POST",
    "data": {"username": "test", "password": "123456"},
    "assertions": [
        {"type": "status_code", "expected": 200},
        {"type": "json_path", "path": "$.token", "expected": "not_null"}
    ]
}

test_case_manager.create_test_case("login_test_001", test_case)

# 创建测试套件
test_case_manager.create_test_suite("auth_suite", "认证测试套件", ["login_test_001"])

# 导出测试用例
test_case_manager.export_to_excel("./exports/test_cases.xlsx")

# 导入测试用例
test_case_manager.import_from_json("./exports/test_cases.json")
```

### 5. 定时任务调度 (scheduleutil.py)

```python
from utils.scheduleutil import task_scheduler, TestCaseScheduler

# 添加定时任务（每5分钟执行一次）
def my_task():
    print("定时任务执行")

# 间隔任务（每5分钟）
task_scheduler.add_interval_task(
    task_id="interval_task",
    func=my_task,
    interval=300,  # 5分钟
    name="示例间隔任务",
    max_retries=3
)

# Cron任务（每天上午10点）
task_scheduler.add_cron_task(
    task_id="daily_task",
    func=my_task,
    cron_expression="0 10 * * *",
    name="每日任务"
)

# 启动调度器
task_scheduler.start()

# 测试用例调度器
test_scheduler = TestCaseScheduler()

# 添加测试套件定时执行
test_scheduler.schedule_suite(
    suite_id="auth_suite",
    cron_expression="0 9 * * *",  # 每天上午9点
    report_dir="./reports"
)
```

### 6. 异常处理 (exceptionutil.py)

```python
from utils.exceptionutil import (
    HttpRequestError, handle_exception, error_reporter
)

# 使用装饰器处理异常
@handle_exception(report_errors=True, continue_on_error=False)
def risky_operation():
    # 可能抛出异常的操作
    pass

# 手动捕获和报告异常
try:
    # 执行操作
    pass
except Exception as e:
    error_reporter.add_error(e, context={"operation": "test_operation"})

# 生成错误报告
error_reporter.export_to_html("./reports/error_report.html")

# 发送邮件报告
smtp_config = {
    "server": "smtp.example.com",
    "port": 587,
    "username": "user@example.com",
    "password": "password",
    "from": "user@example.com"
}

error_reporter.send_email_report(
    smtp_config=smtp_config,
    recipients=["admin@example.com"],
    include_attachments=True
)
```

## 配置文件说明

### 主配置文件 (config/config.py)

```python
# 框架全局配置
class Config:
    # HTTP配置
    HTTP_TIMEOUT = 30
    HTTP_RETRY_COUNT = 3
    HTTP_RETRY_DELAY = 1
    
    # 性能测试配置
    PERF_TEST_DURATION = 60  # 秒
    PERF_TEST_WARMUP = 10    # 预热时间（秒）
    
    # 报告配置
    REPORT_DIR = "./reports"
    REPORT_FORMAT = "html"  # html, json
    
    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FILE = "api_auto_test.log"
    
    # 调度器配置
    SCHEDULER_THREAD_COUNT = 10
```

### 环境配置 (config/environments.py)

```python
# 环境配置
ENVIRONMENTS = {
    "dev": {
        "base_url": "http://dev-api.example.com",
        "timeout": 10,
        "headers": {
            "X-Environment": "development"
        }
    },
    "test": {
        "base_url": "http://test-api.example.com",
        "timeout": 15,
        "headers": {
            "X-Environment": "testing"
        }
    },
    "prod": {
        "base_url": "http://api.example.com",
        "timeout": 30,
        "headers": {
            "X-Environment": "production"
        }
    }
}
```

## 综合示例

### 完整的接口测试流程

```python
from utils.configutil import load_config, get_config
from utils.authutil import AuthManager, TokenAuth
from utils.requestutil import RequestManager
from utils.assertutil import AssertionManager
from utils.extractutil import ResponseExtractor
from utils.randomutil import DataGenerator

# 1. 加载配置
load_config('config/api_config.json')
base_url = get_config('api.base_url')
timeout = get_config('api.timeout', default=30)

# 2. 创建认证管理器
auth_manager = AuthManager(
    default_auth=TokenAuth(token=get_config('api.token'))
)

# 3. 创建请求管理器
request_manager = RequestManager(
    base_url=base_url,
    timeout=timeout,
    retry_count=get_config('api.retry_count', default=3),
    retry_status_codes=[500, 502, 503],
    auth_manager=auth_manager
)

# 4. 生成测试数据
generator = DataGenerator()
test_user_data = generator.generate_dict({
    'name': {'type': 'chinese', 'kwargs': {'length': 4}},
    'email': {'type': 'email'},
    'age': {'type': 'integer', 'kwargs': {'min_value': 18, 'max_value': 60}}
})

# 5. 发送请求
response = request_manager.post(
    '/api/users',
    json=test_user_data,
    headers={'Content-Type': 'application/json'}
)

# 6. 提取响应数据	extractor = ResponseExtractor(response.text)
user_id = extractor.extract_json('$.data.id')
created_at = extractor.extract_json('$.data.created_at')

# 7. 执行断言
assert_manager = AssertionManager()
assert_manager.add_assertion('状态码为200', 'equal', response.status_code, 200)
assert_manager.add_assertion('ID存在', 'is_not_none', user_id)
assert_manager.add_assertion('名称正确', 'equal', extractor.extract_json('$.data.name'), test_user_data['name'])
assert_manager.add_assertion('邮箱正确', 'equal', extractor.extract_json('$.data.email'), test_user_data['email'])

# 8. 验证断言结果
results = assert_manager.execute_all()
all_passed = all(result.success for result in results)

print(f"测试结果: {'通过' if all_passed else '失败'}")
for result in results:
    print(f"  {result.name}: {'通过' if result.success else '失败'}")

if not all_passed:
    raise AssertionError("接口测试失败")
```

### 大模型接口测试示例

```python
from utils.configutil import load_config, get_config
from utils.modelutils import OpenAIAPI, ModelResponseHandler
from utils.assertutil import assert_contains
from utils.randomutil import generate_model_input

# 加载配置
load_config('config/model_config.json')

# 创建大模型API客户端
model_api = OpenAIAPI(
    api_key=get_config('openai.api_key'),
    model=get_config('openai.model', default='gpt-3.5-turbo')
)

# 生成模型输入（基于分词表）
test_prompt = generate_model_input(
    word_list_name='chinese_common',
    min_length=100,
    max_length=200,
    language='chinese'
)
print(f"测试输入: {test_prompt}")

# 使用流式响应处理
print("\n模型响应:")
handler = ModelResponseHandler()

for chunk in model_api.chat_completions(
    messages=[{"role": "user", "content": f"总结以下内容:\n{test_prompt}"}],
    stream=True,
    max_tokens=150
):
    text = handler.process_chunk(chunk)
    if text:
        print(text, end='', flush=True)

# 获取完整响应
full_response = handler.get_full_response()

# 执行断言验证
assert_contains(full_response, '总结', '响应应该包含总结内容')
assert len(full_response) > 50, '响应内容长度应该大于50个字符'

print("\n\n大模型接口测试通过!")
```
```

## 性能测试最佳实践

1. **设置合理的预热时间**：在正式测试前让系统达到稳定状态
2. **逐步增加并发**：使用exponential或binary策略快速定位性能瓶颈
3. **关注错误率**：当错误率超过阈值时及时停止测试
4. **分析详细指标**：不仅关注TPS，还要分析响应时间分布、错误类型等
5. **持续监控**：在性能测试期间监控系统资源使用情况

## 注意事项

1. **安全考虑**：生产环境测试时注意控制并发量，避免影响线上服务
2. **资源管理**：长时间运行的定时任务需要合理管理系统资源
3. **错误处理**：在关键业务流程中确保异常被正确捕获和报告
4. **版本兼容**：确保Python版本和依赖包版本符合要求

## 高级特性

### 1. 参数化测试

```python
import pytest
from utils.randomutil import generate
from utils.requestutil import RequestManager
from utils.assertutil import AssertionManager

@pytest.mark.parametrize("user_type,expected_status", [
    ("admin", 200),
    ("user", 200),
    ("guest", 403)
])
def test_user_access(user_type, expected_status):
    """参数化测试不同用户类型的访问权限"""
    # 创建请求管理器
    request_manager = RequestManager(base_url="https://api.example.com")
    
    # 发送请求
    response = request_manager.get(
        f"/api/access?type={user_type}",
        headers={"X-User-Type": user_type}
    )
    
    # 断言验证
    assert_manager = AssertionManager()
    assert_manager.add_assertion("状态码正确", "equal", response.status_code, expected_status)
    assert_manager.execute_all()
```

### 2. 环境变量覆盖

```python
# 在代码中使用环境变量覆盖的配置
from utils.configutil import ConfigManager

config_manager = ConfigManager()
config_manager.load_config('config/default.json')

# 加载环境变量覆盖
# 环境变量格式: API_TIMEOUT -> api.timeout
config_manager.load_env_vars(prefix='API_')

# 获取配置（会优先使用环境变量中的值）
timeout = config_manager.get('api.timeout')
```

### 3. 自定义中间件

```python
from utils.requestutil import RequestManager, RequestMiddleware

# 创建自定义请求中间件
class LoggingMiddleware(RequestMiddleware):
    def before_request(self, request):
        print(f"发送请求: {request.method} {request.url}")
        return request
    
    def after_request(self, response):
        print(f"收到响应: {response.status_code}")
        return response

# 创建请求管理器并添加中间件
request_manager = RequestManager(base_url="https://api.example.com")
request_manager.add_middleware(LoggingMiddleware())

# 发送请求时会自动应用中间件
response = request_manager.get('/api/data')
```

## 最佳实践

1. **配置管理**
   - 使用多环境配置文件管理不同环境的配置
   - 敏感信息（如API密钥）使用环境变量配置
   - 为配置项设置合理的默认值

2. **认证管理**
   - 对不同接口使用适当的认证方式
   - 对于需要频繁刷新的token，使用动态认证提供者
   - 为不同路径配置特定的认证策略

3. **请求处理**
   - 针对502、503等临时错误配置自动重试
   - 使用异步请求提高测试效率
   - 为不同类型的响应配置专用处理器

4. **断言验证**
   - 验证关键业务数据而不仅是状态码
   - 使用自定义断言扩展验证能力
   - 批量断言提高测试可读性

5. **数据管理**
   - 使用随机数据生成器创建测试数据
   - 对于大模型接口测试，使用基于分词表的文本生成
   - 结构化数据使用schema定义确保数据一致性

6. **测试组织**
   - 按功能模块组织测试用例
   - 使用fixture管理测试资源
   - 实现测试数据的自动清理

## 常见问题解答

### Q: 如何配置HTTPS代理？

A: 可以在创建RequestManager时设置代理配置：

```python
request_manager = RequestManager(
    base_url='https://api.example.com',
    proxies={
        'https': 'https://proxy.example.com:8080',
        'http': 'http://proxy.example.com:8080'
    }
)
```

### Q: 如何处理文件上传接口？

A: 使用RequestManager的文件上传支持：

```python
files = {'file': open('test.txt', 'rb')}
response = request_manager.post('/api/upload', files=files)
```

### Q: 如何自定义HMAC签名的构建逻辑？

A: 创建自定义的HMACAuth子类：

```python
from utils.authutil import HMACAuth

class CustomHMACAuth(HMACAuth):
    def _build_signature_string(self, request, timestamp):
        # 自定义签名字符串构建逻辑
        return f"{request.method}\n{request.path}\n{timestamp}\n{request.body}"

custom_hmac = CustomHMACAuth(
    access_key='access_key',
    secret_key='secret_key'
)
```

### Q: 如何处理WebSocket接口？

A: 对于WebSocket接口，建议使用专门的WebSocket库，如websockets：

```python
import asyncio
import websockets

async def test_websocket():
    async with websockets.connect('ws://api.example.com/ws') as websocket:
        # 发送消息
        await websocket.send('{"action": "subscribe", "channel": "updates"}')
        
        # 接收消息
        response = await websocket.recv()
        print(f"收到WebSocket消息: {response}")

asyncio.run(test_websocket())
```

### Q: 如何使用框架进行压力测试？

A: 结合asyncio进行并发请求测试：

```python
import asyncio
from utils.requestutil import AsyncRequestManager

async def stress_test():
    async_manager = AsyncRequestManager(base_url='https://api.example.com')
    
    # 创建100个并发请求
    tasks = [async_manager.get_async('/api/health') for _ in range(100)]
    
    # 执行并计时
    import time
    start_time = time.time()
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    # 统计结果
    successful = sum(1 for r in responses if isinstance(r, dict) and 'status' in r)
    failed = len(responses) - successful
    
    print(f"压力测试结果:")
    print(f"总请求数: {len(responses)}")
    print(f"成功请求: {successful}")
    print(f"失败请求: {failed}")
    print(f"总耗时: {end_time - start_time:.2f}秒")
    print(f"QPS: {len(responses) / (end_time - start_time):.2f}")

asyncio.run(stress_test())
```

## 扩展开发

框架设计采用了模块化和面向对象的思想，便于扩展：

1. **添加新的认证方式**：继承`AuthBase`类并实现`get_headers`和`authenticate_request`方法
2. **自定义断言类型**：使用`AssertionManager.register_assertion`注册自定义断言函数
3. **扩展结果提取器**：继承`Extractor`基类并实现`extract`方法
4. **添加新的数据生成器**：继承`RandomGenerator`类并实现`generate`方法
5. **实现新的响应处理器**：继承`ResponseHandler`基类并实现`handle_response`方法
6. **扩展并发策略**：在`ConcurrencyUtil`中添加新的并发控制算法

## 贡献指南

欢迎贡献代码或提供建议！请遵循以下步骤：

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 许可证

本项目采用Apache许可证。详情请查看LICENSE文件。

## 更新日志

### v1.0.0
- 初始版本，包含所有核心功能
- 支持多种认证方式、断言验证、结果提取
- 大模型接口支持和随机数据生成工具
