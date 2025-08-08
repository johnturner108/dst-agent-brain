# 测试文件夹

标准的unittest测试，简洁高效！

## 文件结构

```
tests/
├── __init__.py              # 测试包初始化
├── README.md               # 本文档
├── config_test.json        # 测试专用配置文件(可选)
├── run_tests.py           # 测试运行器
└── test_model_stream.py   # AI模型流式输出单元测试
```

## 使用方法

### 1. 运行所有测试 (推荐)
```bash
cd tests
python run_tests.py
```

### 2. 运行特定测试
```bash
# 运行特定测试模块
python run_tests.py test_model_stream

# 或直接运行测试文件
python test_model_stream.py
```

### 3. 使用标准unittest
```bash
# 运行所有测试
python -m unittest discover

# 运行特定测试类
python -m unittest test_model_stream.TestModelStream

# 运行特定测试方法
python -m unittest test_model_stream.TestModelStream.test_basic_stream_output
```

## 测试内容

### TestModelStream类
- `test_model_creation()` - 测试模型创建
- `test_model_info()` - 测试模型信息获取  
- `test_basic_stream_output()` - 测试基本流式输出
- `test_abort_functionality()` - 测试中止功能
- `test_different_temperatures()` - 测试不同温度参数

### TestModelConfig类
- `test_config_loading()` - 测试配置加载
- `test_model_type()` - 测试模型类型

### 预期输出示例
```bash
$ python test_model_stream.py
test_abort_functionality (__main__.TestModelStream) ... ok
test_basic_stream_output (__main__.TestModelStream) ... ok
test_different_temperatures (__main__.TestModelStream) ... ok
test_model_creation (__main__.TestModelStream) ... ok
test_model_info (__main__.TestModelStream) ... ok
test_config_loading (__main__.TestModelConfig) ... ok
test_model_type (__main__.TestModelConfig) ... ok

----------------------------------------------------------------------
Ran 7 tests in 8.234s

OK
```

## 优势

✅ **标准unittest框架** - 使用Python标准库，无需额外依赖  
✅ **@装饰器支持** - 使用setUp、tearDown等标准装饰器  
✅ **断言丰富** - assertTrue、assertEqual等标准断言方法  
✅ **自动发现** - 支持测试自动发现和批量运行  
✅ **详细报告** - 清晰的测试结果和错误报告  

## 添加新测试

创建新的测试文件，继承`unittest.TestCase`:

```python
import unittest

class TestNewFeature(unittest.TestCase):
    
    def setUp(self):
        """每个测试方法前执行"""
        pass
    
    def test_something(self):
        """测试某个功能"""
        self.assertTrue(True)
        
    def tearDown(self):
        """每个测试方法后执行"""
        pass

if __name__ == '__main__':
    unittest.main()
```
