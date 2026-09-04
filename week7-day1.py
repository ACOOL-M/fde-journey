"""
Week 7 Day 1: AI Agent 自主规划（教学演示）

这是 FDE 进阶最核心的技能 —— 让 AI 不只是"调工具"，而是"自主规划"。

核心概念：ReAct 循环
  Thought → Action → Observation → Thought → Action → ...

对比：
  - 普通 Function Calling：你写好 if-else，AI 按顺序调
  - Agent：AI 看目标，自己拆步骤，自己决定调什么工具、什么时候停

演示场景：30 天内推动比亚迪签 50 万订单
  Agent 自主规划：
    1. 查客户信息
    2. 评估 50 万可行性
    3. 查跟进历史
    4. 推荐资料
    5. 创建跟进任务
    6. 输出完整方案
"""

import requests
import json
import os


# ============ API 配置（部署友好版） ============

def load_api_key():
    """优先从环境变量/st.secrets 取，本地回退 key.txt"""
    key = os.environ.get("DASHSCOPE_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        key = st.secrets.get("DASHSCOPE_API_KEY")
        if key:
            return key
    except Exception:
        pass
    try:
        with open("key.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise RuntimeError("未找到 API Key，请配置 key.txt 或环境变量 DASHSCOPE_API_KEY")


API_KEY = load_api_key()
CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


# ============ 工具集：销售跟进相关的真实函数 ============

def get_customer_info(name):
    """查询客户档案"""
    customers = {
        "比亚迪": {"等级": "A", "预算": 150, "联系人": "张工", "行业": "制造业", "关心": "数据安全、ERP 集成"},
        "美的": {"等级": "A", "预算": 200, "联系人": "李经理", "行业": "家电", "关心": "AI 客服降本"},
        "拼多多": {"等级": "A", "预算": 200, "联系人": "王总", "行业": "电商", "关心": "用户增长、ROI"},
        "腾讯云": {"等级": "A", "预算": 500, "联系人": "陈总", "行业": "云服务", "关心": "大模型集成"},
        "广汽埃安": {"等级": "B", "预算": 80, "联系人": "刘经理", "行业": "新能源车", "关心": "智能座舱"},
    }
    return customers.get(name, {"错误": f"未找到客户 {name}"})


def evaluate_deal(customer_name, amount):
    """评估订单可行性"""
    customer = get_customer_info(customer_name)
    if "错误" in customer:
        return customer
    budget = customer["预算"]
    level = customer["等级"]
    feasible = amount <= budget
    probability_map = {
        "A": 0.7 if feasible else 0.3,
        "B": 0.5 if feasible else 0.2,
        "C": 0.3 if feasible else 0.1,
    }
    probability = probability_map.get(level, 0.2)
    return {
        "客户": customer_name,
        "等级": level,
        "目标金额": f"{amount} 万",
        "客户预算": f"{budget} 万",
        "金额可行": feasible,
        "成交概率": f"{int(probability * 100)}%",
        "建议": "建议推进" if feasible else "建议调整金额或争取预算扩容",
    }


def search_history(customer_name):
    """查询跟进历史"""
    history = {
        "比亚迪": [
            {"日期": "2026-08-15", "动作": "首次拜访", "结果": "对数据安全模块感兴趣"},
            {"日期": "2026-08-25", "动作": "技术交流", "结果": "技术团队评估中"},
        ],
        "美的": [
            {"日期": "2026-09-01", "动作": "电话沟通", "结果": "已发送产品资料"},
        ],
    }
    return {"客户": customer_name, "跟进记录": history.get(customer_name, "暂无")}


def recommend_materials(customer_name):
    """推荐准备资料"""
    customer = get_customer_info(customer_name)
    if "错误" in customer:
        return customer
    industry = customer.get("行业", "")
    mapping = {
        "制造业": ["制造业案例集.pdf", "宁德时代签约新闻", "数据安全白皮书", "POC 测试方案"],
        "家电": ["美的 AI 客服试点报告", "ROI 计算模板", "竞品对比表"],
        "电商": ["拼多多用户增长方案", "私域运营白皮书"],
        "云服务": ["大模型 API 文档", "云原生部署方案"],
        "新能源车": ["智能座舱集成方案", "车机系统对接白皮书"],
    }
    return {"客户": customer_name, "行业": industry, "推荐资料": mapping.get(industry, ["产品概述.pdf"])}


def create_followup_task(customer_name, action_type, due_date):
    """创建跟进任务"""
    return {
        "状态": "已创建",
        "客户": customer_name,
        "动作": action_type,
        "截止日期": due_date,
        "创建时间": "2026-09-04",
    }


# ============ 工具 Schema 定义（告诉 AI 你有什么工具） ============

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_info",
            "description": "查询客户档案（等级、预算、联系人、行业、关心点）",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "客户名称"}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_deal",
            "description": "评估特定金额订单的成交概率",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "amount": {"type": "number", "description": "目标金额（万元）"},
                },
                "required": ["customer_name", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_history",
            "description": "查询客户的历史跟进记录",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                },
                "required": ["customer_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_materials",
            "description": "根据客户行业推荐准备资料",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                },
                "required": ["customer_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_followup_task",
            "description": "创建跟进任务",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "action_type": {"type": "string"},
                    "due_date": {"type": "string", "description": "截止日期 YYYY-MM-DD"},
                },
                "required": ["customer_name", "action_type", "due_date"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "get_customer_info": get_customer_info,
    "evaluate_deal": evaluate_deal,
    "search_history": search_history,
    "recommend_materials": recommend_materials,
    "create_followup_task": create_followup_task,
}


