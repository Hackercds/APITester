import traceback
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_auto_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api_auto_test")

# 自定义异常类
class ApiTestBaseError(Exception):
    """
    API测试基础异常类
    """
    def __init__(self, message: str, error_code: int = 500, 
                 details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()
        self.stack_trace = traceback.format_exc()
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将异常信息转换为字典
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }

class HttpRequestError(ApiTestBaseError):
    """
    HTTP请求异常
    """
    def __init__(self, message: str, url: str, method: str,
                 status_code: Optional[int] = None,
                 response_text: Optional[str] = None,
                 request_data: Optional[Any] = None):
        details = {
            "url": url,
            "method": method,
            "status_code": status_code,
            "response_text": response_text,
            "request_data": request_data
        }
        super().__init__(message, error_code=400, details=details)

class AuthError(ApiTestBaseError):
    """
    认证异常
    """
    def __init__(self, message: str, auth_type: str,
                 credentials: Optional[Dict[str, Any]] = None):
        details = {
            "auth_type": auth_type,
            "credentials": credentials or {}
        }
        super().__init__(message, error_code=401, details=details)

class ValidationError(ApiTestBaseError):
    """
    数据验证异常
    """
    def __init__(self, message: str, field: Optional[str] = None,
                 value: Optional[Any] = None, expected: Optional[Any] = None):
        details = {
            "field": field,
            "value": value,
            "expected": expected
        }
        super().__init__(message, error_code=400, details=details)

class PerformanceError(ApiTestBaseError):
    """
    性能测试异常
    """
    def __init__(self, message: str, metric: str,
                 value: Optional[float] = None,
                 threshold: Optional[float] = None):
        details = {
            "metric": metric,
            "value": value,
            "threshold": threshold
        }
        super().__init__(message, error_code=500, details=details)

class TestCaseError(ApiTestBaseError):
    """
    测试用例异常
    """
    def __init__(self, message: str, case_id: Optional[str] = None,
                 step: Optional[str] = None):
        details = {
            "case_id": case_id,
            "step": step
        }
        super().__init__(message, error_code=400, details=details)

class SchedulerError(ApiTestBaseError):
    """
    调度器异常
    """
    def __init__(self, message: str, task_id: Optional[str] = None,
                 schedule_type: Optional[str] = None):
        details = {
            "task_id": task_id,
            "schedule_type": schedule_type
        }
        super().__init__(message, error_code=500, details=details)

