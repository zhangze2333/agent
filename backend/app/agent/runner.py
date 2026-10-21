"""
agent/runner.py —— 智能体主循环（Agent Loop）

═══════════════════════════════════════════════════════════════════
一次智能体对话的完整流程（务必对照代码走一遍）：

  用户: "明天下午3点提醒我开会"
        │
        ▼
  ┌─> ① 把[系统提示+用户消息+工具说明书]发给大模型
  │       │
  │       ▼
  │   ② 大模型返回两种可能之一：
  │      a) 纯文字回复 ────────────────> 跳出循环，返回给用户 ✓
  │      b) "帮我调用 add_todo(...)":
  │           │
  │           ▼
  │   ③ 我们的代码真正执行 add_todo()，结果写入数据库
  │           │
  │           ▼
  │   ④ 把"工具执行结果"追加到对话历史，回到 ①
  └───────┘   （大模型看到"创建成功"后，这次会输出文字："好的，已帮你记下..."）

MAX_STEPS 的作用：万一大模型陷入"不停调工具"的死循环，强制刹车。
═══════════════════════════════════════════════════════════════════
"""
import json
from datetime import datetime

from app.agent import llm, tools

MAX_STEPS = 6  # 一轮对话最多允许大模型调用工具的次数

SYSTEM_PROMPT = """你是"AI 待办助手"，通过调用工具帮用户管理待办事项。

今天的日期是 {today}，{weekday}。
用户说的"明天""下周三"这类相对日期，你需要根据今天的日期换算成 YYYY-MM-DD 再传参。

规则：
1. 涉及查、增、完成、删除待办的操作，必须调用对应工具，不要凭空编造数据
2. 工具返回的 todo_id 要原样告诉用户，方便他们之后说"把第 3 条完成"
3. 回复用中文，简洁友好，不要输出大段废话
"""


def _build_system_prompt() -> str:
    """把今天的日期动态填进系统提示，大模型才能理解'明天'是哪天。"""
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return SYSTEM_PROMPT.format(today=now.strftime("%Y-%m-%d"), weekday=weekdays[now.weekday()])


def run_agent(user_message: str) -> dict:
    """
    执行一轮完整对话，返回给前端：
      reply   大模型最终说的那段话
      actions 这轮对话里实际执行了哪些工具（前端会展示出来，方便你理解 Agent 干了什么）
    """
    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": user_message},
    ]
    actions = []

    for step in range(MAX_STEPS):
        # ① 请求大模型
        response = llm.chat(messages, tools=tools.TOOLS_SCHEMA)
        assistant_msg = response.choices[0].message

        # ② 情况 a：没有要求调工具，说明它已经能给出最终回答了
        if not assistant_msg.tool_calls:
            return {"reply": assistant_msg.content, "actions": actions}

        # ② 情况 b：大模型要求调工具。
        # 先把它"想调工具"这条消息原样追加进历史（这是协议要求，
        # 否则下一步发历史时，tool 结果会找不到它对应的请求）
        messages.append(
            {
                "role": "assistant",
                "content": assistant_msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in assistant_msg.tool_calls
                ],
            }
        )

        # ③④ 逐个执行工具，把结果追加进历史
        for tc in assistant_msg.tool_calls:
            tool_name = tc.function.name
            tool_args = json.loads(tc.function.arguments or "{}")  # 参数是 JSON 字符串，要解析
            result = tools.execute_tool(tool_name, tool_args)
            actions.append({"tool": tool_name, "args": tool_args, "result": result})
            # role=tool 的消息必须带 tool_call_id，告诉大模型这是哪次调用的结果
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return {
        "reply": "这个任务有点复杂，工具调用次数达到上限了，我先停下来。你可以换个说法试试。",
        "actions": actions,
    }
