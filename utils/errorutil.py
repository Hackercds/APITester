"""
统一错误处理模块
提供标准化的异常类层次结构、异常处理装饰器、错误报告和日志集成功能
"""

import traceback
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic, Union, Type
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# 导入日志工具
from utils.logutil import logger as base_logger

# 创建专用日志记录器
logger = logging.getLogger("api_auto_test.error")


# ============================================================================
# 异常层次结构定义
# ============================================================================


class ApiAutoFrameworkError(Exception):
    """
    框架基础异常类
    所有自定义异常的根类
    """
    def __init__(self, message: str, error_code: int = 500, 
                 details: Optional[Dict[str, Any]] = None):
        """
        初始化异常
        
        Args:
            message: 异常描述信息
            error_code: 错误代码，默认为500（服务器内部错误）
            details: 额外的错误详情字典
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()
        self.stack_trace = traceback.format_exc()
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将异常信息转换为字典格式
        
        Returns:
            包含异常所有信息的字典
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }
    
    def __str__(self) -> str:
        """
        返回格式化的异常字符串表示
        """
        base_str = f"[{self.__class__.__name__}:{self.error_code}] {self.message}"
        if self.details:
            details_str = json.dumps(self.details, ensure_ascii=False, default=str)
            base_str += f" | 详情: {details_str}"
        return base_str


class ConfigError(ApiAutoFrameworkError):
    """
    配置相关错误
    用于配置加载、验证和处理过程中的错误
    """
    def __init__(self, message: str, config_name: Optional[str] = None,
                 config_value: Optional[Any] = None):
        details = {
            "config_name": config_name,
            "config_value": config_value
        }
        super().__init__(message, error_code=400, details={k: v for k, v in details.items() if v is not None})


class HttpError(ApiAutoFrameworkError):
    """
    HTTP请求相关错误的基类
    """
    pass


class HttpRequestError(HttpError):
    """
    HTTP请求错误
    用于请求发送、连接建立等过程中的错误
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
        # 根据HTTP状态码设置错误级别
        error_code = status_code or 400
        super().__init__(message, error_code=error_code, details=details)


class HttpRetryError(HttpRequestError):
    """
    HTTP请求重试失败错误
    用于当请求在多次重试后仍然失败的情况
    """
    def __init__(self, message: str, url: str, method: str, 
                 retry_count: int, last_error: Optional[Exception] = None):
        details = {
            "url": url,
            "method": method,
            "retry_count": retry_count,
            "last_error": str(last_error) if last_error else None
        }
        super().__init__(message, error_code=503, details=details)


class AuthError(ApiAutoFrameworkError):
    """
    认证/授权错误
    用于认证失败、权限不足等情况
    """
    def __init__(self, message: str, auth_type: str,
                 credentials: Optional[Dict[str, Any]] = None,
                 error_details: Optional[Any] = None):
        details = {
            "auth_type": auth_type,
            "credentials": credentials or {},
            "error_details": error_details
        }
        super().__init__(message, error_code=401, details={k: v for k, v in details.items() if v is not None})


class ValidationError(ApiAutoFrameworkError):
    """
    数据验证错误
    用于参数验证、响应验证等场景
    """
    def __init__(self, message: str, field: Optional[str] = None,
                 value: Optional[Any] = None, expected: Optional[Any] = None):
        details = {
            "field": field,
            "value": value,
            "expected": expected
        }
        super().__init__(message, error_code=400, details={k: v for k, v in details.items() if v is not None})


class TestCaseError(ApiAutoFrameworkError):
    """
    测试用例错误
    用于测试用例执行过程中的错误
    """
    def __init__(self, message: str, case_id: Optional[str] = None,
                 step: Optional[str] = None):
        details = {
            "case_id": case_id,
            "step": step
        }
        super().__init__(message, error_code=400, details={k: v for k, v in details.items() if v is not None})


