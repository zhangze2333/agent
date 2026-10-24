"""
agent/llm.py —— 封装大模型（GLM）的调用

【知识点：大模型 API 的通用套路】
几乎所有大模型（智谱 GLM / OpenAI / DeepSeek...）的接口都是同一个模式：
    传入 messages 列表 -> 返回 assistant 的回复

messages 里每条消息有 role（角色）：
    system    给 AI 的"幕后指令"：人设、规则。用户在界面上看不到
    user      用户说的话
    assistant AI 之前说过的话
    tool      工具执行结果（后面 agent 部分会用到）

【知识点：API key 为什么要放 .env？】
key = 你的钱包。写死在代码里一旦推到 GitHub，全世界的爬虫几小时内
就会扫到它、盗用你的额度。放 .env 文件并加入 .gitignore 是行业标准做法。
"""

import os

from dotenv import load_dotenv
from zhipuai import ZhipuAI

# 读取同目录（backend/）下的 .env 文件，把里面的键值对加载进环境变量
load_dotenv()

# 模型和接口地址都做成配置项，因为智谱有两种 key，入口不同：
# ① 普通个人 API key（免费）：不配 GLM_BASE_URL，模型用 glm-4-flash
# ② Coding Plan 编程套餐 key：必须走专用入口，模型用 glm-4.6 / glm-4.5
#    GLM_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4
# 用错入口的报错很有迷惑性（比如报"套餐已失效"），遇到先检查入口对不对
MODEL = os.getenv("GLM_MODEL", "glm-4-flash")
_base_url = os.getenv("GLM_BASE_URL", "")

# 还没配 key 时不报错，让待办 CRUD 功能照常能用；聊天接口会给出友好提示
_api_key = os.getenv("ZHIPU_API_KEY", "")
if _api_key:
    client = (
        ZhipuAI(api_key=_api_key, base_url=_base_url) if _base_url else ZhipuAI(api_key=_api_key)
    )
else:
    client = None


def is_configured() -> bool:
    """判断是否已配置 API key，chat 接口据此决定要不要返回 503 提示。"""
    return client is not None


def chat(messages: list, tools: list | None = None, stream: bool = False, **extra):
    """
    调用大模型。
    messages: 完整对话历史（大模型是无状态的，每次都要把历史带上它才"记得"之前说过什么）
    tools:    可选，告诉大模型它能调用哪些工具（见 tools.py）
    stream:   True 时返回"增量碎片"的可迭代对象（流式），False 时返回完整结果
    **extra:  其他要透传给 API 的参数（比如 thinking={"type": "enabled"} 控制深度思考）
    """
    kwargs = {"model": MODEL, "messages": messages}
    if tools:
        kwargs["tools"] = tools
    if stream:
        kwargs["stream"] = True
    kwargs.update(extra)
    return client.chat.completions.create(**kwargs)
