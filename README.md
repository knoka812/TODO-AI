# 待办事项检测服务

这是一个基于FastAPI和ERNIE大语言模型的智能待办事项检测服务，专门用于分析微信群聊消息并识别其中的待办事项。

## 功能特点

- 智能识别微信群聊中的待办事项
- 支持多维度分析：任务指令、客户请求、时间节点等
- 异步处理请求，提高响应效率
- 完善的错误处理机制
- 支持用户ID和群组ID的追踪
- 自动时间戳记录

## 技术栈

- FastAPI：高性能Web框架
- ERNIE 4.5：百度智能云大语言模型
- Pydantic：数据验证和序列化
- Uvicorn：ASGI服务器

## 安装说明

1. 克隆项目到本地
2. 安装依赖包：
```bash
pip install fastapi uvicorn openai pydantic
```

## 配置说明

在使用前，需要配置以下参数：

- API密钥：在代码中配置百度AI Studio的API密钥
- 服务端口：默认使用8088端口
- 模型参数：使用ERNIE 4.5预览版模型

## 使用方法

1. 启动服务：
```bash
python todo.py
```

2. API接口说明：
- 端点：`/detect-todo`
- 方法：POST
- 请求体格式：
```json
{
    "user_id": "用户ID",
    "group_id": "群组ID",
    "content": "消息内容",
    "sender": "发送者",
    "group_name": "群聊名称"
}
```

3. 响应格式：
```json
{
    "status": "Succeed",
    "user_id": "用户ID",
    "group_id": "群组ID",
    "is_todo": true/false,
    "sender": "发送者",
    "content": "待办内容",
    "group_name": "群聊名称",
    "timestamp": "时间戳",
    "is_public": false,
    "is_repeated": false,
    "completed": false
}
```

## 待办事项识别规则

服务会根据以下特征识别待办事项：

1. 明确任务指令
   - 包含动作动词
   - 指定具体对象
   - 包含时间节点

2. 客户特殊请求
   - 信息索取
   - 专业解答需求
   - 进度确认
   - 政策咨询

3. 排除条件
   - 群聊讨论
   - 非任务交互
   - 简单问候

## 错误处理

服务包含完善的错误处理机制，包括：
- API调用异常
- 参数验证错误
- 网络连接问题
- 认证失败处理

## 注意事项

1. 确保API密钥配置正确
2. 注意网络连接状态
3. 建议在生产环境中使用HTTPS
4. 定期检查API调用限制

## 许可证

MIT License 