# ============ ReAct Agent 主循环 ============

SYSTEM_PROMPT = """你是一个 B 端销售总监 Agent，正在为销售团队制定客户跟进策略。

**工作循环（ReAct）**：
1. **Thought**：分析当前情况，决定下一步
2. **Action**：调用合适的工具获取信息或执行操作
3. **Observation**：看工具返回的结果
4. 重复以上，直到能给出完整方案

**规则**：
- 必须用工具查询真实数据，不能凭空想象
- 至少调用 5 个工具，覆盖：客户信息 → 评估 → 历史 → 资料 → 任务
- 完成所有步骤后，输出"FINAL_ANSWER: "开头的完整方案

输出每个步骤时，用清晰的中文说明你的思考过程。"""


def run_agent(user_goal, max_steps=8, verbose=True):
    """运行 Agent 自主规划循环"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"销售目标：{user_goal}\n\n请自主规划完成这个目标的步骤。"},
    ]

    for step in range(max_steps):
        if verbose:
            print(f"\n{'=' * 60}")
            print(f"🤖 Agent 第 {step + 1} 步")
            print("=" * 60)

        # 调用 LLM
        response = requests.post(
            CHAT_URL,
            headers=HEADERS,
            json={
                "model": "qwen-plus",
                "messages": messages,
                "tools": TOOLS,
                "temperature": 0.3,
            },
            timeout=30,
        )

        result = response.json()
        if "error" in result:
            if verbose:
                print(f"❌ API 错误：{result}")
            return None

        message = result["choices"][0]["message"]
        messages.append(message)

        # 检查是否调用工具
        if message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                func_name = tool_call["function"]["name"]
                func_args = json.loads(tool_call["function"]["arguments"])

                if verbose:
                    print(f"🧠 思考：{message.get('content', '(继续)')}")
                    print(f"🔧 行动：{func_name}({json.dumps(func_args, ensure_ascii=False)})")

                # 执行工具
                tool_func = TOOL_FUNCTIONS.get(func_name)
                if tool_func:
                    tool_result = tool_func(**func_args)
                else:
                    tool_result = {"错误": f"未知工具 {func_name}"}

                if verbose:
                    print(f"👁️ 观察：{json.dumps(tool_result, ensure_ascii=False, indent=2)}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })
        else:
            # AI 决定停下了
            final_answer = message.get("content", "")
            if verbose:
                print(f"\n{'=' * 60}")
                print("✅ Agent 完成任务")
                print("=" * 60)
                print(final_answer)
            return final_answer

    return None


# ============ 主程序 ============

if __name__ == "__main__":
    print("=" * 60)
    print("🎯 AI Agent 自主规划演示")
    print("=" * 60)
    print()
    print("你将看到 Agent 自己拆解复杂任务，决定调用哪些工具、")
    print("什么时候停下。")
    print()
    print("对比固定流程：")
    print("  - 固定流程：你写 if-else，AI 按顺序执行")
    print("  - Agent：AI 看目标，自主决定")
    print()

    # 演示场景
    goal = "30 天内推动比亚迪签约 50 万 WorkBuddy 企业版订单"
    print(f"📋 销售目标：{goal}")
    print()

    run_agent(goal, max_steps=8)

    print("\n" + "=" * 60)
    print("🎓 关键学习")
    print("=" * 60)
    print("""
1. Agent = LLM + 工具集 + ReAct 循环
2. ReAct = Reasoning + Acting（思考 + 行动）
3. AI 自主决策：不是程序员写死流程
4. 看 AI 的"思考"就知道为什么调这个工具

实战价值：
  - 销售跟进：给目标，AI 自主设计节点
  - 客户分析：AI 自动查多维度数据
  - 方案生成：AI 综合所有信息输出建议
""")