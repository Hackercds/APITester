"""
数据库工具模块
"""
import pymysql
import pymysql.cursors
from typing import Dict, List, Any, Optional, Union, Tuple
from contextlib import contextmanager
from config.settings import DB_CONFIG

# 导入日志工具
# 假设utils.logutil模块存在，如果不存在可以注释掉
# from utils.logutil import logger


class DatabaseUtil:
    """
    数据库工具类，提供数据库连接和操作功能
    """
    
    def __init__(self, **kwargs):
        """
        初始化数据库连接配置
        
        Args:
            **kwargs: 数据库连接参数，默认为从DB_CONFIG读取
        """
        # 如果没有提供参数，使用配置文件中的参数
        self.config = kwargs if kwargs else DB_CONFIG
        self.conn = None
        self.cursor = None
        self._connect()
    
    def _connect(self) -> None:
        """
        建立数据库连接
        """
        try:
            self.conn = pymysql.connect(
                **self.config,
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cursor = self.conn.cursor()
            print("数据库连接成功")
            # logger.info(f"数据库连接成功: {self.config.get('host')}:{self.config.get('port')}/{self.config.get('database')}")
        except Exception as e:
            error_msg = f"数据库连接失败: {str(e)}"
            print(error_msg)
            # logger.error(error_msg)
            raise Exception(error_msg)
    
    def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        执行查询语句
        
        Args:
            sql: SQL查询语句
            params: SQL参数，用于防止SQL注入
            
        Returns:
            查询结果列表
        """
        try:
            if params:
                self.cursor.execute(sql, params)
                print(f"执行查询语句: {sql}，参数: {params}")
                # logger.info(f"执行查询语句: {sql}，参数: {params}")
            else:
                self.cursor.execute(sql)
                print(f"执行查询语句: {sql}")
                # logger.info(f"执行查询语句: {sql}")
            
            result = self.cursor.fetchall()
            return result
        except Exception as e:
            error_msg = f"查询语句执行失败: {str(e)}"
            print(error_msg)
            # logger.error(error_msg)
            raise Exception(error_msg)
    
    def execute_update(self, sql: str, params: Optional[Tuple] = None) -> int:
        """
        执行更新语句（insert、update、delete）
        
        Args:
            sql: SQL更新语句
            params: SQL参数，用于防止SQL注入
            
        Returns:
            受影响的行数
        """
        try:
            if params:
                affected_rows = self.cursor.execute(sql, params)
                print(f"执行更新语句: {sql}，参数: {params}")
                # logger.info(f"执行更新语句: {sql}，参数: {params}")
            else:
                affected_rows = self.cursor.execute(sql)
                print(f"执行更新语句: {sql}")
                # logger.info(f"执行更新语句: {sql}")
                
            self.conn.commit()
            print("sql执行成功～！")
            return affected_rows
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            error_msg = f"更新语句执行失败: {str(e)}"
            print(error_msg)
            # logger.error(error_msg)
            raise Exception(error_msg)
    
    def execute_batch(self, sql: str, params_list: List[Tuple]) -> int:
        """
        批量执行更新语句
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            
        Returns:
            受影响的行数
        """
        try:
            affected_rows = self.cursor.executemany(sql, params_list)
            self.conn.commit()
            print(f"批量执行语句: {sql}，参数数量: {len(params_list)}")
            # logger.info(f"批量执行语句: {sql}，参数数量: {len(params_list)}")
            return affected_rows
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            error_msg = f"批量语句执行失败: {str(e)}"
            print(error_msg)
            # logger.error(error_msg)
            raise Exception(error_msg)
    
    def close(self) -> None:
        """
        关闭数据库连接
        """
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.conn:
                self.conn.close()
                self.conn = None
            print("数据库连接已关闭")
            # logger.info("数据库连接已关闭")
        except Exception as e:
            print(f"数据库连接关闭失败: {str(e)}")
            # logger.error(f"数据库连接关闭失败: {str(e)}")
    
    def get_count(self, sql: str, params: Optional[Tuple] = None) -> int:
        """
        获取查询结果数量
        
        Args:
            sql: SQL查询语句
            params: SQL参数
            
        Returns:
            结果数量
        """
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
                
            result = self.cursor.fetchone()
            if result and isinstance(result, dict):
                return list(result.values())[0] if result else 0
            elif result:
                return result[0] if result else 0
            return 0
        except Exception as e:
            error_msg = f"获取数据数量失败: {str(e)}"
            print(error_msg)
            # logger.error(error_msg)
            raise Exception(error_msg)
    
    # 兼容旧版本的方法
    def get_fetchone(self, sql: str):
        """获取单条数据（兼容旧版本）"""
        try:
            self.cursor.execute(sql)
            return self.cursor.fetchone()
        except Exception as e:
            print(f"获取单条数据失败: {str(e)}")
            return None
    
    def get_fetchall(self, sql: str):
        """获取多条数据（兼容旧版本）"""
        try:
            self.cursor.execute(sql)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"获取多条数据失败: {str(e)}")
            return None
    
    def sql_execute(self, sql: str):
        """执行更新类sql（兼容旧版本）"""
        try:
            if self.conn and self.cursor:
                print("sql是", sql)
                self.cursor.execute(sql)
                self.conn.commit()
                print("sql执行成功～！")
                return True
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            print(f"sql执行失败: {str(e)}")
            return False
    
    def __del__(self):
        """析构函数，确保连接关闭"""
        self.close()


# 为了向后兼容，保留MysqlUtil类
class MysqlUtil(DatabaseUtil):
    """MySQL工具类（向后兼容）"""
    pass


@contextmanager
def get_db_connection(**kwargs) -> DatabaseUtil:
    """
    数据库连接上下文管理器
    
    Args:
        **kwargs: 数据库连接参数
        
    Yields:
        DatabaseUtil实例
    """
    db = DatabaseUtil(**kwargs)
    try:
        yield db
    finally:
        db.close()

def get_db_util(**kwargs) -> DatabaseUtil:
    """
    获取数据库工具实例
    
    Args:
        **kwargs: 数据库连接参数
        
    Returns:
        DatabaseUtil实例
    """
    return DatabaseUtil(**kwargs)

# 测试代码
if __name__ == '__main__':


    # 验证编写的方法

    mysql = MysqlUtil()
    res1=mysql.get_fetchone("select * from jwtest_case_list")
    print(res1)
    res2 = mysql.get_fetchall("select * from jwtest_case_list")
    print(res2)
    res3=mysql.sql_execute("insert into jwtest_result_record (case_id,result) values ('9999','测试通过');")
    print(res3)