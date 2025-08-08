"""
简单的测试运行器
运行unittest测试
"""

import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_all_tests():
    """运行所有单元测试"""
    # 发现并运行所有测试
    loader = unittest.TestLoader()
    suite = loader.discover('.', pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_specific_test(test_name):
    """运行特定测试"""
    try:
        # 导入测试模块
        module = __import__(test_name)
        
        # 运行测试
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    except ImportError as e:
        print(f"❌ 无法导入测试模块 {test_name}: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="运行DST Agent Brain测试")
    parser.add_argument(
        'test', 
        nargs='?', 
        help='指定测试模块 (如: test_model_stream)'
    )
    parser.add_argument(
        '-v', '--verbose', 
        action='store_true', 
        help='详细输出'
    )
    
    args = parser.parse_args()
    
    if args.test:
        # 运行指定测试
        print(f"🧪 运行测试: {args.test}")
        success = run_specific_test(args.test)
    else:
        # 运行所有测试
        print("🧪 运行所有测试...")
        success = run_all_tests()
    
    if success:
        print("\n✅ 所有测试通过!")
    else:
        print("\n❌ 有测试失败!")
        sys.exit(1)