class ParameterError(ApiAutoFrameworkError):
    """
    参数错误
    用于方法参数校验失败的情况
    """
    def __init__(self, message: str, param_name: Optional[str] = None,
                 param_value: Optional[Any] = None,
                 expected_type: Optional[TypeVar] = None):
        details = {
            "param_name": param_name,
            "param_value": param_value,
            "expected_type": str(expected_type) if expected_type else None
        }
        super().__init__(message, error_code=400, details={k: v for k, v in details.items() if v is not None})


class ModelError(ApiAutoFrameworkError):
    """
    大模型接口相关错误
    用于模型API调用、响应处理等场景
    """
    def __init__(self, message: str, model_type: str,
                 request_params: Optional[Dict[str, Any]] = None,
                 response: Optional[Any] = None):
        details = {
            "model_type": model_type,
            "request_params": request_params,
            "response": response
        }
        super().__init__(message, error_code=500, details={k: v for k, v in details.items() if v is not None})


class ExtractionError(ApiAutoFrameworkError):
    """
    数据提取错误
    用于从响应中提取数据失败的情况
    """
    def __init__(self, message: str, extraction_type: str,
                 expression: Optional[str] = None,
                 source_data: Optional[Any] = None):
        details = {
            "extraction_type": extraction_type,
            "expression": expression,
            "source_data": source_data
        }
        super().__init__(message, error_code=400, details={k: v for k, v in details.items() if v is not None})


class DataSourceError(ApiAutoFrameworkError):
    """
    数据源错误
    用于数据加载、读取失败的情况
    """
    def __init__(self, message: str, source_type: str,
                 source_path: Optional[str] = None):
        details = {
            "source_type": source_type,
            "source_path": source_path
        }
        super().__init__(message, error_code=500, details={k: v for k, v in details.items() if v is not None})


# ============================================================================
# 错误严重程度枚举
# ============================================================================


