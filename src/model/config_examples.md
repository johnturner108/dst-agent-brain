# AI模型配置示例

## 当前配置结构

您的 `config.json` 文件应该包含以下字段来配置AI模型：

```json
{
    "api_key": "您的API密钥",
    "base_url": "API基础URL",
    "model_name": "模型名称",
    "temperature": 0.7
}
```

## 不同AI服务提供商配置示例

### 1. Moonshot AI (Kimi)
```json
{
    "api_key": "sk-your-moonshot-api-key",
    "base_url": "https://api.moonshot.cn/v1",
    "model_name": "kimi-k2-0711-preview",
    "temperature": 0.6
}
```

### 2. 阿里云通义千问
```json
{
    "api_key": "sk-your-alibaba-api-key",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model_name": "qwen-turbo",
    "temperature": 0.6
}
```

### 3. OpenAI GPT
```json
{
    "api_key": "sk-your-openai-api-key",
    "base_url": "https://api.openai.com/v1",
    "model_name": "gpt-3.5-turbo",
    "temperature": 0.7
}
```

### 4. Azure OpenAI
```json
{
    "api_key": "your-azure-api-key",
    "base_url": "https://your-resource.openai.azure.com/openai/deployments/your-deployment/",
    "model_name": "gpt-35-turbo",
    "temperature": 0.7
}
```

### 5. 本地部署的模型 (如Ollama)
```json
{
    "api_key": "not-needed",
    "base_url": "http://localhost:11434/v1",
    "model_name": "llama2",
    "temperature": 0.7
}
```

## 配置说明

- `api_key`: API密钥，某些本地部署的服务可能不需要
- `base_url`: API服务的基础URL
- `model_name`: 要使用的具体模型名称
- `temperature`: 控制输出随机性的参数 (0.0-1.0)

## 更改配置

1. 编辑 `config.json` 文件
2. 重启应用程序以加载新配置
3. 系统会自动使用新的配置创建AI模型实例

所有OpenAI兼容的API都会被自动支持，无需修改代码。
