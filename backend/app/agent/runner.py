"""
agent/runner.py —— 智能体主循环（Agent Loop，流式版）

═══════════════════════════════════════════════════════════════════
【v0.2 升级点】
1. 流式：大模型每生成一小段文字，立即通过 yield "播报"给前端（SSE），
   用户看到的是逐字出现，而不是干等十几秒
2. 过程可视化：思考中 / 调用什么工具 / 执行结果，每一步都发 status 事件，
   前端实时显示"智能体正在干嘛"
3. 多轮对话：接受 history 参数，把之前的对话一起带给大模型——
   它才能理解"不用""明天"这种依赖上下文的简短回答
4. 澄清机制：系统提示要求模型在"信息不足时先反问"（见 SYSTEM_PROMPT）

事件协议（前端按 event 类型分别处理）：
    ("status", {"step": "thinking"})                        开始思考
    ("reasoning", {"text": "思考碎片"})                      模型的深度思考过程（灰色折叠块展示）
    ("delta",  {"text": "部分文字"})                         最终回复的增量文字
    ("status", {"step": "tool", "name":..., "args":...})    即将调用工具
    ("status", {"step": "tool_result", ...})                工具执行完成
    ("done",   {"reply": 完整回复, "actions": [...]})        一切结束
═══════════════════════════════════════════════════════════════════
"""

import json
import logging
from datetime import datetime

from app.agent import llm, tools

logger = logging.getLogger("agent")

MAX_STEPS = 6  # 一轮对话最多允许大模型调用工具的次数

SYSTEM_PROMPT = """你是"AI 待办助手"，通过调用工具帮用户管理待办事项。

今天的日期是 {today}，{weekday}。
用户说的"明天""下周三"这类相对日期，你需要根据今天的日期换算成 YYYY-MM-DD 再传参。

对话规则：
1. 涉及查、增、完成、删除待办的操作，必须调用对应工具，不要凭空编造数据
2. 【澄清机制】用户要添加待办但没有提到时间时，先反问一句（比如"需要设置截止时间吗？"），
   等用户回答后再创建；用户回答不需要时，不传 due_date 直接创建。
   用户已经说了时间/日期的，直接创建，不要多问。
3. 【澄清机制】用户要完成或删除某条待办、但有多条都可能匹配时，
   先把候选列表出来让用户选（带上 id），不要靠猜。
4. 工具返回的 todo_id 要原样告诉用户，方便他们之后说"把第 3 条完成"
5. 你有对话历史记忆：用户的简短回答（如"不用""明天""就第一个"）要联系你上一句话来理解
6. 回复用中文，简洁友好，不要输出大段废话
"""


def _build_system_prompt() -> str:
    """把今天的日期动态填进系统提示，大模型才能理解'明天'是哪天。"""
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return SYSTEM_PROMPT.format(today=now.strftime("%Y-%m-%d"), weekday=weekdays[now.weekday()])


def _build_messages(user_message: str, history: list | None) -> list:
    """
    组装完整消息列表：[系统提示] + [历史对话] + [本次用户消息]

    大模型本身是无状态的——"记忆"的本质就是把历史一起发过去。
    history 是前端传来的之前的问答（只含 user/assistant 两种角色）。
    """
    messages = [{"role": "system", "content": _build_system_prompt()}]
    for m in history or []:
        # 防御：只接受两种合法角色，其他一律当作用户说的
        role = m.role if m.role in ("user", "assistant") else "user"
        messages.append({"role": role, "content": m.content})
    messages.append({"role": "user", "content": user_message})
    return messages


