"""
定时任务模块，支持定时执行测试用例和接口测试
增强版支持：cron表达式、间隔调度、一次性任务、错误重试、状态跟踪和历史记录
"""
import json
import os
import queue
import time
import threading
import datetime
from typing import Callable, Dict, Any, Optional, Union, List, Tuple
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

import schedule  # 需要安装: pip install schedule
from croniter import croniter  # 需要安装: pip install croniter

from utils.logutil import logger
from utils.concurrencyutil import ConcurrentExecutor


class TaskScheduler:
    """
    增强版任务调度器，管理定时任务
    支持任务状态跟踪、错误重试、执行历史记录和一次性任务
    """
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.scheduler = schedule
        self.running = False
        self.scheduler_thread = None
        self.lock = threading.RLock()
        self.task_id_counter = 0
        self.execution_queue = queue.Queue()
        self.execution_thread = None
        self._stop_event = threading.Event()
    
    def _generate_task_id(self) -> str:
        """生成唯一的任务ID"""
        with self.lock:
            self.task_id_counter += 1
            return f"task_{int(time.time())}_{self.task_id_counter}"
    
    def start(self):
        """
        启动调度器线程和执行线程
        """
        if self.running:
            logger.warning("调度器已经在运行中")
            return
        
        self.running = True
        self._stop_event.clear()
        
        # 启动调度器线程
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        # 启动执行线程
        self.execution_thread = threading.Thread(target=self._execution_worker, daemon=True)
        self.execution_thread.start()
        
        logger.info("任务调度器已启动，包括调度线程和执行线程")
    
    def stop(self):
        """
        停止调度器
        """
        if not self.running:
            logger.warning("调度器已经停止")
            return
        
        self.running = False
        self._stop_event.set()
        
        # 等待调度线程结束
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        # 等待执行线程结束
        if self.execution_thread:
            self.execution_thread.join(timeout=5)
        
        self.scheduler.clear()
        with self.lock:
            self.tasks.clear()
        
        logger.info("任务调度器已停止")
    
    def _run_scheduler(self):
        """
        调度器线程运行函数
        """
        while self.running:
            try:
                self.scheduler.run_pending()
            except Exception as e:
                logger.error(f"调度器运行出错: {str(e)}")
            time.sleep(1)
    
    def _execution_worker(self):
        """
        任务执行工作线程
        负责从队列中取出任务并执行，支持超时控制
        """
        while not self._stop_event.is_set():
            try:
                task_info = self.execution_queue.get(timeout=1)
                task_id = task_info['task_id']
                func = task_info['func']
                args = task_info['args']
                kwargs = task_info['kwargs']
                timeout = task_info.get('timeout')
                max_retries = task_info.get('max_retries', 0)
                retry_count = task_info.get('retry_count', 0)
                
                try:
                    # 更新任务状态为运行中
                    with self.lock:
                        if task_id in self.tasks:
                            self.tasks[task_id]['status'] = 'running'
                            self.tasks[task_id]['last_run_time'] = datetime.datetime.now()
                    
                    logger.info(f"开始执行任务 {task_id}: {task_info.get('name')}")
                    start_time = time.time()
                    
                    # 支持超时控制
                    if timeout:
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(func, *args, **kwargs)
                            result = future.result(timeout=timeout)
                    else:
                        result = func(*args, **kwargs)
                    
                    duration = time.time() - start_time
                    
                    # 更新任务状态为成功
                    with self.lock:
                        if task_id in self.tasks:
                            task = self.tasks[task_id]
                            task['status'] = 'success'
                            task['success_count'] = task.get('success_count', 0) + 1
                            task['last_result'] = result
                            task['retry_count'] = 0
                            
                            # 更新执行历史
                            self._update_execution_history(task_id, True, result, duration)
                    
                    logger.info(f"任务 {task_id} 执行成功，耗时: {duration:.2f}秒")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    error_msg = str(e)
                    
                    logger.error(f"任务 {task_id} 执行失败: {error_msg}")
                    
                    # 错误重试逻辑
                    if retry_count < max_retries:
                        retry_count += 1
                        logger.info(f"任务 {task_id} 将进行第 {retry_count}/{max_retries} 次重试")
                        
                        # 重新放入队列进行重试
                        task_info['retry_count'] = retry_count
                        self.execution_queue.put(task_info)
                    else:
                        # 更新任务状态为失败
                        with self.lock:
                            if task_id in self.tasks:
                                task = self.tasks[task_id]
                                task['status'] = 'failed'
                                task['fail_count'] = task.get('fail_count', 0) + 1
                                task['last_error'] = error_msg
                                task['retry_count'] = 0
                                
                                # 更新执行历史
                                self._update_execution_history(task_id, False, error_msg, duration)
                    
                finally:
                    self.execution_queue.task_done()
                    
            except queue.Empty:
                # 队列为空，继续等待
                pass
            except Exception as e:
                logger.error(f"执行工作线程发生异常: {str(e)}")
    
    def _update_execution_history(self, task_id: str, success: bool, 
                               result: Any = None, duration: float = 0):
        """
        更新任务执行历史
        
        Args:
            task_id: 任务ID
            success: 是否成功
            result: 执行结果或错误信息
            duration: 执行时长
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                history_item = {
                    'timestamp': datetime.datetime.now().isoformat(),
                    'success': success,
                    'result': str(result)[:1000],  # 限制长度
                    'duration': duration,
                    'retry_count': task.get('retry_count', 0)
                }
                
                # 初始化或获取执行历史
                if 'execution_history' not in task:
                    task['execution_history'] = []
                
                # 只保留最近100条历史记录
                task['execution_history'].append(history_item)
                if len(task['execution_history']) > 100:
                    task['execution_history'].pop(0)
    
    def add_interval_task(self, 
                         func: Callable, 
                         seconds: int = 0, 
                         minutes: int = 0, 
                         hours: int = 0, 
                         days: int = 0,
                         args: tuple = (),
                         kwargs: Optional[Dict[str, Any]] = None,
                         task_name: Optional[str] = None,
                         timeout: Optional[int] = None,
                         max_retries: int = 0) -> str:
        """
        添加基于固定时间间隔的定时任务
        
        Args:
            func: 要执行的函数
            seconds: 秒间隔
            minutes: 分钟间隔
            hours: 小时间隔
            days: 天间隔
            args: 函数位置参数
            kwargs: 函数关键字参数
            task_name: 任务名称
            timeout: 任务超时时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            任务ID
        """
        task_id = self._generate_task_id()
        kwargs = kwargs or {}
        name = task_name or func.__name__
        
        # 创建任务执行包装函数
        @wraps(func)
        def task_wrapper():
            task_info = {
                'task_id': task_id,
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'name': name,
                'timeout': timeout,
                'max_retries': max_retries,
                'retry_count': 0
            }
            # 将任务放入执行队列
            self.execution_queue.put(task_info)
        
        # 创建定时任务
        job = self.scheduler.every()
        if days > 0:
            job = job.days
        elif hours > 0:
            job = job.hours
        elif minutes > 0:
            job = job.minutes
        else:
            job = job.seconds
        
        job = job.do(task_wrapper)
        
        with self.lock:
            self.tasks[task_id] = {
                'job': job,
                'func': func,
                'type': 'interval',
                'name': name,
                'created_at': datetime.datetime.now(),
                'active': True,
                'timeout': timeout,
                'max_retries': max_retries,
                'status': 'idle',  # idle, running, success, failed
                'success_count': 0,
                'fail_count': 0
            }
        
        logger.info(f"添加固定间隔任务 {task_id}: {name}, 超时: {timeout}秒, 重试: {max_retries}次")
        return task_id
    
    def add_cron_task(self, 
                     func: Callable,
                     cron_expression: str,
                     args: tuple = (),
                     kwargs: Optional[Dict[str, Any]] = None,
                     task_name: Optional[str] = None,
                     timeout: Optional[int] = None,
                     max_retries: int = 0) -> str:
        """
        添加基于cron表达式的定时任务
        
        Args:
            func: 要执行的函数
            cron_expression: cron表达式，格式：分 时 日 月 周
            args: 函数位置参数
            kwargs: 函数关键字参数
            task_name: 任务名称
            timeout: 任务超时时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            任务ID
        """
        # 验证cron表达式
        try:
            croniter(cron_expression, datetime.datetime.now())
        except Exception as e:
            logger.error(f"无效的cron表达式: {cron_expression}, 错误: {str(e)}")
            raise ValueError(f"无效的cron表达式: {cron_expression}")
        
        task_id = self._generate_task_id()
        kwargs = kwargs or {}
        name = task_name or func.__name__
        
        # 创建任务执行包装函数
        def task_executor():
            task_info = {
                'task_id': task_id,
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'name': name,
                'timeout': timeout,
                'max_retries': max_retries,
                'retry_count': 0
            }
            # 将任务放入执行队列
            self.execution_queue.put(task_info)
        
        # 使用schedule库的every().do()配合自定义的cron检查
        # 我们将使用一个每秒检查的任务来检查cron表达式
        cron = croniter(cron_expression, datetime.datetime.now())
        next_run = cron.get_next(datetime.datetime)
        
        @wraps(func)
        def cron_checker():
            nonlocal next_run
            now = datetime.datetime.now()
            if now >= next_run:
                task_executor()
                next_run = cron.get_next(datetime.datetime)
        
        job = self.scheduler.every(1).seconds.do(cron_checker)
        
        with self.lock:
            self.tasks[task_id] = {
                'job': job,
                'func': func,
                'type': 'cron',
                'expression': cron_expression,
                'name': name,
                'created_at': datetime.datetime.now(),
                'active': True,
                'timeout': timeout,
                'max_retries': max_retries,
                'status': 'idle',
                'success_count': 0,
                'fail_count': 0,
                '_cron_iter': cron,
                '_next_run': next_run
            }
        
        logger.info(f"添加cron任务 {task_id}: {name}, 表达式: {cron_expression}, 超时: {timeout}秒, 重试: {max_retries}次")
        return task_id
    
    def remove_task(self, task_id: str) -> bool:
        """
        移除定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功移除
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"任务 {task_id} 不存在")
                return False
            
            task_info = self.tasks.pop(task_id)
            self.scheduler.cancel_job(task_info['job'])
        
        logger.info(f"移除任务 {task_id}: {task_info['name']}")
        return True
    
    def pause_task(self, task_id: str) -> bool:
        """
        暂停定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功暂停
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"任务 {task_id} 不存在")
                return False
            
            task_info = self.tasks[task_id]
            if not task_info.get('active', True):
                logger.warning(f"任务 {task_id} 已经处于暂停状态")
                return False
            
            self.scheduler.cancel_job(task_info['job'])
            task_info['active'] = False
        
        logger.info(f"暂停任务 {task_id}: {task_info['name']}")
        return True
    
    def resume_task(self, task_id: str) -> bool:
        """
        恢复定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功恢复
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"任务 {task_id} 不存在")
                return False
            
            task_info = self.tasks[task_id]
            if task_info.get('active', True):
                logger.warning(f"任务 {task_id} 已经处于运行状态")
                return False
            
            # 重新创建任务
            if task_info['type'] == 'interval':
                # 重新计算间隔参数（这里简化处理，实际可能需要更复杂的计算）
                # 由于schedule库的限制，我们简单地重新添加任务
                task_info['job'] = self.scheduler.every(1).seconds.do(task_info['func'])
            elif task_info['type'] == 'cron':
                # 对于cron任务，重新创建cron迭代器
                cron = croniter(task_info['expression'], datetime.datetime.now())
                task_info['_cron_iter'] = cron
                task_info['_next_run'] = cron.get_next(datetime.datetime)
                
                @wraps(task_info['func'])
                def cron_checker():
                    nonlocal task_info
                    now = datetime.datetime.now()
                    if now >= task_info['_next_run']:
                        try:
                            task_info['func']()
                        except Exception as e:
                            logger.error(f"cron任务 {task_id} 执行失败: {str(e)}")
                        task_info['_next_run'] = task_info['_cron_iter'].get_next(datetime.datetime)
                
                task_info['job'] = self.scheduler.every(1).seconds.do(cron_checker)
            
            task_info['active'] = True
        
        logger.info(f"恢复任务 {task_id}: {task_info['name']}")
        return True
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息字典
        """
        with self.lock:
            task_info = self.tasks.get(task_id)
            if not task_info:
                return None
            
            # 返回安全的任务信息副本，包含状态和重试信息
            result = {
                'task_id': task_id,
                'name': task_info['name'],
                'type': task_info['type'],
                'active': task_info['active'],
                'created_at': task_info['created_at'],
                'expression': task_info.get('expression'),
                'next_run': task_info.get('_next_run'),
                'status': task_info.get('status', 'idle'),
                'success_count': task_info.get('success_count', 0),
                'fail_count': task_info.get('fail_count', 0),
                'max_retries': task_info.get('max_retries', 0),
                'timeout': task_info.get('timeout')
            }
            
            # 添加最近的执行结果
            if 'last_result' in task_info:
                result['last_result'] = task_info['last_result']
            if 'last_error' in task_info:
                result['last_error'] = task_info['last_error']
            if 'last_run_time' in task_info:
                result['last_run_time'] = task_info['last_run_time']
                
            return result
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        列出所有任务
        
        Returns:
            任务信息列表
        """
        tasks = []
        with self.lock:
            for task_id in self.tasks:
                task_info = self.get_task_info(task_id)
                if task_info:
                    tasks.append(task_info)
        return tasks
        
    def add_one_time_task(self, 
                         func: Callable,
                         delay_seconds: int,
                         args: tuple = (),
                         kwargs: Optional[Dict[str, Any]] = None,
                         task_name: Optional[str] = None,
                         timeout: Optional[int] = None,
                         max_retries: int = 0) -> str:
        """
        添加一次性定时任务
        
        Args:
            func: 要执行的函数
            delay_seconds: 延迟执行时间（秒）
            args: 函数位置参数
            kwargs: 函数关键字参数
            task_name: 任务名称
            timeout: 任务超时时间（秒）
            max_retries: 最大重试次数
            
        Returns:
            任务ID
        """
        task_id = self._generate_task_id()
        kwargs = kwargs or {}
        name = task_name or func.__name__
        
        # 创建任务执行包装函数
        @wraps(func)
        def task_wrapper():
            task_info = {
                'task_id': task_id,
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'name': name,
                'timeout': timeout,
                'max_retries': max_retries,
                'retry_count': 0
            }
            # 将任务放入执行队列
            self.execution_queue.put(task_info)
            
            # 执行完成后移除任务（在实际执行后）
            with self.lock:
                if task_id in self.tasks:
                    self.scheduler.cancel_job(self.tasks[task_id]['job'])
        
        # 创建一次性任务
        job = self.scheduler.every(delay_seconds).seconds.do(task_wrapper)
        
        with self.lock:
            self.tasks[task_id] = {
                'job': job,
                'func': func,
                'type': 'one_time',
                'name': name,
                'created_at': datetime.datetime.now(),
                'active': True,
                'timeout': timeout,
                'max_retries': max_retries,
                'status': 'idle',
                'success_count': 0,
                'fail_count': 0
            }
        
        logger.info(f"添加一次性任务 {task_id}: {name}, 延迟: {delay_seconds}秒, 超时: {timeout}秒, 重试: {max_retries}次")
        return task_id


