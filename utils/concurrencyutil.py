import time
import threading
import asyncio
from queue import Queue
import concurrent.futures
from contextlib import contextmanager
from typing import Dict, List, Callable, Any, Optional, Union
import logging
import statistics
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('concurrencyutil')


class RateLimiter:
    """
    速率限制器，用于精确控制TPS/QPS
    支持固定速率模式和令牌桶算法，增强统计和监控功能
    """
    def __init__(self, rate: int, time_unit: float = 1.0, mode: str = 'fixed', burst_capacity: Optional[int] = None):
        """
        初始化速率限制器
        
        Args:
            rate: 单位时间内允许的请求数量
            time_unit: 时间单位（秒），默认1秒
            mode: 限流模式，'fixed'表示固定间隔，'token_bucket'表示令牌桶算法
            burst_capacity: 令牌桶突发容量（仅在token_bucket模式下生效），默认等于rate
        """
        self.rate = rate
        self.time_unit = time_unit
        self.mode = mode
        self.interval = time_unit / rate if rate > 0 else 0
        self.last_request_time = 0
        self.lock = threading.RLock()
        
        # 令牌桶参数
        self.capacity = burst_capacity if burst_capacity is not None else rate
        self.tokens = self.capacity  # 初始填满令牌桶
        self.last_token_time = time.time()
        
        # 增强的统计信息
        self.request_count = 0
        self.rejected_count = 0
        self.start_time = time.time()
        self.request_timestamps = []
        self.wait_times = []  # 记录每个请求的等待时间
        
        # 滑动窗口参数
        self.window_size = 1.0  # 默认1秒滑动窗口
        self.window_requests = []
        
    def _add_tokens(self):
        """添加令牌到令牌桶"""
        now = time.time()
        elapsed = now - self.last_token_time
        
        if elapsed > 0:
            new_tokens = elapsed * (self.capacity / self.time_unit)
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_token_time = now
    
    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        等待直到可以发送下一个请求
        
        Args:
            timeout: 超时时间（秒），如果为None则无限等待
            
        Returns:
            bool: True表示成功获取令牌，False表示超时
        """
        start_wait_time = time.time()
        
        with self.lock:
            if self.mode == 'fixed':
                # 固定间隔模式
                now = time.time()
                elapsed_since_last = now - self.last_request_time
                wait_time = max(0, self.interval - elapsed_since_last)
                
                # 检查是否超时
                if timeout is not None and wait_time > timeout:
                    self.rejected_count += 1
                    return False
                
                if wait_time > 0:
                    time.sleep(wait_time)
                    self.last_request_time = time.time()
                else:
                    self.last_request_time = now
                    
            elif self.mode == 'token_bucket':
                # 令牌桶模式
                self._add_tokens()
                
                # 尝试获取令牌
                if self.tokens < 1:
                    # 计算需要等待的时间
                    wait_time = (1 - self.tokens) * (self.time_unit / self.capacity)
                    
                    # 检查是否超时
                    if timeout is not None and wait_time > timeout:
                        self.rejected_count += 1
                        return False
                    
                    # 等待直到有令牌可用
                    time.sleep(wait_time)
                    self._add_tokens()
                
                # 消耗一个令牌
                self.tokens -= 1
            
            # 记录请求信息
            self.request_count += 1
            current_time = time.time()
            self.request_timestamps.append(current_time)
            self.wait_times.append(current_time - start_wait_time)
            
            # 更新滑动窗口
            self._update_sliding_window(current_time)
            
            # 清理旧数据
            self._cleanup_old_data(current_time)
            
            return True
    
    def _update_sliding_window(self, current_time: float):
        """更新滑动窗口数据"""
        # 移除过期的请求记录
        self.window_requests = [ts for ts in self.window_requests if current_time - ts <= self.window_size]
        self.window_requests.append(current_time)
    
    def _cleanup_old_data(self, current_time: float):
        """清理旧数据，保持内存使用合理"""
        # 只保留最近1000个时间戳和等待时间
        if len(self.request_timestamps) > 1000:
            self.request_timestamps = self.request_timestamps[-1000:]
        
        if len(self.wait_times) > 1000:
            self.wait_times = self.wait_times[-1000:]
    
    def get_current_tps(self) -> float:
        """
        获取当前TPS（每秒事务数），使用滑动窗口计算
        
        Returns:
            当前TPS值
        """
        if len(self.window_requests) < 2:
            return 0.0
        
        now = time.time()
        # 只考虑窗口内的请求
        window_start = now - self.window_size
        valid_requests = [ts for ts in self.window_requests if ts >= window_start]
        
        if len(valid_requests) < 2:
            return 0.0
        
        # 计算实际TPS
        time_span = now - valid_requests[0]
        return len(valid_requests) / max(0.001, time_span)  # 避免除零
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取速率限制器的详细统计信息
        
        Returns:
            包含详细统计信息的字典
        """
        now = time.time()
        total_time = now - self.start_time
        avg_tps = self.request_count / total_time if total_time > 0 else 0
        
        # 计算等待时间统计
        avg_wait_time = statistics.mean(self.wait_times) if self.wait_times else 0
        p95_wait_time = self._calculate_percentile(self.wait_times, 95) if self.wait_times else 0
        p99_wait_time = self._calculate_percentile(self.wait_times, 99) if self.wait_times else 0
        
        return {
            'total_requests': self.request_count,
            'rejected_requests': self.rejected_count,
            'total_time': total_time,
            'average_tps': avg_tps,
            'current_tps': self.get_current_tps(),
            'configured_rate': self.rate / self.time_unit,
            'mode': self.mode,
            'average_wait_time_ms': avg_wait_time * 1000,
            'p95_wait_time_ms': p95_wait_time * 1000,
            'p99_wait_time_ms': p99_wait_time * 1000,
            'window_size': self.window_size
        }
    
    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """
        计算百分位数
        
        Args:
            data: 数据列表
            percentile: 百分位数（如95、99）
            
        Returns:
            百分位数值
        """
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        
        # 确保索引有效
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        
        return sorted_data[index]
    
    def __enter__(self):
        self.wait()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def get_current_tps(self) -> float:
        """
        获取当前TPS（每秒事务数）
        
        Returns:
            当前TPS值
        """
        if len(self.request_timestamps) < 2:
            return 0.0
        
        # 计算最近1秒内的请求数
        now = time.time()
        recent_requests = [ts for ts in self.request_timestamps if now - ts <= 1.0]
        
        if len(recent_requests) < 2:
            return 0.0
        
        # 计算实际TPS
        return len(recent_requests) / max(1.0, now - recent_requests[0])
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取速率限制器的统计信息
        
        Returns:
            包含统计信息的字典
        """
        now = time.time()
        total_time = now - self.start_time
        avg_tps = self.request_count / total_time if total_time > 0 else 0
        
        return {
            'total_requests': self.request_count,
            'total_time': total_time,
            'average_tps': avg_tps,
            'current_tps': self.get_current_tps(),
            'configured_rate': self.rate / self.time_unit,
            'mode': self.mode
        }
    
    def update_rate(self, new_rate: int):
        """
        动态更新速率限制
        
        Args:
            new_rate: 新的速率限制
        """
        with self.lock:
            self.rate = new_rate
            self.capacity = new_rate
            self.interval = self.time_unit / new_rate if new_rate > 0 else 0
            # 重新填充令牌桶
            self._add_tokens()


class ConcurrentExecutor:
    """
    高级并发执行器，用于精确管理并发请求和控制TPS/QPS
    支持自适应并发控制、详细统计和错误处理
    """
    def __init__(self, max_workers: int = 10, rate_limiter: Optional[RateLimiter] = None, 
                 executor_type: str = 'thread'):
        """
        初始化并发执行器
        
        Args:
            max_workers: 最大工作线程数
            rate_limiter: 速率限制器实例
            executor_type: 执行器类型，'thread'或'process'
        """
        self.max_workers = max_workers
        self.rate_limiter = rate_limiter
        self.executor_type = executor_type
        self.executor = None
        self.results_queue = Queue()
        self.active_tasks = 0
        self.tasks_lock = threading.Lock()
        self.executor_lock = threading.RLock()
        
        # 增强的任务执行统计
        self.task_times = []
        self.task_errors = 0
        self.total_tasks = 0
        self.successful_tasks = 0
        self.start_time = time.time()
        self.last_task_completion_time = time.time()
        
        # 错误类型统计
        self.error_types = defaultdict(int)
        
        # 增强的自适应并发控制参数
        self.adaptive_concurrency = False
        self.target_tps = None
        self.min_concurrency = 1
        self.max_concurrency = max_workers
        self.concurrency_adjustment_interval = 2.0  # 秒
        self.last_adjustment_time = time.time()
        self.concurrency_history = [(max_workers, time.time())]  # 记录并发数调整历史
        self.error_threshold = 0.05  # 错误率阈值5%
        
        # 延迟初始化executor
        self._initialize_executor()
    
    def _initialize_executor(self):
        """初始化执行器"""
        with self.executor_lock:
            if self.executor is None:
                if self.executor_type == 'process':
                    self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers)
                else:
                    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        
    def _worker_wrapper(self, func: Callable, *args, **kwargs):
        """
        增强的工作线程包装器，添加速率限制、结果收集和详细统计
        """
        task_start_time = time.time()
        task_id = kwargs.pop('__task_id__', id(args))  # 可选的任务ID，从kwargs中移除
        
        try:
            # 更新活动任务计数
            with self.tasks_lock:
                self.active_tasks += 1
            
            # 应用速率限制
            if self.rate_limiter:
                if not self.rate_limiter.wait():
                    raise Exception("Rate limiting timeout")
            
            # 执行实际函数
            result = func(*args, **kwargs)
            
            # 记录成功任务
            with self.tasks_lock:
                self.successful_tasks += 1
            
            # 将结果放入队列，包含任务ID
            self.results_queue.put((task_id, args, kwargs, result, None))
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            # 记录错误信息并统计错误类型
            with self.tasks_lock:
                self.task_errors += 1
                # 捕获错误类型
                error_type = type(e).__name__
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
            
            # 将错误放入队列，包含任务ID
            self.results_queue.put((task_id, args, kwargs, None, e))
        finally:
            # 减少活动任务计数并更新统计
            with self.tasks_lock:
                self.active_tasks -= 1
                self.total_tasks += 1  # 增加总任务计数
                task_time = time.time() - task_start_time
                self.task_times.append(task_time)
                self.last_task_completion_time = time.time()
                # 只保留最近1000个任务时间
                if len(self.task_times) > 1000:
                    self.task_times.pop(0)
            
            # 动态调整并发数
            if self.adaptive_concurrency:
                self._adjust_concurrency()
    
    def _adjust_concurrency(self):
        """
        增强的动态并发调整算法，结合错误率、TPS和历史数据进行智能调整
        """
        if not self.adaptive_concurrency or self.target_tps is None:
            return
        
        now = time.time()
        if now - self.last_adjustment_time < self.concurrency_adjustment_interval:
            return
        
        current_tps = self.get_current_tps()
        with self.tasks_lock:
            current_workers = self.max_workers
            
            # 计算当前错误率
            error_rate = 0.0
            if self.total_tasks > 0:
                error_rate = self.task_errors / self.total_tasks
            
            # 基于错误率和TPS的智能调整算法
            if error_rate > self.error_threshold:
                # 错误率过高，立即降低并发
                new_workers = max(self.min_concurrency, current_workers - 1)
                if new_workers != current_workers:
                    self.max_workers = new_workers
                    logger.warning(f"错误率过高({error_rate:.2%})，降低并发数到 {new_workers}")
                    # 记录调整历史
                    self.concurrency_history.append((new_workers, now))
                    # 如果并发数改变，需要重启执行器
                    if self.executor:
                        self.executor.shutdown(wait=False)
                    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
            elif current_tps < self.target_tps * 0.9 and current_workers < self.max_concurrency:
                # TPS过低且错误率正常，适度增加并发数
                new_workers = min(self.max_concurrency, current_workers + 1)
                # 避免快速震荡，检查历史记录
                if len(self.concurrency_history) > 0 and now - self.concurrency_history[-1][1] > 10:  # 至少10秒内不重复调整
                    self.max_workers = new_workers
                    logger.info(f"增加并发数到 {new_workers}，当前TPS: {current_tps:.2f}")
                    self.concurrency_history.append((new_workers, now))
                    # 如果并发数改变，需要重启执行器
                    if self.executor:
                        self.executor.shutdown(wait=False)
                    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
            elif current_tps > self.target_tps * 1.2:
                # TPS显著过高，适当降低并发
                new_workers = max(self.min_concurrency, current_workers - 1)
                self.max_workers = new_workers
                logger.info(f"TPS过高，降低并发数到 {new_workers}")
                self.concurrency_history.append((new_workers, now))
                # 如果并发数改变，需要重启执行器
                if self.executor:
                    self.executor.shutdown(wait=False)
                self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
            
            # 清理历史记录，只保留最近100条
            if len(self.concurrency_history) > 100:
                self.concurrency_history = self.concurrency_history[-100:]
                
            self.last_adjustment_time = now
    
    def submit(self, func: Callable, *args, **kwargs):
        """
        提交一个任务到执行器
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
        """
        if self.executor is None:
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        
        with self.tasks_lock:
            self.active_tasks += 1
            self.total_tasks += 1
        
        return self.executor.submit(self._worker_wrapper, func, *args, **kwargs)
    
    def map(self, func: Callable, *iterables, timeout: Optional[float] = None, chunksize: int = 1):
        """
        映射函数到可迭代对象
        
        Args:
            func: 要执行的函数
            *iterables: 可迭代对象
            timeout: 超时时间
            chunksize: 块大小
        
        Returns:
            结果迭代器
        """
        if self.executor is None:
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        
        # 包装原始函数以应用速率限制
        def wrapped_func(*args, **kwargs):
            if self.rate_limiter:
                self.rate_limiter.wait()
            return func(*args, **kwargs)
        
        with self.tasks_lock:
            self.total_tasks += len(iterables[0])
        
        return self.executor.map(wrapped_func, *iterables, timeout=timeout, chunksize=chunksize)
    
    def wait_completion(self, collect_results: bool = True):
        """
        等待所有任务完成
        
        Args:
            collect_results: 是否收集结果
            
        Returns:
            如果collect_results为True，返回结果列表
        """
        # 等待所有活动任务完成
        while True:
            with self.tasks_lock:
                if self.active_tasks == 0:
                    break
            time.sleep(0.01)
        
        if collect_results:
            results = []
            while not self.results_queue.empty():
                results.append(self.results_queue.get())
            return results
        
        return None
    
    def shutdown(self, wait: bool = True):
        """
        关闭执行器
        
        Args:
            wait: 是否等待所有任务完成
        """
        if self.executor:
            self.executor.shutdown(wait=wait)
    
    def get_current_tps(self) -> float:
        """
        获取当前TPS（每秒事务数）
        
        Returns:
            当前TPS值
        """
        if len(self.task_times) < 2:
            return 0.0
        
        # 计算平均任务执行时间
        avg_task_time = statistics.mean(self.task_times) if self.task_times else 0
        
        # 根据当前并发数和平均任务时间估算TPS
        if avg_task_time > 0:
            return self.active_tasks / avg_task_time
        
        return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取执行器的统计信息
        
        Returns:
            包含统计信息的字典
        """
        now = time.time()
        total_time = now - self.start_time
        
        # 计算任务时间统计
        if self.task_times:
            min_time = min(self.task_times)
            max_time = max(self.task_times)
            avg_time = statistics.mean(self.task_times)
            try:
                p95_time = sorted(self.task_times)[int(len(self.task_times) * 0.95)]
                p99_time = sorted(self.task_times)[int(len(self.task_times) * 0.99)]
            except:
                p95_time = avg_time
                p99_time = avg_time
        else:
            min_time = max_time = avg_time = p95_time = p99_time = 0
        
        success_rate = ((self.total_tasks - self.task_errors) / self.total_tasks * 100) if self.total_tasks > 0 else 0
        
        stats = {
            'total_tasks': self.total_tasks,
            'successful_tasks': self.total_tasks - self.task_errors,
            'failed_tasks': self.task_errors,
            'success_rate': success_rate,
            'total_time': total_time,
            'avg_task_time': avg_time,
            'min_task_time': min_time,
            'max_task_time': max_time,
            'p95_task_time': p95_time,
            'p99_task_time': p99_time,
            'current_concurrency': self.active_tasks,
            'max_concurrency': self.max_workers,
            'adaptive_concurrency': self.adaptive_concurrency,
            'target_tps': self.target_tps,
            'current_tps': self.get_current_tps()
        }
        
        # 如果有速率限制器，添加其统计信息
        if self.rate_limiter:
            stats['rate_limiter'] = self.rate_limiter.get_stats()
        
        return stats
    
    def enable_adaptive_concurrency(self, target_tps: float, min_concurrency: int = 1, 
                                   max_concurrency: Optional[int] = None, 
                                   error_threshold: float = 0.05, 
                                   adjustment_interval: float = 2.0):
        """
        增强的自适应并发控制
        
        Args:
            target_tps: 目标TPS
            min_concurrency: 最小并发数
            max_concurrency: 最大并发数（如果为None则使用当前最大并发数）
            error_threshold: 错误率阈值，超过此阈值将降低并发数
            adjustment_interval: 并发数调整间隔（秒）
        """
        self.adaptive_concurrency = True
        self.target_tps = target_tps
        self.min_concurrency = max(1, min_concurrency)
        self.max_concurrency = max_concurrency if max_concurrency is not None else self.max_workers
        self.error_threshold = error_threshold
        self.concurrency_adjustment_interval = adjustment_interval
        self.last_adjustment_time = time.time()
        logger.info(f"启用自适应并发控制: 目标TPS={target_tps}, 并发范围=[{min_concurrency}, {self.max_concurrency}], 错误阈值={error_threshold*100}%")
    
    def disable_adaptive_concurrency(self):
        """
        禁用自适应并发控制
        """
        self.adaptive_concurrency = False
        self.target_tps = None
        logger.info("禁用自适应并发控制")
    
    def set_max_concurrency(self, max_workers: int):
        """
        动态设置最大并发数
        
        Args:
            max_workers: 新的最大工作线程数
        """
        with self.tasks_lock:
            if self.max_workers != max_workers:
                self.max_workers = max(1, max_workers)
                if self.executor:
                    # 重启执行器以应用新的并发数
                    old_executor = self.executor
                    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
                    old_executor.shutdown(wait=False)
                logger.info(f"更新最大并发数: {self.max_workers}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown(wait=True)


class AsyncRateLimiter:
    """
    异步速率限制器，用于asyncio环境
    """
    def __init__(self, rate: int, time_unit: float = 1.0):
        """
        初始化异步速率限制器
        
        Args:
            rate: 单位时间内允许的请求数量
            time_unit: 时间单位（秒），默认1秒
        """
        self.rate = rate
        self.time_unit = time_unit
        self.interval = time_unit / rate if rate > 0 else 0
        self.last_request_time = 0
        self.lock = asyncio.Lock()
    
    async def wait(self):
        """
        异步等待直到可以发送下一个请求
        """
        async with self.lock:
            now = time.time()
            elapsed_since_last = now - self.last_request_time
            wait_time = max(0, self.interval - elapsed_since_last)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self.last_request_time = time.time()
            else:
                self.last_request_time = now
    
    async def __aenter__(self):
        await self.wait()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@contextmanager
def limited_concurrency(max_workers: int = 10, tps: Optional[int] = None):
    """
    限制并发数和TPS的上下文管理器
    
    Args:
        max_workers: 最大工作线程数
        tps: 每秒事务数限制
    """
    rate_limiter = RateLimiter(tps) if tps else None
    executor = ConcurrentExecutor(max_workers=max_workers, rate_limiter=rate_limiter)
    
    try:
        yield executor
    finally:
        executor.shutdown()


class ConcurrencyManager:
    """
    并发管理器，提供多种并发控制策略
    """
    def __init__(self, default_max_workers: int = 10):
        """
        初始化并发管理器
        
        Args:
            default_max_workers: 默认最大工作线程数
        """
        self.default_max_workers = default_max_workers
        self.executors: Dict[str, ConcurrentExecutor] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
    
    def get_rate_limiter(self, name: str, rate: int, time_unit: float = 1.0, mode: str = 'fixed'):
        """
        获取或创建速率限制器
        
        Args:
            name: 限制器名称
            rate: 速率
            time_unit: 时间单位
            mode: 模式
            
        Returns:
            速率限制器实例
        """
        if name not in self.rate_limiters:
            self.rate_limiters[name] = RateLimiter(rate, time_unit, mode)
        return self.rate_limiters[name]
    
    def get_executor(self, name: str, max_workers: Optional[int] = None, 
                     rate_limiter: Optional[Union[RateLimiter, str]] = None):
        """
        获取或创建执行器
        
        Args:
            name: 执行器名称
            max_workers: 最大工作线程数
            rate_limiter: 速率限制器或其名称
            
        Returns:
            并发执行器实例
        """
        if name not in self.executors:
            # 确定速率限制器
            limiter = None
            if isinstance(rate_limiter, str):
                limiter = self.rate_limiters.get(rate_limiter)
            elif isinstance(rate_limiter, RateLimiter):
                limiter = rate_limiter
            
            self.executors[name] = ConcurrentExecutor(
                max_workers=max_workers or self.default_max_workers,
                rate_limiter=limiter
            )
        
        return self.executors[name]
    
    def shutdown_executor(self, name: str, wait: bool = True):
        """
        关闭指定的执行器
        
        Args:
            name: 执行器名称
            wait: 是否等待任务完成
        """
        if name in self.executors:
            self.executors[name].shutdown(wait=wait)
            del self.executors[name]
    
    def shutdown_all(self, wait: bool = True):
        """
        关闭所有执行器
        
        Args:
            wait: 是否等待任务完成
        """
        for name in list(self.executors.keys()):
            self.shutdown_executor(name, wait)


# 创建全局并发管理器实例
global_concurrency_manager = ConcurrencyManager()


def run_concurrent_tasks(tasks: List[Callable], max_workers: int = 10, 
                         tps: Optional[int] = None, collect_results: bool = True):
    """
    并发执行任务列表
    
    Args:
        tasks: 任务函数列表
        max_workers: 最大工作线程数
        tps: 每秒事务数限制
        collect_results: 是否收集结果
        
    Returns:
        如果collect_results为True，返回结果列表
    """
    rate_limiter = RateLimiter(tps) if tps else None
    
    with ConcurrentExecutor(max_workers=max_workers, rate_limiter=rate_limiter) as executor:
        # 提交所有任务
        for task in tasks:
            if callable(task):
                executor.submit(task)
            elif isinstance(task, tuple) and len(task) > 0 and callable(task[0]):
                # 支持 (func, *args, **kwargs) 格式
                func = task[0]
                args = task[1:] if len(task) > 1 else ()
                kwargs = {}
                if args and isinstance(args[-1], dict):
                    kwargs = args[-1]
                    args = args[:-1]
                executor.submit(func, *args, **kwargs)
        
        # 等待完成并收集结果
        return executor.wait_completion(collect_results)


def run_with_rate_limit(func: Callable, tps: int, *args, **kwargs):
    """
    以指定TPS执行单个函数
    
    Args:
        func: 要执行的函数
        tps: 每秒事务数限制
        *args: 函数参数
        **kwargs: 函数关键字参数
        
    Returns:
        函数执行结果
    """
    rate_limiter = RateLimiter(tps)
    with rate_limiter:
        return func(*args, **kwargs)


# 示例用法
if __name__ == "__main__":
    # 示例1: 使用速率限制器
    def test_rate_limiter():
        print("测试速率限制器 (5 TPS):")
        limiter = RateLimiter(rate=5)  # 5次/秒
        
        start_time = time.time()
        for i in range(10):
            with limiter:
                print(f"执行请求 {i+1}, 时间: {time.time() - start_time:.2f}s")
        
        elapsed = time.time() - start_time
        print(f"10次请求总耗时: {elapsed:.2f}s, 平均TPS: {10/elapsed:.2f}")
    
    # 示例2: 使用并发执行器
    def test_task(task_id):
        time.sleep(0.1)  # 模拟工作负载
        return f"Task {task_id} completed"
    
    def test_concurrent_executor():
        print("\n测试并发执行器 (最大8并发, 10 TPS):")
        
        tasks = [(test_task, i) for i in range(20)]
        
        start_time = time.time()
        results = run_concurrent_tasks(tasks, max_workers=8, tps=10)
        
        elapsed = time.time() - start_time
        print(f"20个任务总耗时: {elapsed:.2f}s, 平均TPS: {20/elapsed:.2f}")
        print(f"成功完成: {len([r for _, _, r, e in results if e is None])}")
    
    # 运行示例
    test_rate_limiter()
    test_concurrent_executor()