def run_agent_stream(user_message: str, history: list | None = None, user_id: int | None = None):
    """
    流式版智能体主循环：它是一个"生成器"（generator）。

    user_id：当前登录用户的 id，执行工具时注入（见 tools.py 的安全说明）。

    【知识点：yield 和生成器】
    普通函数 return 一次就结束；生成器函数用 yield 可以"吐"出很多次值，
    每吐一次就暂停，等调用方要下一个再继续跑。正好匹配流式场景：
    模型生成一段 → yield 给前端 → 模型再生成一段 → 再 yield……

    循环逻辑和非流式版完全一样：思考 → 要么回复要么调工具 → 调完再思考。
    区别只是每个环节都边发生边播报。
    """
    messages = _build_messages(user_message, history)
    actions = []
    logger.info("════ 新对话开始（用户 %s）════", user_id)
    logger.info("用户说: %s", user_message)

    for step in range(MAX_STEPS):
        yield "status", {"step": "thinking"}

        # ① 流式请求大模型：返回的不是完整结果，而是一串"增量碎片"(chunk)
        response = llm.chat(messages, tools=tools.TOOLS_SCHEMA, stream=True)

        content_parts = []  # 这轮模型输出的正文碎片，最后拼成完整回复
        pending_calls = {}  # 工具调用在流里也是碎片化的（函数名、参数分很多段到达），按 index 拼装

        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta  # delta = "这一小段新增的内容"
            # 思考过程碎片（glm-4.6 是深度思考模型，回答前会先输出 reasoning_content）。
            # 它不是给用户看的正文，而是模型的推理草稿——单独发 reasoning 事件，
            # 前端做成灰色可折叠块展示（ZCode/Claude 那种效果）
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield "reasoning", {"text": reasoning}
            # 正文碎片：立即转发给前端（这就是"真流式"——生成一个字推一个字）
            if getattr(delta, "content", None):
                content_parts.append(delta.content)
                yield "delta", {"text": delta.content}
            # 工具调用碎片：攒起来，凑完整了才执行
            for tc in getattr(delta, "tool_calls", None) or []:
                slot = pending_calls.setdefault(tc.index, {"id": None, "name": "", "arguments": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    slot["arguments"] += tc.function.arguments

        # ② 情况 a：没有工具调用 → 正文就是最终回复，播报 done 收工
        if not pending_calls:
            reply = "".join(content_parts)
            logger.info("AI最终回复: %s", reply)
            logger.info("════ 对话结束（第 %d 步）════", step + 1)
            yield "done", {"reply": reply, "actions": actions}
            return

        # ② 情况 b：模型要求调工具。先把它"想调工具"的消息原样补进历史（协议要求）
        messages.append(
            {
                "role": "assistant",
                "content": "".join(content_parts) or None,
                "tool_calls": [
                    {
                        "id": slot["id"] or f"call_{step}_{i}",
                        "type": "function",
                        "function": {"name": slot["name"], "arguments": slot["arguments"]},
                    }
                    for i, slot in sorted(pending_calls.items())
                ],
            }
        )

        # ③④ 逐个执行工具，把结果追加进历史。user_id 由后端注入，不信任模型参数
        for i, slot in sorted(pending_calls.items()):
            tool_name = slot["name"]
            tool_args = json.loads(slot["arguments"] or "{}")
            result = tools.execute_tool(tool_name, tool_args, user_id)
            actions.append({"tool": tool_name, "args": tool_args, "result": result})
            logger.info(
                "第%d步 调用工具: %s 参数: %s 结果: %s",
                step + 1,
                tool_name,
                json.dumps(tool_args, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
            )
            # 播报：调了什么工具、结果如何（前端实时显示进度）
            yield "status", {"step": "tool", "name": tool_name, "args": tool_args}
            yield "status", {"step": "tool_result", "name": tool_name, "result": result}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": slot["id"] or f"call_{step}_{i}",
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    yield (
        "done",
        {
            "reply": "这个任务有点复杂，工具调用次数达到上限了，我先停下来。你可以换个说法试试。",
            "actions": actions,
        },
    )


def run_agent(user_message: str, history: list | None = None, user_id: int | None = None) -> dict:
    """非流式版：把流式循环完整跑完再返回（方便 curl 测试和简单调用）。"""
    done = {"reply": None, "actions": []}
    for _event, payload in run_agent_stream(user_message, history, user_id):
        if _event == "done":
            done = payload
    return done
