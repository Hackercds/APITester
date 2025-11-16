# 测试用例执行类
import datetime
import json

import pytest

from common import Base
from config.settings import DynamicParam
from utils.logutil import logger

# 初始化代码准备：
from utils.readmysql import RdTestcase
from utils.requestsutil import RequestSend
#媳妇1：从数据库获取用例
jwcase_data = RdTestcase()
# 根据测试用例对象获取测试用例列表 okr-api 注意 这个位置要和数据库中的okr-api保持一致
# 功能1：筛选出想要使用的用例
case_list = jwcase_data.is_run_data('okr-api')

##媳妇2：根据数据中的数据发出接口请求 记录结果
jwsend_jiekou=RequestSend()

# 获取当前时间（用于声明执行时间）
# 注意导入包的语句 这里导入的是模块
#import datetime
current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class TestApi:
    # 类方法，运行开始前只执行1次
    def setup_class(self):
        # 打印日志
        # 注意导入包的语句
        #from utils.logutil import logger
        #from urllib3.util import current_time
        logger.info(f"***** 开始执行测试用例，开始时间为：{current_time} *****")

    # 类方法，运行结束后只执行1次
    def teardown_class(self):
        # 打印日志
        #from urllib3.util import current_time
        logger.info(f"***** 执行用例完成，完成时间为：{current_time} *****")

    # 测试用例参数化
    @pytest.mark.parametrize('case', case_list)
    def test_run(self, case):
        print("用例数据", case)
        # 根据条件，从数据库获取url信息，并拼接完整url信息
        url = jwcase_data.loadConfkey('atstudy_okr', 'url_api')['value'] + case['url']
        # 获取method内容
        method = case['method']
        # 获取headers内容,格式化字符为字典
        headers = eval(case['headers'])
        # 获取cookies内容，格式化字符为字典
        cookies = eval(case['cookies'])
        # 获取请求内容，格式化字符为字典
        data = eval(case['request_body'])  # eval对数据要求不能为空
        # 获取关联内容
        relation = str(case['relation'])  # str对数据要求可以为空
        # 获取测试用例名称
        case_name = case['title']
        print(case_name)

        headers = self.correlation(headers)

        # 异常处理
        try:
            # 打印日志
            logger.info("正在执行{}用例".format(case_name))
            # 执行测试用例，发送http请求
            res_data = jwsend_jiekou.send(url, method, data=data, headers=headers, cookies=cookies)
            # 打印日志
            logger.info("用例执行成功，请求的结果为{}".format(res_data))
        # 异常捕获
        except:
            # 打印日志
            logger.info("用例执行失败，请查看日志找原因。")
            # 断言结果为失败
            assert False

        # 判断res_data是否存在
        if res_data:
            # res_data存在后，判断relation不为None
            if relation != "None":
                # 根据响应结果，以及关联信息（token=cookies.admin-token），设置变量token的值为响应结果的信息
                self.set_relation(relation, res_data)  # 将需要关联的数据保留下来
        self.jwassert_response(case, res_data)
        # 返回res_data信息
        return res_data
        # 响应结果关联设置函数
    def set_relation(self, relation, res_data):
        print(f'relation{relation}')
        print(f'res_data{res_data}')
        # 异常处理
        try:
            if relation:
                # 根据=进行分割
                var = relation.split("=")
                # 列表第1个值设置为var_name
                var_name = var[0]
                # 列表第2值内容按.进行分割，结果内容保存变量var_tmp
                var_tmp = var[1]
                print(f"var_tmp{var_tmp}")
                print(f"res_data{res_data}")
                # 在响应结果res_data中，根据条件var_tmp进行匹配
                res = res_data.get("headers").get(var_tmp, "没有var键所对应的值")
                # 打印信息
                print("res的值", res)
                # 把定义的变量名称以及值 以属性的方式设置到DynamicParam类中，实现动态存储
                setattr(DynamicParam, var_name, res)
                #验证：
                #查看是否从结果中提取出了关联数据到DynamicParam
                print("验证是否存放了token数据",var_name,getattr(DynamicParam,var_name,"没有提取到"))
        # 捕获异常
        except:
            print("处理断言失败")

    # 根据关联，获取该变量内容
    def correlation(self, data):
        # 根据正则，获取数据 提取外面有 ${} 数据

        res_data = Base.find(data)
        print("根据正则找到的数据", data)# jwtoken 是动态参数的属性值
        # 判断res_data有数据为True  # True 代表提取到了数据
        if res_data: # 先判断是否有数据
            for i in res_data:# 因为data值是个列表所以要循环遍历
                print("i的结果是",i)
                # 定义空的字典
                replace_dict = {}
                print(i)
                # 根据名称，从DynamicParam动态获取属性值，
                # 这个获取的就是jw_token 对应的值
                # 参数3 返回对象的默认值
                data_tmp = getattr(DynamicParam, str(i), "None")
                print("data_tmp的值是", data_tmp)
                # 把结果更新到字典replace_dict中
                # 这里就是 {jw_token:授权码"}
                replace_dict.update({str(i): data_tmp})
                print("更新后的字典是", replace_dict)
            # 参数进行替换，并把str转换为python对象
                genghuan = Base.relace(data, replace_dict)
                print("jsonloads 之前的数据类型", type(genghuan))
                data = json.loads(genghuan)
                print("jsonloads之后的数据类型", type(data))
            # 注意考虑到有些用例没有数据的 这个data要和if平齐
        return data  #返回的是值

# 结果验证方法
    def jwassert_response(self, case, res_data):
        # 变量初始化为False
        is_pass = False
        # 异常处理，捕获assert抛出的异常，不直接抛出
        try:
            print("jwcase", case)
            print("jwres_data", res_data)
            # 根据结果进行断言验证
            # 验证不同的断言测试点
            print("实际结果1", str(res_data.get('body', "body键没有值").get('msg', "没有msg键")))
            print("实际结果2", str(res_data.get('body', "body键没有值").get('message', "没有message键")))
            print("实际结果3", str(res_data.get('body', "body键没有值").get('success', "没有success键")))
            print("实际结果4", str(res_data.get('code', "code键没有值")))
            ceshijieguo = str(case['expected_code']) in \
                          [str(res_data.get('body').get('msg', "没有msg键")),
                           str(res_data.get('body').get('message', "没有message键")),
                           str(res_data.get('body').get('success', "没有success键")),
                           str(res_data.get('code'))]
            assert ceshijieguo
            # 打印信息
            logger.info("用例断言成功")
            # 设置变量为True
            is_pass = True
        # 捕获异常
        except:
            print("22222")
            # 设置变量为False
            is_pass = False
            # 打印日志
            logger.info("用例断言失败")
        # 无论是否出现异常，都执行下面内容代码
        finally:
            # 把结果更新到数据库
            jwcase_data.updateResults(res_data, is_pass, str(case['id']))
            # 根据变量结果是True/False，进行断言验证，成功则通过，失败则未通过
            assert is_pass
# 主程序执行入口
if __name__ == '__main__':
    pytest.main(['-s', '-v', 'test_run.py'])