class ApiTaskScheduler:
    """
    API测试定时任务调度器
    集成HttpClient的定时任务管理
    """
    
    def __init__(self):
        self.scheduler = TaskScheduler()
    
    def start(self):
        """启动调度器"""
        self.scheduler.start()
    
    def stop(self):
        """停止调度器"""
        self.scheduler.stop()
    
    def schedule_api_test(self, 
                         client,  # HttpClient实例
                         method: str,
                         url: str,
                         schedule_type: str = 'interval',
                         interval_seconds: int = 60,
                         cron_expression: str = None,
                         task_name: Optional[str] = None,
                         **request_kwargs) -> str:
        """
        调度API测试任务
        
        Args:
            client: HttpClient实例
            method: 请求方法
            url: 请求URL
            schedule_type: 调度类型，'interval'或'cron'
            interval_seconds: 间隔秒数（当schedule_type为'interval'时）
            cron_expression: cron表达式（当schedule_type为'cron'时）
            task_name: 任务名称
            **request_kwargs: 请求参数
            
        Returns:
            任务ID
        """
        if task_name is None:
            task_name = f"{method.upper()} {url}"
        
        def api_test_task():
            try:
                logger.info(f"执行API测试: {task_name}")
                response = client.send_request(method, url, **request_kwargs)
                if response:
                    logger.info(f"API测试结果 - URL: {url}, 状态码: {response.status_code}, 响应时间: {response.elapsed.total_seconds():.3f}s")
                return response
            except Exception as e:
                logger.error(f"API测试失败: {str(e)}")
        
        if schedule_type == 'interval':
            return self.scheduler.add_interval_task(
                api_test_task,
                seconds=interval_seconds,
                task_name=task_name
            )
        elif schedule_type == 'cron':
            if not cron_expression:
                raise ValueError("使用cron类型调度时必须提供cron表达式")
            return self.scheduler.add_cron_task(
                api_test_task,
                cron_expression=cron_expression,
                task_name=task_name
            )
        else:
            raise ValueError(f"不支持的调度类型: {schedule_type}")
    
    def schedule_batch_test(self, 
                           client,  # HttpClient实例
                           test_configs: List[Dict[str, Any]],
                           schedule_type: str = 'interval',
                           interval_seconds: int = 60,
                           cron_expression: str = None,
                           task_name: Optional[str] = None) -> str:
        """
        调度批量API测试任务
        
        Args:
            client: HttpClient实例
            test_configs: 测试配置列表，每个配置包含method, url等
            schedule_type: 调度类型
            interval_seconds: 间隔秒数
            cron_expression: cron表达式
            task_name: 任务名称
            
        Returns:
            任务ID
        """
        if task_name is None:
            task_name = f"批量API测试 ({len(test_configs)}个接口)"
        
        def batch_test_task():
            results = []
            for config in test_configs:
                try:
                    method = config.pop('method', 'GET')
                    url = config.pop('url', '')
                    logger.info(f"执行批量测试中的API: {method.upper()} {url}")
                    response = client.send_request(method, url, **config)
                    if response:
                        logger.info(f"批量测试API结果 - URL: {url}, 状态码: {response.status_code}")
                    results.append((url, response))
                except Exception as e:
                    logger.error(f"批量测试API失败: {str(e)}")
                    results.append((config.get('url', 'unknown'), None))
            return results
        
        if schedule_type == 'interval':
            return self.scheduler.add_interval_task(
                batch_test_task,
                seconds=interval_seconds,
                task_name=task_name
            )
        elif schedule_type == 'cron':
            if not cron_expression:
                raise ValueError("使用cron类型调度时必须提供cron表达式")
            return self.scheduler.add_cron_task(
                batch_test_task,
                cron_expression=cron_expression,
                task_name=task_name
            )
        else:
            raise ValueError(f"不支持的调度类型: {schedule_type}")
    
    # 复用TaskScheduler的方法
    def remove_task(self, task_id: str) -> bool:
        return self.scheduler.remove_task(task_id)
    
    def pause_task(self, task_id: str) -> bool:
        return self.scheduler.pause_task(task_id)
    
    def resume_task(self, task_id: str) -> bool:
        return self.scheduler.resume_task(task_id)
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.scheduler.get_task_info(task_id)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        return self.scheduler.list_tasks()


