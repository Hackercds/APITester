# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


"""
接口自动化测试框架 - 主入口文件
提供命令行方式运行测试的能力
"""
import os
import sys
import argparse
import json
from typing import Optional, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import logger
from testcase.test_runner import TestRunner, TestAPI
from api_auto_framework import ApiTestFramework


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        解析后的参数命名空间
    """
    parser = argparse.ArgumentParser(
        description='接口自动化测试框架',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行默认项目的所有启用测试用例
  python main.py
  
  # 运行指定项目的测试用例
  python main.py --project okr-api
  
  # 运行所有测试用例（包括未启用的）
  python main.py --all
  
  # 生成报告到指定文件
  python main.py --report report.json
        """)
    
    parser.add_argument(
        '--project',
        type=str,
        default='okr-api',
        help='项目名称 (默认: okr-api)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='运行所有测试用例，包括未启用的'
    )
    
    parser.add_argument(
        '--report',
        type=str,
        help='测试报告输出文件路径'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='启用详细日志输出'
    )
    
    parser.add_argument(
        '--case-ids',
        type=str,
        help='指定要运行的测试用例ID列表，逗号分隔'
    )
    
    return parser.parse_args()


def run_tests(args: argparse.Namespace) -> dict:
    """
    运行测试
    
    Args:
        args: 命令行参数
        
    Returns:
        测试报告字典
    """
    logger.info(f"开始运行测试 - 项目: {args.project}")
    
    # 创建框架实例
    framework = ApiTestFramework(args.project)
    
    # 创建测试运行器
    runner = TestRunner(args.project)
    
    # 加载测试用例
    test_cases = runner.load_test_cases(run_only=not args.all)
    
    # 如果指定了测试用例ID，过滤测试用例
    if args.case_ids:
        specified_ids = [int(id.strip()) for id in args.case_ids.split(',')]
        test_cases = [case for case in test_cases if case.get('id') in specified_ids]
        logger.info(f"已过滤测试用例，仅运行ID在 {specified_ids} 中的用例")
    
    logger.info(f"加载了 {len(test_cases)} 个测试用例")
    
    # 逐个执行测试用例
    for case in test_cases:
        try:
            # 使用框架运行测试用例
            result = framework.run_test_case(case)
            logger.info(f"测试用例 {case.get('title', case.get('name'))} 执行{'成功' if result['status'] == 'passed' else '失败'}")
        except Exception as e:
            logger.error(f"测试用例 {case.get('title', case.get('name'))} 执行失败，但继续执行其他用例: {str(e)}")
    
    # 生成报告
    report = framework.generate_report()
    
    # 如果指定了报告文件，保存报告
    if args.report:
        framework.save_report(args.report)
        logger.info(f"测试报告已保存到: {args.report}")
    
    return report


def save_report(report: dict, file_path: str) -> None:
    """
    保存测试报告到文件
    
    Args:
        report: 测试报告字典
        file_path: 文件路径
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"测试报告已保存到: {file_path}")
    except Exception as e:
        logger.error(f"保存测试报告失败: {str(e)}")


def display_report_summary(report: dict) -> None:
    """
    显示测试报告摘要
    
    Args:
        report: 测试报告字典
    """
    print("=" * 60)
    print("测试执行报告摘要")
    print("=" * 60)
    print(f"项目名称: {report.get('project_name', 'N/A')}")
    print(f"开始时间: {report.get('start_time', 'N/A')}")
    print(f"结束时间: {report.get('end_time', 'N/A')}")
    print(f"总耗时: {report.get('total_time', 0):.3f} 秒")
    print(f"测试用例总数: {report.get('total_cases', 0)}")
    print(f"通过: {report.get('passed_cases', 0)}")
    print(f"失败: {report.get('failed_cases', 0)}")
    print(f"通过率: {report.get('pass_rate', 0):.2f}%")
    print("=" * 60)
    
    # 显示失败的测试用例
    failed_details = [d for d in report.get('details', []) if d['status'] == 'failed']
    if failed_details:
        print("\n失败的测试用例:")
        for detail in failed_details:
            print(f"- {detail['case_name']} (ID: {detail['case_id']})")
            if detail.get('error'):
                print(f"  错误信息: {detail['error']}")
        print("=" * 60)


def main() -> int:
    """
    主函数
    
    Returns:
        退出码，0表示成功，非0表示失败
    """
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 如果启用详细日志，调整日志级别
        if args.verbose:
            logger.setLevel('DEBUG')
        
        # 运行测试
        report = run_tests(args)
        
        # 显示报告摘要
        display_report_summary(report)
        
        # 根据测试结果返回退出码
        return 0 if report.get('failed_cases', 0) == 0 else 1
        
    except Exception as e:
        logger.error(f"运行测试时发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 2


if __name__ == '__main__':
    sys.exit(main())

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
