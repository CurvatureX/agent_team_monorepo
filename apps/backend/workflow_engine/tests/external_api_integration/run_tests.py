#!/usr/bin/env python3
"""
外部API集成测试运行器
用于在开发过程中快速运行测试套件
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_tests(test_type="all", verbose=False, coverage=False):
    """运行测试套件"""
    
    # 基础pytest命令
    cmd = ["python", "-m", "pytest"]
    
    # 添加测试路径
    test_dir = Path(__file__).parent
    
    if test_type == "unit":
        cmd.extend(["-m", "unit", str(test_dir)])
    elif test_type == "integration":
        cmd.extend(["-m", "integration", str(test_dir)])
    elif test_type == "oauth2":
        cmd.extend(["-m", "oauth2", str(test_dir)])
    elif test_type == "external_api":
        cmd.extend(["-m", "external_api", str(test_dir)])
    elif test_type == "all":
        cmd.append(str(test_dir))
    else:
        print(f"Unknown test type: {test_type}")
        return 1
    
    # 添加详细输出
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # 添加覆盖率
    if coverage:
        cmd.extend([
            "--cov=workflow_engine.services", 
            "--cov=workflow_engine.nodes",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    # 添加其他有用的选项
    cmd.extend([
        "--tb=short",  # 短的traceback格式
        "--strict-markers",  # 严格的标记模式
        "-W", "ignore::DeprecationWarning"  # 忽略废弃警告
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 130
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return 1

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="外部API集成测试运行器")
    
    parser.add_argument(
        "--type", "-t",
        choices=["all", "unit", "integration", "oauth2", "external_api"],
        default="all",
        help="测试类型 (默认: all)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="生成覆盖率报告"
    )
    
    parser.add_argument(
        "--watch", "-w",
        action="store_true", 
        help="监听文件变化并自动重新运行测试"
    )
    
    args = parser.parse_args()
    
    if args.watch:
        try:
            import pytest_watch
        except ImportError:
            print("需要安装 pytest-watch: pip install pytest-watch")
            return 1
        
        cmd = ["ptw", "--", "-m", args.type if args.type != "all" else ""]
        if args.verbose:
            cmd.append("-v")
        subprocess.run(cmd)
        return 0
    
    return run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage
    )

if __name__ == "__main__":
    sys.exit(main())