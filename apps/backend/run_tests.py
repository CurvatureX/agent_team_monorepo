#!/usr/bin/env python3
"""
测试运行器 - 统一测试入口
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from tests.auth.test_authentication import AuthenticationTest
from tests.session.test_session_management import SessionManagementTest
from tests.chat.test_streaming_response import StreamingResponseTest
from tests.chat.test_response_types import ResponseTypesTest
from tests.integration.test_complete_workflow import CompleteWorkflowTest

async def run_single_test(test_name: str):
    """运行单个测试"""
    test_map = {
        "auth": (AuthenticationTest, "认证功能测试"),
        "session": (SessionManagementTest, "会话管理测试"),
        "streaming": (StreamingResponseTest, "流式响应测试"),
        "types": (ResponseTypesTest, "三种返回类型测试"),
        "complete": (CompleteWorkflowTest, "完整集成测试"),
    }
    
    if test_name not in test_map:
        print(f"❌ 未知测试: {test_name}")
        print(f"可用测试: {', '.join(test_map.keys())}")
        return False
    
    test_class, test_description = test_map[test_name]
    
    print(f"🚀 运行 {test_description}")
    print("=" * 50)
    
    try:
        if test_name == "complete":
            # 完整测试有特殊的运行方法
            test_instance = test_class()
            success = await test_instance.run_complete_integration_test()
        else:
            test_instance = test_class()
            success = await test_instance.run_all_tests()
        
        return success
        
    except Exception as e:
        print(f"❌ 测试运行异常: {e}")
        return False

async def run_quick_test():
    """运行快速测试（基本功能验证）"""
    print("🚀 运行快速测试")
    print("=" * 50)
    
    # 只运行认证和流式响应测试
    quick_tests = [
        ("auth", "认证功能"),
        ("streaming", "流式响应"),
    ]
    
    results = []
    
    for test_name, test_description in quick_tests:
        print(f"\n--- {test_description} ---")
        success = await run_single_test(test_name)
        results.append((test_description, success))
    
    # 生成快速测试报告
    print("\n" + "=" * 50)
    print("📊 快速测试报告")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} {test_name}")
    
    print(f"\n通过率: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 快速测试全部通过！")
        print("✅ 系统基本功能正常")
    else:
        print("⚠️ 快速测试部分失败")
    
    return passed == total

def print_usage():
    """打印使用说明"""
    print("""
🧪 测试运行器 - 新工作流系统测试套件

用法:
  python run_tests.py [选项]

选项:
  --all, -a          运行完整集成测试（推荐）
  --quick, -q        运行快速测试（基本功能验证）
  --test TEST, -t    运行特定测试
  --list, -l         列出所有可用测试
  --help, -h         显示此帮助信息

可用测试:
  auth              认证功能测试
  session           会话管理测试
  streaming         流式响应测试
  types             三种返回类型测试
  complete          完整集成测试

示例:
  python run_tests.py --all                # 运行完整测试
  python run_tests.py --quick              # 运行快速测试
  python run_tests.py --test auth          # 只运行认证测试
  python run_tests.py --test streaming     # 只运行流式响应测试

环境要求:
  需要 API Gateway 在 localhost:8000 运行
  完整测试需要 .env 文件中的认证配置
  
测试架构:
  tests/auth/          认证功能测试
  tests/session/       会话管理测试  
  tests/chat/          聊天功能测试
  tests/integration/   集成测试
  tests/utils/         测试工具
""")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="新工作流系统测试运行器")
    parser.add_argument("--all", "-a", action="store_true", help="运行完整集成测试")
    parser.add_argument("--quick", "-q", action="store_true", help="运行快速测试")
    parser.add_argument("--test", "-t", type=str, help="运行特定测试")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有可用测试")
    
    args = parser.parse_args()
    
    if args.list:
        print("\n可用测试:")
        tests = [
            ("auth", "认证功能测试"),
            ("session", "会话管理测试"),
            ("streaming", "流式响应测试"),
            ("types", "三种返回类型测试"),
            ("complete", "完整集成测试"),
        ]
        for test_name, description in tests:
            print(f"  {test_name:<12} {description}")
        return True
    
    if args.all or args.test == "complete":
        # 运行完整集成测试
        return await run_single_test("complete")
    
    elif args.quick:
        # 运行快速测试
        return await run_quick_test()
    
    elif args.test:
        # 运行特定测试
        return await run_single_test(args.test)
    
    else:
        # 默认显示帮助
        print_usage()
        return True

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n❌ 测试运行异常: {e}")
        exit(1)