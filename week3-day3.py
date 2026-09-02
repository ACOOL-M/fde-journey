"""
Week 3 Day 3: Function Calling 函数调用
核心：让 AI 不只是"聊天"，而是能"调用你的代码干活"

三要素：
1. 工具（你写的 Python 函数，真实代码）
2. 工具清单（JSON Schema，告诉 AI 你有哪些工具、参数是什么）
3. 调用循环（AI 决定调用 → 你执行 → 结果回传 → AI 组织回答）
"""

import requests
import json

# 读取 API Key
with open("key.txt", "r", encoding="utf-8") as f:
    API_KEY = f.read().strip()

URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ============ 第 1 步：定义你的工具函数（真实代码） ============

# 模拟客户数据库（真实项目中这里会是 CRM / 数据库）
CUSTOMERS = {
    "比亚迪": {"level": "A", "budget": 150, "contact": "张工"},
    "美的":   {"level": "B", "budget": 60,  "contact": "李经理"},
    "拼多多": {"level": "A", "budget": 200, "contact": "王总"},
    "腾讯云": {"level": "A", "budget": 180, "contact": "陈总"},
}


def get_customer_info(company_name):
    """查询客户基本信息（AI 不会写这段代码，但它会调用它）"""
    info = CUSTOMERS.get(company_name)
    if info:
        return f"{company_name}：等级{info['level']}级，预算{info['budget']}万，联系人{info['contact']}"
    return f"未找到 {company_name} 的客户信息"


# ============ 第 2 步：用 JSON Schema 告诉 AI "你有哪些工具" ============

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_info",
            "description": "查询客户的基本信息，包括客户等级、预算和联系人",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "公司名称，例如：比亚迪"
                    }
                },
                "required": ["company_name"]
            }
        }
    }
]

# ============ 第 3 步：完整的调用循环 ============

def ask_with_tools(user_question):
    """
    用户提问 → AI 决定调用工具 → 执行真实代码 → 回传给 AI 总结
    """
    messages = [{"role": "user", "content": user_question}]

    # 第一轮：把工具清单发给 AI
    payload = {
        "model": "qwen-plus",
        "messages": messages,
        "tools": TOOLS,
        "temperature": 0.3
    }
    resp = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
    data = resp.json()
    ai_msg = data["choices"][0]["message"]

    # 检查 AI 是否要求调用工具
    if ai_msg.get("tool_calls"):
        tool_call = ai_msg["tool_calls"][0]
        func_name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])
        print(f"🔧 AI 决定调用工具: {func_name}, 参数: {args}")

        # 执行真实代码（这是关键：数据必须来自你的代码，不是 AI 编的）
        if func_name == "get_customer_info":
            result = get_customer_info(args["company_name"])

        print(f"✅ 工具返回: {result}")

        # 把工具结果回传给 AI
        messages.append(ai_msg)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": result
        })

        # 第二轮：让 AI 基于真实数据组织回答
        payload["messages"] = messages
        resp2 = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
        return resp2.json()["choices"][0]["message"]["content"]

    # AI 判断不需要调用工具，直接回答
    return ai_msg["content"]


# ============ 主程序 ============
if __name__ == "__main__":
    print("=" * 60)
    print("🧰 Function Calling 演示：AI 智能客户查询")
    print("=" * 60)

    questions = [
        "帮我查一下比亚迪的客户信息",
        "美的这家客户的预算和联系人是谁？",
        "今天天气怎么样？",   # 故意问一个没有工具的问题
    ]

    for q in questions:
        print(f"\n👤 用户: {q}")
        print("-" * 40)
        answer = ask_with_tools(q)
        print(f"🤖 AI: {answer}")

    print("\n" + "=" * 60)
    print("今日要点：")
    print("1. AI 自己决定：什么时候用工具、用哪个、传什么参数")
    print("2. 真实数据来自你的代码，AI 只负责理解和表达")
    print("3. 没有对应工具时，AI 会直接回答（比如天气）")
    print("=" * 60)
