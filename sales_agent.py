"""
实战项目：AI 销售助理（带工具的 Agent）
功能：
  1. 查客户信息（等级、预算、联系人）
  2. 按客户等级自动计算折扣报价
  3. 登记产品演示预约
核心：AI 自己决定调用哪个工具，你的代码执行真实操作
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

# ============ 工具函数 1：客户数据库 ============

CUSTOMERS = {
    "比亚迪":   {"level": "A", "budget": 150, "contact": "张工",   "product": "WorkBuddy企业版"},
    "美的":     {"level": "B", "budget": 60,  "contact": "李经理", "product": "WorkBuddy专业版"},
    "拼多多":   {"level": "A", "budget": 200, "contact": "王总",   "product": "WorkBuddy企业版"},
    "腾讯云":   {"level": "A", "budget": 180, "contact": "陈总",   "product": "WorkBuddy企业版"},
    "宁德时代": {"level": "B", "budget": 80,  "contact": "刘工",   "product": "WorkBuddy专业版"},
}

BOOKINGS = []  # 演示预约记录（真实项目中会写入数据库）


def get_customer_info(company_name):
    """查询客户基本信息"""
    info = CUSTOMERS.get(company_name)
    if info:
        return json.dumps(info, ensure_ascii=False)
    return json.dumps({"error": f"未找到 {company_name} 的客户信息"}, ensure_ascii=False)


def calc_discount(company_name, unit_price):
    """
    按客户等级计算折扣报价
    A 级客户: 85 折 | B 级客户: 92 折 | 其他: 无折扣
    """
    info = CUSTOMERS.get(company_name)
    if not info:
        return json.dumps({"error": f"未找到 {company_name}"}, ensure_ascii=False)

    level = info["level"]
    if level == "A":
        rate = 0.85
    elif level == "B":
        rate = 0.92
    else:
        rate = 1.0

    final_price = round(unit_price * rate, 2)
    return json.dumps({
        "company": company_name,
        "level": level,
        "unit_price": unit_price,
        "discount_rate": rate,
        "final_price": final_price,
        "saved": round(unit_price - final_price, 2)
    }, ensure_ascii=False)


def book_demo(company_name, date, time_slot):
    """登记产品演示预约"""
    info = CUSTOMERS.get(company_name)
    if not info:
        return json.dumps({"error": f"未找到 {company_name}"}, ensure_ascii=False)

    booking = {
        "company": company_name,
        "contact": info["contact"],
        "date": date,
        "time": time_slot,
        "status": "已预约"
    }
    BOOKINGS.append(booking)
    return json.dumps(booking, ensure_ascii=False)


# ============ 工具清单（JSON Schema） ============

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_info",
            "description": "查询客户的基本信息，包括客户等级、预算和联系人。当用户询问某个客户的情况时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "公司名称，例如：比亚迪"}
                },
                "required": ["company_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calc_discount",
            "description": "根据客户等级计算折扣报价。当用户询问价格、报价、折扣、多少钱时使用。unit_price 是每套产品的标准单价（万元）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "公司名称"},
                    "unit_price": {"type": "number", "description": "标准单价，单位：万元"}
                },
                "required": ["company_name", "unit_price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_demo",
            "description": "登记产品演示预约。当用户想预约演示、安排演示时间时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "公司名称"},
                    "date": {"type": "string", "description": "预约日期，格式：2026-09-05"},
                    "time_slot": {"type": "string", "description": "时间段，例如：下午3点"}
                },
                "required": ["company_name", "date", "time_slot"]
            }
        }
    }
]

# ============ 工具执行器：把函数名映射到真实代码 ============

TOOL_FUNCTIONS = {
    "get_customer_info": get_customer_info,
    "calc_discount": calc_discount,
    "book_demo": book_demo,
}

# ============ 调用循环 ============

def run_agent(user_question):
    """完整的 Agent 循环：支持 AI 连续调用多个工具"""
    messages = [{"role": "user", "content": user_question}]

    for round_num in range(5):  # 最多循环 5 轮，防止死循环
        payload = {
            "model": "qwen-plus",
            "messages": messages,
            "tools": TOOLS,
            "temperature": 0.2
        }
        resp = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
        data = resp.json()
        ai_msg = data["choices"][0]["message"]

        # AI 不再要求调用工具 → 输出最终回答，结束
        if not ai_msg.get("tool_calls"):
            return ai_msg["content"]

        # AI 要求调用工具 → 逐个执行
        messages.append(ai_msg)
        for tool_call in ai_msg["tool_calls"]:
            func_name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])
            print(f"🔧 第{round_num+1}轮调用: {func_name}({args})")

            # 执行真实代码
            result = TOOL_FUNCTIONS[func_name](**args)
            print(f"✅ 返回: {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result
            })

    return "⚠️ 调用轮次过多，已停止。"


# ============ 主程序 ============
if __name__ == "__main__":
    print("=" * 60)
    print("💼 AI 销售助理（带工具的 Agent）")
    print("=" * 60)

    demo_questions = [
        "帮比亚迪算一下报价，标准单价100万一套，能便宜多少？",
        "美的想预约下周一上午10点演示，帮我登记一下",
        "查一下腾讯云的客户情况，然后按80万单价报价，再预约9月8号下午2点演示",
    ]

    print("\n【自动演示 3 个场景】\n")
    for q in demo_questions:
        print(f"👤 用户: {q}")
        print("-" * 40)
        answer = run_agent(q)
        print(f"🤖 AI: {answer}")
        print()

    # 实战：自己输入
    print("=" * 60)
    print("【实战练习】自己指挥 AI 销售助理")
    print("可以试试：")
    print("  · 查一下宁德时代的客户信息")
    print("  · 拼多多按120万单价报价")
    print("  · 帮腾讯云预约后天下午的演示")
    print("  · 输入 exit 退出")
    print("=" * 60)

    while True:
        user_input = input("\n> ").strip()
        if user_input.lower() in ("exit", "quit", "退出"):
            print("👋 再见！销售助理已下线。")
            break
        if not user_input:
            continue
        print("-" * 40)
        try:
            answer = run_agent(user_input)
            print(f"🤖 AI: {answer}")
        except Exception as e:
            print(f"❌ 出错了: {e}")

    # 输出预约记录
    print("\n📅 当前演示预约记录:")
    for b in BOOKINGS:
        print(f"   · {b['company']} | {b['date']} {b['time']} | 联系人 {b['contact']} | {b['status']}")
