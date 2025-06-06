# 导入系统和正则表达式模块
import os
import re
# 导入Pydantic数据模型
from pydantic import BaseModel
# 导入OpenAI客户端及异常处理类
from openai import AsyncOpenAI, APIError, APIConnectionError, AuthenticationError
from fastapi import FastAPI, HTTPException, status, Depends, Request
# 导入日期时间模块并设置时区支持
from datetime import datetime, timezone
# 导入JSON处理模块
import json
# 导入ASGI服务器
import uvicorn
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


# 创建FastAPI应用实例
app = FastAPI()

# 初始化模型客户端,这里使用的AsyncOpenAI进行异步API调用
client = AsyncOpenAI(
    api_key="填写你的密钥哦~",  # API密钥
    base_url="https://aistudio.baidu.com/llm/lmapi/v3"  # 百度AI Studio接口地址
)

# 请求数据模型定义
class TodoRequest(BaseModel):
    user_id: str     # 新增：用户ID
    group_id: str    # 新增：群ID
    content: str     # 微信消息内容
    sender: str      # 发送者微信名
    group_name: str  # 群聊名称

# 响应数据模型定义
class TodoResponse(BaseModel):
    status: str = "Succeed"
    user_id: str = None    # 新增：用户ID
    group_id: str = None   # 新增：群ID
    is_todo: bool          # 是否为待办事项
    sender: str = None     # 发送者（仅当is_todo=True时存在）
    content: str = None    # 待办内容
    group_name: str = None # 群聊名称
    timestamp: datetime = None  # 消息时间戳
    is_public: bool = False    # 是否公开（默认否）
    is_repeated: bool = False  # 是否重复任务（默认否）
    completed: bool = False    # 是否完成（默认否）

    class Config:
        # 自定义JSON序列化格式，时间格式化为ISO8601
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M") if v else None
        }

# 定义ERNIE模型的提示指令
prompt = """
你是一个待办事项检测专家，需要判断微信群聊消息是否为待办事项。请严格按以下规则处理：

【待办特征】
1. 明确任务指令：
   - 包含动作动词（如：准备、完成、发送、联系、提供、确认等）
   - 指定具体对象（如：报告、文件、会议、订单等）
   - 示例："请准备Q3财务报告"、"明天前发送合作方案"

2. 客户特殊请求：
   - 明确索取信息："请提供xxx合同模板"
   - 需要专业解答："请教一下税务认定流程"
   - 确认进度询问："项目报告什么时候能完成"
   - 问题询问类请求："哈喽，行业政策变化(如环保要求、监管新规)对公司经营及财务的影响如何?"

3. 附加特征：
   - 包含时间节点："明早9点前"
   - 指定责任人："李经理负责对接"
   - 明确结果要求："需要盖章版本"

4. 混合消息优先级规则：
    当消息包含多个语义单元时，需仔细分析，若整体语句描述内，存在请求特征或动作特征，必须判定为待办
   - 示例："陈总早晨好，请教下税务局认定流程" → 待办
   - 示例："你好，这份文件今天能完成吗" → 待办
   - 示例："问你一下，社保政策是否新调整呀" → 待办

【排除条件】
1. 群聊讨论特征：
   - 主观陈述："我觉得这个方案可行"
   - 过程描述："根据之前的讨论..."
   - 状态汇报："目前进展顺利"
   - 单纯疑问句式（非任务请求）："这个怎么处理？"
   - 无具体内容："这个怎么处理/最近怎么样"
   - 讨论陈述："根据讨论/我觉得可行/目前进展"

2. 非任务交互：
   - 礼貌问候："早上好"
   - 简单确认："收到"
   - 情感表达："辛苦了"
   - 闲聊对话："最近怎么样"

【输出规则】
- 非待办事项仅返回：{"is_todo": false}
- 待办事项返回完整JSON结构：
{
  "is_todo": true,
  "sender": "发送人微信名",
  "content": "待办事项内容",
  "group_name": "群聊名称",
  "timestamp": "消息时间戳（ISO8601格式）"
}
- 严格按JSON格式输出，禁止任何解释性文字
"""

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        # status_code=exc.status_code,
        content=exc.detail
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_msg = exc.errors()[0]['msg']
    return JSONResponse(
        # status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "Failed", "reason": f"参数校验失败: {error_msg}"}
    )

