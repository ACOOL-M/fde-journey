"""
Week 7 Day 1: AI 销售跟进 Agent 网页版

把 Agent 自主规划做成网页应用，目标输入 + 实时显示 AI 的思考/行动/观察过程。
这是 FDE 进阶核心项目。
"""

import requests
import json
import streamlit as st
from datetime import datetime

# ============ 页面配置 ============

st.set_page_config(
    page_title="AI 销售跟进 Agent",
    page_icon="🎯",
    layout="wide",
)

# ============ API Key 加载 ============

API_KEY = None
try:
    API_KEY = st.secrets.get("DASHSCOPE_API_KEY")
except Exception:
    pass
if not API_KEY:
    import os
    API_KEY = os.environ.get("DASHSCOPE_API_KEY")
if not API_KEY:
    try:
        with open("key.txt", "r", encoding="utf-8") as f:
            API_KEY = f.read().strip()
    except FileNotFoundError:
        st.error("未找到 API Key，请配置 key.txt 或云端 Secrets 中的 DASHSCOPE_API_KEY")
        st.stop()

CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ============ 工具集 ============

def get_customer_info(name):
    customers = {
        "比亚迪": {"等级": "A", "预算": 150, "联系人": "张工", "行业": "制造业", "关心": "数据安全、ERP 集成"},
        "美的": {"等级": "A", "预算": 200, "联系人": "李经理", "行业": "家电", "关心": "AI 客服降本"},
        "拼多多": {"等级": "A", "预算": 200, "联系人": "王总", "行业": "电商", "关心": "用户增长、ROI"},
        "腾讯云": {"等级": "A", "预算": 500, "联系人": "陈总", "行业": "云服务", "关心": "大模型集成"},
        "广汽埃安": {"等级": "B", "预算": 80, "联系人": "刘经理", "行业": "新能源车", "关心": "智能座舱"},
    }
    return customers.get(name, {"错误": f"未找到客户 {name}"})


def evaluate_deal(customer_name, amount):
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
    return {
        "状态": "已创建",
        "客户": customer_name,
        "动作": action_type,
        "截止日期": due_date,
        "创建时间": "2026-09-04",
    }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_info",
            "description": "查询客户档案",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_deal",
            "description": "评估订单可行性",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "amount": {"type": "number"},
                },
                "required": ["customer_name", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_history",
            "description": "查询跟进历史",
            "parameters": {
                "type": "object",
                "properties": {"customer_name": {"type": "string"}},
                "required": ["customer_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_materials",
            "description": "推荐准备资料",
            "parameters": {
                "type": "object",
                "properties": {"customer_name": {"type": "string"}},
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
                    "due_date": {"type": "string"},
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

SYSTEM_PROMPT = """你是一个 B 端销售总监 Agent，正在为销售团队制定客户跟进策略。

**工作循环（ReAct）**：
1. Thought：分析当前情况，决定下一步
2. Action：调用合适的工具获取信息或执行操作
3. Observation：看工具返回的结果
4. 重复以上，直到能给出完整方案

**规则**：
- 必须用工具查询真实数据，不能凭空想象
- 至少调用 5 个工具，覆盖：客户信息 → 评估 → 历史 → 资料 → 任务
- 完成所有步骤后，输出"FINAL_ANSWER: "开头的完整方案

输出每个步骤时，用清晰的中文说明你的思考过程。"""


def run_agent_streamlit(user_goal, max_steps=8, status_container=None, log_container=None):
    """运行 Agent，返回 (steps_history, final_answer)"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"销售目标：{user_goal}\n\n请自主规划完成这个目标的步骤。"},
    ]

    steps_history = []

    for step in range(max_steps):
        if status_container:
            status_container.info(f"🤖 Agent 正在执行第 {step + 1} 步...")

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
            return steps_history, f"❌ API 错误：{result}"

        message = result["choices"][0]["message"]
        messages.append(message)

        if message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                func_name = tool_call["function"]["name"]
                func_args = json.loads(tool_call["function"]["arguments"])

                tool_func = TOOL_FUNCTIONS.get(func_name)
                tool_result = tool_func(**func_args) if tool_func else {"错误": f"未知工具 {func_name}"}

                step_record = {
                    "step": step + 1,
                    "thought": message.get("content", ""),
                    "action": func_name,
                    "args": func_args,
                    "observation": tool_result,
                }
                steps_history.append(step_record)

                # 流式显示
                if log_container:
                    with log_container.container():
                        st.markdown(f"### 第 {step + 1} 步")
                        if step_record["thought"]:
                            st.info(f"🧠 **思考**：{step_record['thought']}")
                        st.code(f"🔧 行动：{func_name}({json.dumps(func_args, ensure_ascii=False)})", language="python")
                        st.json(tool_result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })
        else:
            final_answer = message.get("content", "")
            return steps_history, final_answer

    return steps_history, "⚠️ 达到最大步数限制"


# ============ Streamlit UI ============

st.title("🎯 AI 销售跟进 Agent")
st.caption("Week 7 · Agent 自主规划 · 给一个目标，AI 自主拆解 5+ 步")

# 侧边栏：示例目标
with st.sidebar:
    st.header("📚 示例目标")
    examples = [
        "30 天内推动比亚迪签约 50 万 WorkBuddy 企业版订单",
        "本月把拼多多从 B 级提升到 A 级合作",
        "帮美的设计一次完整的 WorkBuddy POC 试点方案",
        "通过宁德时代案例撬动广汽埃安",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex[:10]}"):
            st.session_state.goal_input = ex

    st.divider()
    st.markdown("**核心区别**")
    st.markdown("""
    - ❌ 固定流程：写死 if-else
    - ✅ Agent：AI 自己拆解
    """)

# 主区域
goal = st.text_area(
    "🎯 销售目标",
    value=st.session_state.get("goal_input", "30 天内推动比亚迪签约 50 万 WorkBuddy 企业版订单"),
    height=80,
    placeholder="描述你想达成的销售目标，AI 会自主规划跟进步骤",
)

col1, col2 = st.columns([1, 5])
with col1:
    run_btn = st.button("🚀 启动 Agent", type="primary")
with col2:
    st.caption("AI 会自主调用 5+ 个工具，直到给出完整方案")

if run_btn and goal:
    st.divider()
    st.subheader("🤖 Agent 执行过程")

    status = st.empty()
    log = st.container()

    steps, final = run_agent_streamlit(goal, max_steps=8, status_container=status, log_container=log)

    status.success(f"✅ Agent 完成，共执行 {len(steps)} 步")

    if final:
        st.divider()
        st.subheader("📋 最终方案")
        st.markdown(final)

        # 下载按钮
        report = f"""# AI 销售跟进 Agent 方案

## 目标
{goal}

## 执行步骤
"""
        for s in steps:
            report += f"\n### 第 {s['step']} 步\n"
            if s.get("thought"):
                report += f"**思考**：{s['thought']}\n\n"
            report += f"**行动**：`{s['action']}({json.dumps(s['args'], ensure_ascii=False)})`\n\n"
            report += f"**观察**：{json.dumps(s['observation'], ensure_ascii=False, indent=2)}\n\n"

        report += f"\n## 最终方案\n\n{final}\n"

        st.download_button(
            "📥 下载完整方案（Markdown）",
            data=report,
            file_name=f"销售跟进方案_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
        )

st.divider()
st.caption("💡 部署在阿里云服务器 · Week 7 Day 1 · Agent 自主规划")