class ErrorSeverity:
    """
    错误严重程度枚举
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    @classmethod
    def from_error_code(cls, error_code: int) -> str:
        """
        根据错误代码确定严重程度
        
        Args:
            error_code: 错误代码
            
        Returns:
            严重程度字符串
        """
        if error_code >= 500:
            return cls.HIGH
        elif error_code >= 400:
            return cls.MEDIUM
        else:
            return cls.LOW


# ============================================================================
# 错误报告生成器
# ============================================================================


class ErrorReporter:
    """
    错误报告生成器
    收集、管理和导出错误信息
    """
    def __init__(self, report_dir: str = "./reports/errors"):
        """
        初始化错误报告生成器
        
        Args:
            report_dir: 报告存储目录
        """
        self.report_dir = report_dir
        self.errors: List[Dict[str, Any]] = []
        
        # 确保报告目录存在
        if not os.path.exists(report_dir):
            os.makedirs(report_dir, exist_ok=True)
    
    def add_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        添加错误信息
        
        Args:
            error: 异常对象
            context: 上下文信息，提供额外的错误发生环境
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error.__class__.__name__,
            "message": str(error),
            "stack_trace": traceback.format_exc(),
            "context": context or {}
        }
        
        # 如果是自定义异常，添加更多信息
        if isinstance(error, ApiAutoFrameworkError):
            error_info.update(error.to_dict())
            # 添加严重程度
            error_info["severity"] = ErrorSeverity.from_error_code(error.error_code)
        else:
            # 对于标准异常，设置默认严重程度
            error_info["severity"] = ErrorSeverity.MEDIUM
            error_info["error_code"] = 500  # 默认服务器错误
        
        self.errors.append(error_info)
        
        # 记录到日志
        severity = error_info.get("severity", ErrorSeverity.MEDIUM)
        if severity == ErrorSeverity.HIGH:
            logger.critical(f"错误: {error_info['error_type']} - {error_info['message']}")
        elif severity == ErrorSeverity.MEDIUM:
            logger.error(f"错误: {error_info['error_type']} - {error_info['message']}")
        else:
            logger.warning(f"错误: {error_info['error_type']} - {error_info['message']}")
        
        logger.debug(f"错误详情: {json.dumps(error_info, ensure_ascii=False, default=str)}")
    
    def clear(self) -> None:
        """
        清除所有错误记录
        """
        self.errors.clear()
    
    def get_errors(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取指定严重程度的错误
        
        Args:
            severity: 严重程度过滤，可选值: high, medium, low
            
        Returns:
            过滤后的错误列表
        """
        if not severity:
            return self.errors
        
        return [error for error in self.errors 
                if error.get("severity") == severity]
    
    def generate_summary(self) -> Dict[str, Any]:
        """
        生成错误统计摘要
        
        Returns:
            包含错误统计信息的字典
        """
        if not self.errors:
            return {
                "total_errors": 0,
                "error_types": {},
                "severity_counts": {},
                "most_common_error": None,
                "most_common_error_count": 0,
                "first_error_time": None,
                "last_error_time": None,
                "generated_at": datetime.now().isoformat()
            }
        
        # 统计错误类型
        error_types = {}
        for error in self.errors:
            error_type = error["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # 统计严重程度
        severity_counts = {}
        for error in self.errors:
            severity = error.get("severity", ErrorSeverity.MEDIUM)
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # 找出最常见的错误类型
        most_common_error = None
        most_common_error_count = 0
        for error_type, count in error_types.items():
            if count > most_common_error_count:
                most_common_error = error_type
                most_common_error_count = count
        
        # 排序错误按时间
        sorted_errors = sorted(self.errors, key=lambda x: x["timestamp"])
        
        return {
            "total_errors": len(self.errors),
            "error_types": error_types,
            "severity_counts": severity_counts,
            "most_common_error": most_common_error,
            "most_common_error_count": most_common_error_count,
            "first_error_time": sorted_errors[0]["timestamp"],
            "last_error_time": sorted_errors[-1]["timestamp"],
            "generated_at": datetime.now().isoformat()
        }
    
    def export_to_json(self, output_path: Optional[str] = None) -> str:
        """
        导出错误报告为JSON格式
        
        Args:
            output_path: 输出文件路径，如果不提供则生成默认路径
            
        Returns:
            生成的报告文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.report_dir, f"error_report_{timestamp}.json")
        
        report_data = {
            "summary": self.generate_summary(),
            "errors": self.errors
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"错误报告已导出到: {output_path}")
        return output_path
    
    def export_to_html(self, output_path: Optional[str] = None) -> str:
        """
        导出错误报告为HTML格式
        
        Args:
            output_path: 输出文件路径，如果不提供则生成默认路径
            
        Returns:
            生成的报告文件路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.report_dir, f"error_report_{timestamp}.html")
        
        summary = self.generate_summary()
        
        html_content = self._generate_html_report(summary)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML错误报告已导出到: {output_path}")
        return output_path
    
    def _generate_html_report(self, summary: Dict[str, Any]) -> str:
        """
        生成HTML格式的错误报告
        
        Args:
            summary: 错误统计摘要
            
        Returns:
            HTML格式的报告内容
        """
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API自动化测试错误报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1, h2 {{
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-item {{
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 10px 15px;
            flex: 1;
            min-width: 200px;
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
            transition: transform 0.2s;
        }}
        .error-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
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
            border-left: 4px solid #e74c3c;
        }}
        .severity-medium {{
            color: #f39c12;
            border-left: 4px solid #f39c12;
        }}
        .severity-low {{
            color: #27ae60;
            border-left: 4px solid #27ae60;
        }}
        .severity-badge-high {{
            background-color: #fee;
            color: #e74c3c;
        }}
        .severity-badge-medium {{
            background-color: #fff8e1;
            color: #f39c12;
        }}
        .severity-badge-low {{
            background-color: #e8f5e9;
            color: #27ae60;
        }}
        .stat-chart {{
            height: 10px;
            background-color: #ecf0f1;
            border-radius: 5px;
            overflow: hidden;
            margin-top: 5px;
        }}
        .stat-bar {{
            height: 100%;
            background-color: #3498db;
        }}
        .no-errors {{
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
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
                <strong>最常见错误类型:</strong> {summary['most_common_error'] or 'N/A'} ({summary['most_common_error_count']}次)
            </div>
            <div class="summary-item">
                <strong>首次错误时间:</strong> {summary['first_error_time'] or 'N/A'}
            </div>
            <div class="summary-item">
                <strong>最后错误时间:</strong> {summary['last_error_time'] or 'N/A'}
            </div>
            <div class="summary-item">
                <strong>报告生成时间:</strong> {summary['generated_at']}
            </div>
        </div>
        
        <h2>严重程度统计</h2>
        <div class="summary">
            {self._generate_severity_stats_html(summary.get('severity_counts', {}))}
        </div>
        
        <h2>错误类型统计</h2>
        <div class="summary">
            {self._generate_error_type_stats_html(summary.get('error_types', {}))}
        </div>
        
        <h2>错误详情</h2>
        <div class="error-list">
            {self._generate_error_items_html()}
        </div>
    </div>
</body>
</html>
        """
    
    def _generate_severity_stats_html(self, severity_counts: Dict[str, int]) -> str:
        """
        生成严重程度统计的HTML
        """
        if not severity_counts:
            return "<p>没有错误记录。</p>"
        
        items = []
        total = sum(severity_counts.values())
        
        for severity, count in severity_counts.items():
            percentage = (count / total * 100) if total > 0 else 0
            badge_class = f"severity-badge-{severity}"
            severity_text = severity.upper()
            
            items.append(f"""
            <div class="summary-item">
                <strong class="{badge_class}">{severity_text}:</strong> {count}次 ({percentage:.1f}%)
                <div class="stat-chart">
                    <div class="stat-bar" style="width: {percentage}%"></div>
                </div>
            </div>
            """)
        
        return ''.join(items)
    
    def _generate_error_type_stats_html(self, error_types: Dict[str, int]) -> str:
        """
        生成错误类型统计的HTML
        """
        if not error_types:
            return "<p>没有错误记录。</p>"
        
        items = []
        total = sum(error_types.values())
        
        # 按错误数量降序排序
        sorted_types = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]  # 只显示前10种
        
        for error_type, count in sorted_types:
            percentage = (count / total * 100) if total > 0 else 0
            
            items.append(f"""
            <div class="summary-item">
                <strong>{error_type}:</strong> {count}次 ({percentage:.1f}%)
                <div class="stat-chart">
                    <div class="stat-bar" style="width: {percentage}%"></div>
                </div>
            </div>
            """)
        
        if len(error_types) > 10:
            items.append(f"""
            <div class="summary-item">
                <em>还有 {len(error_types) - 10} 种错误类型未显示</em>
            </div>
            """)
        
        return ''.join(items)
    
    def _generate_error_items_html(self) -> str:
        """
        生成错误详情项的HTML
        """
        if not self.errors:
            return "<p class='no-errors'>没有错误记录。</p>"
        
        items = []
        # 按时间倒序排列，最新的错误在前面
        sorted_errors = sorted(self.errors, key=lambda x: x["timestamp"], reverse=True)
        
        for i, error in enumerate(sorted_errors, 1):
            # 确定严重程度类
            severity_class = error.get("severity", ErrorSeverity.MEDIUM)
            
            # 格式化堆栈跟踪
            stack_trace = error.get("stack_trace", '').replace('\n', '<br>')
            
            # 生成上下文信息
            context_info = ''
            if error.get('context'):
                context_info = f"""
                <div style="margin-top: 10px;">
                    <strong>上下文信息:</strong>
                    <div class="error-details">{json.dumps(error['context'], ensure_ascii=False, indent=2).replace('\n', '<br>')}</div>
                </div>
                """
            
            # 生成详细信息
            details_info = ''
            if error.get('details'):
                details_info = f"""
                <div style="margin-top: 10px;">
                    <strong>详细信息:</strong>
                    <div class="error-details">{json.dumps(error['details'], ensure_ascii=False, indent=2).replace('\n', '<br>')}</div>
                </div>
                """
            
            # 生成错误详情HTML
            error_html = f"""
            <div class="error-item severity-{severity_class}">
                <div class="error-header">
                    错误 #{i}: {error.get('error_type', 'Unknown Error')}
                </div>
                <div class="error-meta">
                    <div class="error-meta-item">{error.get('timestamp', '')}</div>
                    <div class="error-meta-item severity-badge-{severity_class}">
                        严重程度: {severity_class.upper()}
                    </div>
                    <div class="error-meta-item">
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
                {details_info}
                {context_info}
            </div>
            """
            
            items.append(error_html)
        
        return ''.join(items)
    
    def send_email_report(self, smtp_config: Dict[str, Any], 
                         recipients: List[str], 
                         subject: Optional[str] = None,
                         include_html: bool = True,
                         include_json: bool = False,
                         include_attachments: bool = True) -> bool:
        """
        通过邮件发送错误报告
        
        Args:
            smtp_config: SMTP服务器配置
            recipients: 收件人列表
            subject: 邮件主题，如果不提供则生成默认主题
            include_html: 是否包含HTML格式报告
            include_json: 是否包含JSON格式报告
            include_attachments: 是否作为附件发送报告
            
        Returns:
            发送是否成功
        """
        try:
            # 创建邮件消息
            msg = MIMEMultipart()
            
            # 设置邮件主题
            if subject is None:
                summary = self.generate_summary()
                subject = f"[API自动化测试] 错误报告 - 共{summary['total_errors']}个错误"
            
            msg['From'] = smtp_config['from']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # 生成邮件正文
            summary = self.generate_summary()
            body = f"""
            <h2>API自动化测试错误报告</h2>
            
            <h3>错误摘要</h3>
            <ul>
                <li>总错误数: {summary['total_errors']}</li>
                <li>最常见错误类型: {summary['most_common_error'] or 'N/A'} ({summary['most_common_error_count']}次)</li>
                <li>首次错误时间: {summary['first_error_time'] or 'N/A'}</li>
                <li>最后错误时间: {summary['last_error_time'] or 'N/A'}</li>
            </ul>
            
            <p>请查看附件获取完整报告。</p>
            """
            
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            attachments = []
            
            # 生成并添加报告附件
            if include_html and include_attachments:
                html_path = self.export_to_html()
                with open(html_path, 'rb') as f:
                    attachment = MIMEApplication(f.read())
                    attachment.add_header('Content-Disposition', 'attachment', 
                                         filename=os.path.basename(html_path))
                    msg.attach(attachment)
                attachments.append(html_path)
            
            if include_json and include_attachments:
                json_path = self.export_to_json()
                with open(json_path, 'rb') as f:
                    attachment = MIMEApplication(f.read())
                    attachment.add_header('Content-Disposition', 'attachment', 
                                         filename=os.path.basename(json_path))
                    msg.attach(attachment)
                attachments.append(json_path)
            
            # 连接SMTP服务器并发送邮件
            with smtplib.SMTP(smtp_config['server'], smtplib.SMTP_PORT) as server:
                server.starttls()  # 启用TLS加密
                server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            
            logger.info(f"错误报告邮件已发送至 {', '.join(recipients)}")
            logger.debug(f"发送的附件: {attachments}")
            return True
            
        except Exception as e:
            logger.error(f"发送错误报告邮件失败: {str(e)}")
            logger.debug(traceback.format_exc())
            return False


# ============================================================================
# 异常处理装饰器
# ============================================================================


T = TypeVar('T')


def handle_exception(report_errors: bool = True,
                     continue_on_error: bool = False,
                     log_level: str = "ERROR",
                     retry: int = 0,
                     retry_delay: float = 1.0,
                     retry_on_exceptions: Optional[List[Type[Exception]]] = None,
                     transform_exception: Optional[Callable[[Exception], Exception]] = None,
                     context_provider: Optional[Callable[..., Dict[str, Any]]] = None
                    ) -> Callable[[Callable[..., T]], Callable[..., Optional[T]]]:
    """
    高级异常处理装饰器
    提供异常捕获、日志记录、报告生成、重试和异常转换功能
    
    Args:
        report_errors: 是否将错误添加到全局错误报告器
        continue_on_error: 遇到错误是否继续执行
        log_level: 日志记录级别
        retry: 失败后重试次数
        retry_delay: 重试间隔（秒）
        retry_on_exceptions: 指定哪些异常类型需要重试
        transform_exception: 异常转换函数，用于将捕获的异常转换为其他类型
        context_provider: 上下文提供函数，用于生成更丰富的错误上下文
        
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        def wrapper(*args, **kwargs) -> Optional[T]:
            last_exception = None
            
            # 计算最大尝试次数
            max_attempts = retry + 1
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # 构建上下文信息
                    context = {}
                    
                    # 基本上下文
                    context["function"] = func.__name__
                    context["attempt"] = attempt + 1
                    context["max_attempts"] = max_attempts
                    
                    # 添加参数信息（安全起见，不记录全部参数）
                    try:
                        # 尝试安全地序列化参数
                        context["args_count"] = len(args)
                        context["kwargs_keys"] = list(kwargs.keys())
                        
                        # 如果是类方法，添加类名
                        if args and hasattr(args[0], "__class__"):
                            context["class_name"] = args[0].__class__.__name__
                    except Exception:
                        pass
                    
                    # 使用上下文提供函数添加更多信息
                    if context_provider:
                        try:
                            provider_context = context_provider(*args, **kwargs)
                            context.update(provider_context)
                        except Exception as ctx_error:
                            logger.warning(f"上下文提供函数执行失败: {ctx_error}")
                    
                    # 记录错误
                    if log_level == "ERROR":
                        logger.error(f"执行 {func.__name__} 时出错 (尝试 {attempt + 1}/{max_attempts}): {str(e)}")
                    elif log_level == "WARNING":
                        logger.warning(f"执行 {func.__name__} 时警告 (尝试 {attempt + 1}/{max_attempts}): {str(e)}")
                    elif log_level == "INFO":
                        logger.info(f"执行 {func.__name__} 时信息 (尝试 {attempt + 1}/{max_attempts}): {str(e)}")
                    
                    # 报告错误
                    if report_errors:
                        error_reporter.add_error(e, context)
                    
                    # 判断是否需要重试
                    should_retry = attempt < retry
                    
                    # 如果指定了重试异常类型列表，则只对这些类型进行重试
                    if retry_on_exceptions:
                        should_retry = should_retry and any(isinstance(e, exc_type) for exc_type in retry_on_exceptions)
                    
                    if should_retry:
                        import time
                        logger.info(f"将在 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                    else:
                        # 不再重试，处理最终异常
                        if transform_exception:
                            try:
                                transformed_exception = transform_exception(e)
                                if continue_on_error:
                                    return None
                                else:
                                    raise transformed_exception from e
                            except Exception as transform_error:
                                logger.error(f"异常转换失败: {transform_error}")
                        
                        # 如果设置了继续执行，则返回None
                        if continue_on_error:
                            return None
                        else:
                            # 否则重新抛出原始异常
                            raise
            
            # 这一行理论上不会执行到，但为了代码完整性添加
            if continue_on_error:
                return None
            else:
                raise last_exception
        
        # 保留原函数信息
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        
        return wrapper
    
    return decorator


# ============================================================================
# 异常工具函数
# ============================================================================

def wrap_exception(original_exception: Exception, 
                  wrapper_exception: Union[Exception, Type[ApiAutoFrameworkError]],
                  message: Optional[str] = None,
                  **kwargs) -> Exception:
    """
    将原始异常包装为自定义异常
    
    Args:
        original_exception: 原始异常对象
        wrapper_exception: 包装异常类或异常对象
        message: 自定义错误消息，如果为None则使用原始异常消息
        **kwargs: 传递给包装异常构造函数的其他参数
        
    Returns:
        包装后的异常对象
    """
    if isinstance(wrapper_exception, Exception):
        # 如果wrapper_exception已经是异常实例，直接返回
        return wrapper_exception
    
    # 确保wrapper_exception是ApiAutoFrameworkError的子类
    if not (isinstance(wrapper_exception, type) and issubclass(wrapper_exception, ApiAutoFrameworkError)):
        raise TypeError("包装异常必须是ApiAutoFrameworkError的子类")
    
    # 如果没有提供自定义消息，使用原始异常的消息
    if message is None:
        message = str(original_exception)
    
    # 创建包装异常实例
    wrapped_exception = wrapper_exception(message, **kwargs)
    
    # 设置原始异常为cause
    wrapped_exception.__cause__ = original_exception
    
    return wrapped_exception


def format_exception_chain(exception: Exception) -> str:
    """
    格式化异常链，包括所有嵌套异常
    
    Args:
        exception: 异常对象
        
    Returns:
        格式化的异常链字符串
    """
    result = []
    current_exception = exception
    
    while current_exception:
        result.append(f"{type(current_exception).__name__}: {str(current_exception)}")
        
        # 检查是否有cause或context
        if current_exception.__cause__ and current_exception.__cause__ != current_exception:
            current_exception = current_exception.__cause__
        elif current_exception.__context__ and current_exception.__context__ != current_exception and current_exception.__context__ != current_exception.__cause__:
            current_exception = current_exception.__context__
        else:
            break
    
    return "\nCaused by: ".join(result)


# ============================================================================
# 全局实例和便捷函数
# ============================================================================


# 创建全局错误报告器实例
error_reporter = ErrorReporter()

# 导出便捷函数
def report_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    便捷函数：向全局错误报告器添加错误
    
    Args:
        error: 异常对象
        context: 上下文信息
    """
    error_reporter.add_error(error, context)

def export_error_report(format: str = "html", path: Optional[str] = None) -> str:
    """
    便捷函数：导出错误报告
    
    Args:
        format: 报告格式，支持 "html" 或 "json"
        path: 导出路径
        
    Returns:
        导出的文件路径
    """
    if format.lower() == "json":
        return error_reporter.export_to_json(path)
    else:
        return error_reporter.export_to_html(path)

def get_error_summary() -> Dict[str, Any]:
    """
    便捷函数：获取错误摘要
    
    Returns:
        错误摘要字典
    """
    return error_reporter.generate_summary()

def clear_errors() -> None:
    """
    便捷函数：清除所有错误记录
    """
    error_reporter.clear()


# ============================================================================
# 示例用法
# ============================================================================


def example_usage():
    """
    错误处理模块使用示例
    """
    # 1. 抛出自定义异常
    try:
        raise HttpRequestError(
            "API请求失败",
            url="https://api.example.com/users",
            method="GET",
            status_code=404,
            response_text="Not Found"
        )
    except HttpRequestError as e:
        print(f"捕获到HTTP请求错误: {e}")
        print(f"错误详情: {e.details}")
    
    # 2. 使用异常处理装饰器
    @handle_exception(report_errors=True, retry=2, retry_delay=0.5)
    def unstable_operation(param):
        if param < 0:
            raise ValueError("参数不能为负数")
        return param * 2
    
    # 3. 报告错误
    try:
        unstable_operation(-1)
    except Exception as e:
        report_error(e, {"test_case": "example_test", "environment": "dev"})
    
    # 4. 导出错误报告
    html_path = export_error_report("html")
    print(f"错误报告已导出到: {html_path}")
    
    # 5. 获取错误摘要
    summary = get_error_summary()
    print(f"错误摘要: {summary}")


if __name__ == "__main__":
    example_usage()