# 错误报告生成器
class ErrorReporter:
    """
    错误报告生成器
    """
    def __init__(self, report_dir: str = "./reports"):
        """
        初始化错误报告生成器
        
        Args:
            report_dir: 报告存储目录
        """
        self.report_dir = report_dir
        self.errors: List[Dict[str, Any]] = []
        
        # 确保报告目录存在
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
    
    def add_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        添加错误信息
        
        Args:
            error: 异常对象
            context: 上下文信息
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error.__class__.__name__,
            "message": str(error),
            "stack_trace": traceback.format_exc(),
            "context": context or {}
        }
        
        # 如果是自定义异常，添加更多信息
        if isinstance(error, ApiTestBaseError):
            error_info.update(error.to_dict())
        
        self.errors.append(error_info)
        
        # 记录到日志
        logger.error(f"Error: {error_info['error_type']} - {error_info['message']}")
        logger.debug(f"Error details: {json.dumps(error_info, ensure_ascii=False)}")
    
    def generate_summary(self) -> Dict[str, Any]:
        """
        生成错误报告摘要
        
        Returns:
            Dict: 错误摘要信息
        """
        # 按错误类型统计
        error_type_count = {}
        for error in self.errors:
            error_type = error.get('error_type', 'Unknown')
            error_type_count[error_type] = error_type_count.get(error_type, 0) + 1
        
        # 找出最常见的错误
        most_common_error = None
        max_count = 0
        for error_type, count in error_type_count.items():
            if count > max_count:
                max_count = count
                most_common_error = error_type
        
        # 计算总体统计信息
        summary = {
            "total_errors": len(self.errors),
            "error_types": error_type_count,
            "most_common_error": most_common_error,
            "most_common_error_count": max_count,
            "first_error_time": self.errors[0]['timestamp'] if self.errors else None,
            "last_error_time": self.errors[-1]['timestamp'] if self.errors else None,
            "generated_at": datetime.now().isoformat()
        }
        
        return summary
    
    def export_to_json(self, filename: Optional[str] = None) -> str:
        """
        导出错误报告为JSON格式
        
        Args:
            filename: 文件名，如果为None则自动生成
        
        Returns:
            str: 生成的文件路径
        """
        if not filename:
            filename = f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_path = os.path.join(self.report_dir, filename)
        
        report_data = {
            "summary": self.generate_summary(),
            "errors": self.errors,
            "report_info": {
                "generated_at": datetime.now().isoformat(),
                "report_version": "1.0"
            }
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"错误报告已导出到: {report_path}")
        return report_path
    
    def export_to_html(self, filename: Optional[str] = None) -> str:
        """
        导出错误报告为HTML格式
        
        Args:
            filename: 文件名，如果为None则自动生成
        
        Returns:
            str: 生成的文件路径
        """
        if not filename:
            filename = f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        report_path = os.path.join(self.report_dir, filename)
        
        # 生成HTML内容
        html_content = self._generate_html_report()
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML错误报告已导出到: {report_path}")
        return report_path
    
    def _generate_html_report(self) -> str:
        """
        生成HTML报告内容
        """
        summary = self.generate_summary()
        
        # HTML模板
        html_template = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>API自动化测试错误报告</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    border-bottom: 2px solid #e74c3c;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #555;
                    margin-top: 30px;
                }}
                .summary {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .summary-item {{
                    margin: 10px 0;
                    padding: 8px;
                    background-color: white;
                    border-left: 4px solid #3498db;
                }}
                .error-list {{
                    margin-top: 20px;
                }}
                .error-item {{
                    margin: 15px 0;
                    padding: 15px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    background-color: #fff8f8;
                }}
                .error-header {{
                    background-color: #ffeaea;
                    padding: 10px;
                    border-radius: 4px;
                    margin-bottom: 10px;
                    font-weight: bold;
                    color: #c0392b;
                }}
                .error-details {{
                    margin-top: 10px;
                    font-family: monospace;
                    white-space: pre-wrap;
                    background-color: #f8f9fa;
                    padding: 10px;
                    border-radius: 4px;
                    max-height: 200px;
                    overflow-y: auto;
                    font-size: 12px;
                }}
                .error-meta {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    margin-bottom: 10px;
                }}
                .error-meta-item {{
                    background-color: #e8f4fd;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 12px;
                }}
                .severity-high {{
                    color: #e74c3c;
                }}
                .severity-medium {{
                    color: #f39c12;
                }}
                .severity-low {{
                    color: #27ae60;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>API自动化测试错误报告</h1>
                
                <h2>错误摘要</h2>
                <div class="summary">
                    <div class="summary-item">
                        <strong>总错误数:</strong> {summary['total_errors']}
                    </div>
                    <div class="summary-item">
                        <strong>最常见错误类型:</strong> {summary['most_common_error']} ({summary['most_common_error_count']}次)
                    </div>
                    <div class="summary-item">
                        <strong>首次错误时间:</strong> {summary['first_error_time']}
                    </div>
                    <div class="summary-item">
                        <strong>最后错误时间:</strong> {summary['last_error_time']}
                    </div>
                    <div class="summary-item">
                        <strong>报告生成时间:</strong> {summary['generated_at']}
                    </div>
                </div>
                
                <h2>错误类型统计</h2>
                <div class="summary">
                    {self._generate_error_type_stats_html(summary['error_types'])}
                </div>
                
                <h2>错误详情</h2>
                <div class="error-list">
                    {self._generate_error_items_html()}
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _generate_error_type_stats_html(self, error_types: Dict[str, int]) -> str:
        """
        生成错误类型统计的HTML
        """
        items = []
        for error_type, count in error_types.items():
            items.append(f"<div class='summary-item'><strong>{error_type}:</strong> {count}次</div>")
        return ''.join(items)
    
    def _generate_error_items_html(self) -> str:
        """
        生成错误详情项的HTML
        """
        items = []
        for i, error in enumerate(self.errors, 1):
            # 确定严重程度
            severity_class = 'severity-medium'
            if 'error_code' in error:
                if error['error_code'] >= 500:
                    severity_class = 'severity-high'
                elif error['error_code'] < 400:
                    severity_class = 'severity-low'
            
            # 格式化堆栈跟踪
            stack_trace = error.get('stack_trace', '').replace('\n', '<br>')
            
            # 生成上下文信息
            context_info = ''
            if error.get('context'):
                context_info = f"""
                <div style="margin-top: 10px;">
                    <strong>上下文信息:</strong>
                    <div class="error-details">{json.dumps(error['context'], ensure_ascii=False, indent=2).replace('\n', '<br>')}</div>
                </div>
                """
            
            # 生成错误详情HTML
            error_html = f"""
            <div class="error-item">
                <div class="error-header">
                    错误 #{i}: {error.get('error_type', 'Unknown Error')}
                </div>
                <div class="error-meta">
                    <div class="error-meta-item">{error.get('timestamp', '')}</div>
                    <div class="error-meta-item {severity_class}">
                        错误代码: {error.get('error_code', 'N/A')}
                    </div>
                </div>
                <div>
                    <strong>错误信息:</strong> {error.get('message', '')}
                </div>
                <div style="margin-top: 10px;">
                    <strong>堆栈跟踪:</strong>
                    <div class="error-details">{stack_trace}</div>
                </div>
                {context_info}
            </div>
            """
            
            items.append(error_html)
        
        if not items:
            return "<p>没有错误记录。</p>"
        
        return ''.join(items)
    
    def send_email_report(self, smtp_config: Dict[str, Any], 
                         recipients: List[str],
                         include_attachments: bool = True) -> bool:
        """
        发送邮件报告
        
        Args:
            smtp_config: SMTP服务器配置
            recipients: 收件人列表
            include_attachments: 是否包含附件
        
        Returns:
            bool: 是否发送成功
        """
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = smtp_config['from']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"API自动化测试错误报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # 生成HTML报告
            html_report_path = self.export_to_html()
            
            # 读取HTML内容作为邮件正文
            with open(html_report_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 添加附件
            if include_attachments:
                # 添加HTML报告附件
                with open(html_report_path, 'rb') as f:
                    attachment = MIMEApplication(f.read(), Name=os.path.basename(html_report_path))
                    attachment['Content-Disposition'] = f'attachment; filename="{os.path.basename(html_report_path)}"'
                    msg.attach(attachment)
                
                # 添加JSON报告附件
                json_report_path = self.export_to_json()
                with open(json_report_path, 'rb') as f:
                    attachment = MIMEApplication(f.read(), Name=os.path.basename(json_report_path))
                    attachment['Content-Disposition'] = f'attachment; filename="{os.path.basename(json_report_path)}"'
                    msg.attach(attachment)
            
            # 发送邮件
            server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
            server.starttls()
            server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"错误报告邮件已发送到: {', '.join(recipients)}")
            return True
        except Exception as e:
            logger.error(f"发送邮件报告失败: {str(e)}")
            return False
    
    def clear(self) -> None:
        """
        清空错误记录
        """
        self.errors.clear()
        logger.info("错误记录已清空")

# 全局错误报告器实例
error_reporter = ErrorReporter()

# 异常处理器装饰器
def handle_exception(report_errors: bool = True, 
                     continue_on_error: bool = False,
                     log_level: str = "ERROR"):
    """
    异常处理装饰器
    
    Args:
        report_errors: 是否报告错误
        continue_on_error: 遇到错误是否继续执行
        log_level: 日志级别
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 构建上下文信息
                context = {
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
                
                # 记录错误
                if log_level == "ERROR":
                    logger.error(f"执行 {func.__name__} 时出错: {str(e)}")
                elif log_level == "WARNING":
                    logger.warning(f"执行 {func.__name__} 时警告: {str(e)}")
                
                # 报告错误
                if report_errors:
                    error_reporter.add_error(e, context)
                
                # 是否继续执行
                if continue_on_error:
                    return None
                else:
                    raise
        
        # 保留原函数信息
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator

# 示例用法
def main():
    # 创建错误报告器
    reporter = ErrorReporter()
    
    try:
        # 模拟一些错误
        raise HttpRequestError(
            "请求失败", 
            url="http://api.example.com/test", 
            method="GET",
            status_code=404,
            response_text="Not Found"
        )
    except Exception as e:
        reporter.add_error(e, {"test_case": "example_test", "environment": "test"})
    
    try:
        # 模拟认证错误
        raise AuthError(
            "认证失败",
            auth_type="token",
            credentials={"username": "test_user"}
        )
    except Exception as e:
        reporter.add_error(e)
    
    # 导出报告
    json_report = reporter.export_to_json()
    html_report = reporter.export_to_html()
    
    print(f"JSON报告: {json_report}")
    print(f"HTML报告: {html_report}")
    print(f"错误摘要: {reporter.generate_summary()}")

if __name__ == "__main__":
    main()