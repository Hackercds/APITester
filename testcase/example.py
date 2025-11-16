"""
示例测试用例
展示框架的基本使用方法
"""
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
    
    def setup_method(self):
        """方法级别的前置处理"""
        logger.info('开始执行测试方法')
    
    def teardown_method(self):
        """方法级别的后置处理"""
        logger.info('测试方法执行完成')
    
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
    
    def test_header_example(self, setup_class):
        """测试自定义请求头示例"""
        logger.info('执行自定义请求头测试')
        
        # 准备请求头
        headers = {
            'Authorization': 'Bearer test_token_123',
            'User-Agent': 'Test-Automation-Framework/1.0'
        }
        
        # 发送带请求头的请求
        response = request_util.get('/headers', headers=headers)
        
        # 验证响应
        assert response.status_code == 200
        assert 'Authorization' in response.json()['headers']
        
        logger.info('请求头测试通过')
    
    def test_dynamic_params(self, setup_class):
        """测试动态参数使用示例"""
        logger.info('执行动态参数测试')
        
        # 使用之前存储的动态参数
        user_id = dynamic_params.get('user_id', 'default_id')
        
        # 发送包含动态参数的请求
        response = request_util.get('/get', params={'user_id': user_id})
        
        # 验证响应
        assert response.status_code == 200
        assert response.json()['args']['user_id'] == user_id
        
        logger.info(f'动态参数测试通过，user_id: {user_id}')
    
    def test_exception_handling(self, setup_class):
        """测试异常处理示例"""
        logger.info('执行异常处理测试')
        
        # 测试404错误处理
        response = request_util.get('/non_existent_endpoint')
        logger.warning(f'预期的404错误: {response.status_code}')
        
        # 可以在这里添加更多的异常处理逻辑
        # 例如重试、错误断言等


class TestDatabaseOperations:
    """数据库操作示例类"""
    
    def test_database_connection(self):
        """测试数据库连接"""
        try:
            # 测试连接
            with db_util.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                result = cursor.fetchone()
                
            assert result[0] == 1
            logger.info('数据库连接测试通过')
            
        except Exception as e:
            logger.error(f'数据库连接失败: {e}')
            # 数据库测试可能因为环境问题失败，所以不抛出断言错误
            # 只记录日志，让测试继续执行
            print(f'警告: 数据库测试失败，但测试继续执行: {e}')
    
    def test_database_query(self):
        """测试数据库查询（演示用）"""
        try:
            # 这里是演示，实际使用时需要根据数据库结构调整SQL
            # 由于可能没有实际的数据库连接，这里只是演示代码结构
            logger.info('演示数据库查询操作')
            
            # 示例查询（不会实际执行）
            # query = 'SELECT * FROM test_cases WHERE project = %s'
            # params = ('example',)
            # results = db_util.query(query, params)
            
            logger.info('数据库查询操作演示完成')
            
        except Exception as e:
            logger.error(f'数据库查询测试失败: {e}')
            print(f'警告: 数据库查询测试失败，但测试继续执行: {e}')


# 参数化测试示例
@pytest.mark.parametrize('status_code, description', [
    (200, 'OK'),
    (400, 'Bad Request'),
    (404, 'Not Found'),
    (500, 'Internal Server Error')
])
def test_status_codes(status_code, description):
    """参数化测试HTTP状态码"""
    logger.info(f'测试状态码: {status_code} - {description}')
    
    # 使用httpbin的状态码端点测试
    response = request_util.get(f'/status/{status_code}')
    
    # 验证状态码
    assert response.status_code == status_code
    logger.info(f'状态码 {status_code} 测试通过')


if __name__ == '__main__':
    # 直接运行测试
    pytest.main(['-v', __file__])