class TestCaseScheduler(TaskScheduler):
    """
    专门用于测试用例调度的调度器
    支持测试套件管理、批量执行和测试报告生成
    """
    def __init__(self):
        super().__init__()
        self.test_suites = {}  # 测试套件管理
        self.report_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        os.makedirs(self.report_dir, exist_ok=True)
    
    def add_test_suite(self, suite_name: str, test_cases: list):
        """
        添加测试套件
        
        Args:
            suite_name: 测试套件名称
            test_cases: 测试用例列表，每个元素为(test_case_func, args, kwargs)元组
        """
        self.test_suites[suite_name] = test_cases
        logger.info(f"添加测试套件 '{suite_name}'，包含 {len(test_cases)} 个测试用例")
    
    def remove_test_suite(self, suite_name: str):
        """
        移除测试套件
        
        Args:
            suite_name: 测试套件名称
        """
        if suite_name in self.test_suites:
            del self.test_suites[suite_name]
            logger.info(f"移除测试套件 '{suite_name}'")
        else:
            logger.warning(f"测试套件 '{suite_name}' 不存在")
    
    def run_test_suite(self, suite_name: str):
        """
        立即运行测试套件
        
        Args:
            suite_name: 测试套件名称
            
        Returns:
            dict: 测试报告
        """
        if suite_name not in self.test_suites:
            logger.error(f"测试套件 '{suite_name}' 不存在")
            return {'suite_name': suite_name, 'success': False, 'error': '测试套件不存在'}
        
        logger.info(f"开始运行测试套件 '{suite_name}'")
        test_results = []
        suite_start_time = time.time()
        
        # 使用并发执行器执行测试用例
        with ConcurrentExecutor(max_workers=5) as executor:
            future_to_test = {}
            
            for i, (test_case_func, args, kwargs) in enumerate(self.test_suites[suite_name]):
                # 为每个测试用例创建一个包装函数
                def test_wrapper(func, test_args, test_kwargs, test_idx=i):
                    try:
                        start_time = time.time()
                        result = func(*test_args, **test_kwargs)
                        duration = time.time() - start_time
                        
                        # 统一测试结果格式
                        if isinstance(result, bool):
                            result = {'success': result, 'message': '测试通过' if result else '测试失败'}
                        elif not isinstance(result, dict):
                            result = {'success': True, 'message': str(result)}
                        
                        result['test_name'] = func.__name__
                        result['test_index'] = test_idx
                        result['duration'] = duration
                        result['timestamp'] = datetime.datetime.now().isoformat()
                        
                        return result
                    except Exception as e:
                        return {
                            'test_name': func.__name__,
                            'test_index': test_idx,
                            'success': False,
                            'error': str(e),
                            'timestamp': datetime.datetime.now().isoformat(),
                            'duration': time.time() - start_time
                        }
                
                # 提交到并发执行器
                future = executor.submit(test_wrapper, test_case_func, args or (), kwargs or {})
                future_to_test[future] = test_case_func.__name__
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_test):
                test_name = future_to_test[future]
                try:
                    result = future.result()
                    test_results.append(result)
                    logger.info(f"测试用例 '{test_name}' 执行完成: {'成功' if result.get('success') else '失败'}")
                except Exception as e:
                    test_results.append({
                        'test_name': test_name,
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    logger.error(f"测试用例 '{test_name}' 执行异常: {str(e)}")
        
        # 生成测试报告
        report = self._generate_test_suite_report(suite_name, test_results, time.time() - suite_start_time)
        
        # 保存报告
        self._save_test_report(report)
        
        return report
    
    def schedule_test_suite(self, 
                           suite_name: str,
                           interval_seconds: int = None,
                           cron_expression: str = None,
                           delay_seconds: int = None):
        """
        调度测试套件执行
        
        Args:
            suite_name: 测试套件名称
            interval_seconds: 固定间隔（秒）
            cron_expression: cron表达式
            delay_seconds: 一次性任务延迟（秒）
            
        Returns:
            str: 任务ID
        """
        if suite_name not in self.test_suites:
            raise ValueError(f"测试套件 '{suite_name}' 不存在")
        
        # 创建包装函数
        def run_suite_wrapper():
            return self.run_test_suite(suite_name)
        
        # 根据参数选择调度方式
        if interval_seconds:
            return self.add_interval_task(
                run_suite_wrapper,
                interval_seconds,
                name=f"测试套件-{suite_name}",
                timeout=3600,  # 测试套件超时时间（秒）
                max_retries=1
            )
        elif cron_expression:
            return self.add_cron_task(
                run_suite_wrapper,
                cron_expression,
                name=f"测试套件-{suite_name}",
                timeout=3600,
                max_retries=1
            )
        elif delay_seconds:
            return self.add_one_time_task(
                run_suite_wrapper,
                delay_seconds,
                name=f"测试套件-{suite_name}",
                timeout=3600,
                max_retries=1
            )
        else:
            raise ValueError("必须指定interval_seconds、cron_expression或delay_seconds")
    
    def _generate_test_suite_report(self, suite_name, test_results, duration):
        """
        生成测试套件报告
        """
        total = len(test_results)
        passed = sum(1 for r in test_results if r.get('success', False))
        failed = total - passed
        
        report = {
            'suite_name': suite_name,
            'timestamp': datetime.datetime.now().isoformat(),
            'duration': duration,
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'test_results': sorted(test_results, key=lambda x: x.get('test_index', 0))
        }
        
        return report
    
    def _save_test_report(self, report):
        """
        保存测试报告到文件
        """
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"test_suite_{report['suite_name']}_{timestamp}.json"
        file_path = os.path.join(self.report_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"测试报告已保存到: {file_path}")
        except Exception as e:
            logger.error(f"保存测试报告失败: {str(e)}")
    
    def get_latest_reports(self, count=5):
        """
        获取最近的测试报告
        
        Args:
            count: 返回报告数量
            
        Returns:
            list: 报告列表
        """
        try:
            reports = []
            for filename in os.listdir(self.report_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.report_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        report['file_path'] = file_path
                        report['file_name'] = filename
                        reports.append(report)
            
            # 按时间排序
            reports.sort(key=lambda x: x['timestamp'], reverse=True)
            return reports[:count]
        except Exception as e:
            logger.error(f"获取测试报告失败: {str(e)}")
            return []


# 创建全局调度器实例
global_scheduler = TaskScheduler()
global_api_scheduler = ApiTaskScheduler()


def schedule_interval(func: Callable, 
                     seconds: int = 0,
                     minutes: int = 0,
                     hours: int = 0,
                     days: int = 0,
                     args: tuple = (),
                     kwargs: Optional[Dict[str, Any]] = None,
                     task_name: Optional[str] = None) -> str:
    """
    装饰器：使用固定时间间隔调度函数
    
    Args:
        func: 要调度的函数
        seconds: 秒间隔
        minutes: 分钟间隔
        hours: 小时间隔
        days: 天间隔
        args: 函数位置参数
        kwargs: 函数关键字参数
        task_name: 任务名称
        
    Returns:
        任务ID
    """
    task_id = global_scheduler.add_interval_task(
        func, seconds, minutes, hours, days, args, kwargs, task_name
    )
    return task_id


def schedule_cron(func: Callable,
                  cron_expression: str,
                  args: tuple = (),
                  kwargs: Optional[Dict[str, Any]] = None,
                  task_name: Optional[str] = None) -> str:
    """
    装饰器：使用cron表达式调度函数
    
    Args:
        func: 要调度的函数
        cron_expression: cron表达式
        args: 函数位置参数
        kwargs: 函数关键字参数
        task_name: 任务名称
        
    Returns:
        任务ID
    """
    task_id = global_scheduler.add_cron_task(
        func, cron_expression, args, kwargs, task_name
    )
    return task_id


# 确保在导入时启动全局调度器
global_scheduler.start()


# 示例使用
if __name__ == '__main__':
    """
    示例：如何使用定时任务功能
    """
    
    def test_function(name="World"):
        print(f"Hello, {name}! Current time: {datetime.datetime.now()}")
    
    # 创建调度器
    scheduler = TaskScheduler()
    scheduler.start()
    
    # 添加间隔任务（每5秒执行一次）
    task1_id = scheduler.add_interval_task(
        test_function,
        seconds=5,
        args=(),
        kwargs={"name": "Interval Task"},
        task_name="示例间隔任务"
    )
    print(f"添加间隔任务，ID: {task1_id}")
    
    # 添加cron任务（每分钟执行一次）
    task2_id = scheduler.add_cron_task(
        test_function,
        cron_expression="* * * * *",  # 每分钟执行一次
        args=(),
        kwargs={"name": "Cron Task"},
        task_name="示例Cron任务"
    )
    print(f"添加Cron任务，ID: {task2_id}")
    
    # 列出所有任务
    print("\n当前任务列表:")
    for task in scheduler.list_tasks():
        print(f"- {task['task_id']}: {task['name']} (类型: {task['type']}, 活跃: {task['active']})")
    
    try:
        print("\n调度器运行中，按Ctrl+C停止...")
        # 运行15秒后暂停第一个任务
        time.sleep(15)
        print(f"\n暂停任务: {task1_id}")
        scheduler.pause_task(task1_id)
        
        # 再过15秒后恢复第一个任务
        time.sleep(15)
        print(f"\n恢复任务: {task1_id}")
        scheduler.resume_task(task1_id)
        
        # 再过15秒后停止
        time.sleep(15)
    except KeyboardInterrupt:
        print("\n接收到中断信号，停止调度器...")
    finally:
        scheduler.stop()
        print("调度器已停止")