# 定义POST接口处理函数
@app.post("/detect-todo", response_model=TodoResponse)
async def detect_todo(request: TodoRequest):
    try:
        # 获取当前带时区的时间戳
        current_time = datetime.now(timezone.utc).astimezone()
        
        
        # 构建模型输入消息
        message = (
            f"消息时间：{current_time.strftime('%Y-%m-%dT%H:%M')}\n"
            f"用户ID：{request.user_id}\n"        # 新增
            f"群ID：{request.group_id}\n"          # 新增
            f"发送人：{request.sender}\n"
            f"群聊名称：{request.group_name}\n"
            f"消息内容：{request.content}"
        )
        
        # 调用ERNIE模型进行推理
        response = await client.chat.completions.create(
            model="ernie-4.5-8k-preview",  # 使用ERNIE 4.5预览版模型
            messages=[
                {"role": "system", "content": prompt},  # 系统指令
                {"role": "user", "content": message}    # 用户输入
            ],
            temperature=0.1,  # 降低温度值提高确定性
            timeout=15        # 设置15秒超时
        )
        
        # 检查响应有效性
        if not response.choices or not response.choices[0].message:
            raise ValueError("Empty response from OpenAI")
            
        # 提取并清理原始响应内容
        raw_content = response.choices[0].message.content.strip()
        print(f"Raw Response: {raw_content}")  # 调试输出
        
        # 使用正则表达式提取JSON结构
        json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        if not json_match:
            return TodoResponse(
            is_todo=False,
            user_id=request.user_id,        # 新增
            group_id=request.group_id       # 新增
        )
            
        cleaned_content = json_match.group(0)
        
        # 解析JSON并验证字段完整性
        try:
            result = json.loads(cleaned_content)
        except json.JSONDecodeError:
            return TodoResponse(
            is_todo=False,
            user_id=request.user_id,        # 新增
            group_id=request.group_id       # 新增
        )
            
        # 检查必要字段是否存在
        required_fields = {"is_todo", "sender", "content", "group_name", "timestamp"}
        if not required_fields.issubset(result.keys()):
            return TodoResponse(
            is_todo=False,
            user_id=request.user_id,        # 新增
            group_id=request.group_id       # 新增
        )
            
        # 处理有效待办事项响应
        if result["is_todo"]:
            return TodoResponse(
                user_id=request.user_id,     # 新增
                group_id=request.group_id,   # 新增
                is_todo=True,
                sender=request.sender,
                content=request.content,
                group_name=request.group_name,
                timestamp=current_time  # 保持datetime对象自动格式化
            )
        return TodoResponse(
            is_todo=False,
            user_id=request.user_id,        # 新增
            group_id=request.group_id       # 新增
        )
        
    # 异常处理块
    except APIError as e:
        print(f"OpenAI API Error: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "Failed", "reason": "OpenAI服务暂时不可用"}
        )
    except AuthenticationError:
        print("API密钥验证失败")
        raise HTTPException(
            status_code=401,
            detail={"status": "Failed", "reason": "无效的OpenAI API密钥"}
        )
    except APIConnectionError:
        print("无法连接到OpenAI服务")
        raise HTTPException(
            status_code=503,
            detail={"status": "Failed", "reason": "网络连接失败"}
        )
    except Exception as e:
        print(f"未知错误：{str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"status": "Failed", "reason": "内部服务器错误"}
        )

# 启动服务器配置
if __name__ == "__main__":
    uvicorn.run(
        app,      # 可以更换成app
        host="0.0.0.0",  # 监听所有网络接口
        port=8088,        # 使用8088端口
    )