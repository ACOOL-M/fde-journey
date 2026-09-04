"""
Week 7 Day 2: AI Agent + RAG 增强 网页版

升级点：
- Day 1 网页版：5 个工具 + 流式思考
- Day 2 网页版：6 个工具 + KB 检索结果相似度可视化（颜色编码）

关键能力：
1. KB 在启动时一次性向量化（@st.cache_resource 缓存，避免每次重复算）
3. Agent 调 search_workbuddy_kb 时，相似度可视化（🟢🟡🔴 + 字符条）
2. 每个工具被调用次数统计
"""

import requests
import json
import os
import streamlit as st
from datetime import datetime

# ============ 页面配置 ============
st.set_page_config(
    page_title="AI Agent + RAG 销售助手",
    page_icon="🧠",
    layout="wide",
)

# ============ API Key 加载（三源自适应）============
API_KEY = None
try:
    API_KEY = st.secrets.get("DASHSCOPE_API_KEY")
except Exception:
    pass
if not API_KEY:
    API_KEY = os.environ.get("DASHSCOPE_API_KEY")
if not API_KEY:
    try:
        with open("key.txt", "r", encoding="utf-8") as f:
            API_KEY = f.read().strip()
    except FileNotFoundError:
        st.error("未找到 API Key，请配置 key.txt 或云端 Secrets 中的 DASHSCOPE_API_KEY")
        st.stop()

CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
EMBED_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


# ============ Embedding 工具 ============
def get_embeddings_batch(texts):
    """批量向量化"""
    payload = {"model": "text-embedding-v3", "input": texts, "dimensions": 256}
    resp = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    data = sorted(resp.json()["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in data]


def cosine_similarity(vec_a, vec_b):
    """余弦相似度"""
    dot = sum(x * y for x, y in zip(vec_a, vec_b))
    norm_a = sum(x * x for x in vec_a) ** 0.5
    norm_b = sum(x * x for x in vec_b) ** 0.5
    return dot / (norm_a * norm_b + 1e-9)


# ============ 知识库加载 + 向量化（缓存）============
@st.cache_resource(show_spinner="⏳ 正在把产品知识库转成向量（首次加载约 5 秒）...")
def load_and_embed_kb(filepath):
    """加载 KB 并向量化，仅启动时执行一次"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
    vecs = get_embeddings_batch(chunks)
    return chunks, vecs


try:
    CHUNKS, CHUNK_VECS = load_and_embed_kb("workbuddy_kb.txt")
except FileNotFoundError:
    st.error("未找到 workbuddy_kb.txt，请确保该文件在当前目录")
    st.stop()


def search_workbuddy_kb(query, top_k=2):
    """语义检索 WorkBuddy 产品知识库"""
    query_vec = get_embeddings_batch([query])[0]
    scored = []
    for idx, chunk in enumerate(CHUNKS):
        sim = cosine_similarity(query_vec, CHUNK_VECS[idx])
        scored.append((sim, idx, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    return {
        "query": query,
        "命中数": len(top),
        "片段": [
            {"相似度": round(sim, 3), "内容": chunk}
            for sim, _, chunk in top
        ]
    }


# ============ 销售工具集（沿用 Day 1）============
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


# ============ 工具 Schema（6 个）============
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_info",
            "description": "查询客户档案（等级、预算、联系人、行业、关心点）",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "客户名称"}},
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
                "properties": {"customer_name": {"type": "string"}},
                "required": ["customer_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_materials",
            "description": "根据客户行业推荐准备资料（销售物料）",
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
                    "due_date": {"type": "string", "description": "截止日期 YYYY-MM-DD"},
                },
                "required": ["customer_name", "action_type", "due_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_workbuddy_kb",
            "description": "【新增·必用】检索 WorkBuddy 产品知识库。客户问产品功能/技术细节/对比/部署方式/数据安全/适用场景/价格等任何产品相关问题时，必须调用此工具，禁止凭空编造。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要查的产品问题关键词"},
                    "top_k": {"type": "integer", "description": "返回几条最相关结果，默认 2"},
                },
                "required": ["query"],
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
    "search_workbuddy_kb": search_workbuddy_kb,
}

SYSTEM_PROMPT = """你是一个 B 端销售总监 Agent，正在为销售团队制定客户跟进策略。

**工作循环（ReAct）**：
1. Thought：分析当前情况，决定下一步
2. Action：调用合适的工具获取信息或执行操作
3. Observation：看工具返回的结果
4. 重复以上，直到能给出完整方案

**规则**：
- 必须用工具查询真实数据，不能凭空想象
- 客户关心 WorkBuddy 产品细节（功能/对比/部署/安全/适用场景/价格/集成等）时，必须调用 search_workbuddy_kb 检索真实资料，绝不允许编造
- 至少调用 5 个工具
- 完成所有步骤后，输出"FINAL_ANSWER: "开头的完整方案

输出每个步骤时，用清晰的中文说明你的思考过程。"""


# ============ 特殊渲染：KB 检索结果（相似度可视化）============
def render_kb_result(observation):
    """KB 检索结果特殊渲染：颜色编码 + 字符进度条"""
    if not isinstance(observation, dict) or "片段" not in observation:
        st.json(observation)
        return

    st.markdown(f"**🔍 查询关键词**：`{observation.get('query', '')}`")

    for i, hit in enumerate(observation["片段"], 1):
        sim = hit["相似度"]
        # 字符进度条
        filled = int(sim * 20)
        bar = "█" * filled + "░" * (20 - filled)
        # 颜色编码
        if sim >= 0.75:
            color = "🟢"
            label = "高命中"
        elif sim >= 0.6:
            color = "🟡"
            label = "中命中"
        else:
            color = "🔴"
            label = "低命中"

        st.markdown(f"{color} **{label} {sim:.3f}**  `{bar}`")
        st.caption(hit["内容"])

        if i < len(observation["片段"]):
            st.divider()


# ============ Agent 主循环 ============
def run_agent_streamlit(user_goal, max_steps=10, status_container=None, log_container=None):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"销售目标：{user_goal}\n\n请自主规划完成这个目标的步骤。"},
    ]

    steps_history = []

    for step in range(max_steps):
        if status_container:
            status_container.info(f"🤖 Agent 正在执行第 {step + 1} 步...")

        response = requests.post(
            CHAT_URL, headers=HEADERS,
            json={"model": "qwen-plus", "messages": messages, "tools": TOOLS, "temperature": 0.3},
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
                        # KB 检索特殊渲染
                        if func_name == "search_workbuddy_kb":
                            render_kb_result(tool_result)
                        else:
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
st.title("🧠 AI Agent + RAG 销售助手")
st.caption("Week 7 Day 2 · 自主规划 + 产品知识库 · 6 个工具协同")

# 侧边栏：示例 + 工具清单
with st.sidebar:
    st.header("📚 示例目标")
    examples = [
        "30 天内推动比亚迪签约 50 万 WorkBuddy 企业版订单",
        "客户在比较 WorkBuddy 和飞书，帮我准备差异化卖点话术",
        "比亚迪关心数据安全和 ERP 集成，请基于 WorkBuddy 产品文档准备针对性方案",
        "腾讯云想买大模型 API 集成方案，预算 500 万，准备一个 30 天推进计划",
        "美的想做 AI 客服降本，准备 POC 试点方案并报价",
    ]
    for i, ex in enumerate(examples):
        display = ex[:30] + "..." if len(ex) > 30 else ex
        if st.button(display, key=f"ex_{i}"):
            st.session_state.goal_input = ex

    st.divider()
    st.markdown("**🆕 Day 2 新增能力**")
    st.markdown("""
    - 🔍 `search_workbuddy_kb` 工具
    - 自动查产品功能/对比/部署细节
    - 相似度可视化（🟢🟡🔴 颜色编码）
    - 禁止 AI 编造产品细节
    """)

    st.divider()
    st.markdown("**🔧 工具清单（6 个）**")
    for name in ["get_customer_info", "evaluate_deal", "search_history", "recommend_materials", "create_followup_task", "search_workbuddy_kb"]:
        st.markdown(f"- `{name}`")

# 主区域
goal = st.text_area(
    "🎯 销售目标",
    value=st.session_state.get("goal_input", "比亚迪关心数据安全和 ERP 集成，请基于 WorkBuddy 产品文档准备针对性方案"),
    height=80,
    placeholder="描述你的销售目标，Agent 会自主调度 6 个工具（含 KB 检索）",
)

col1, col2 = st.columns([1, 5])
with col1:
    run_btn = st.button("🚀 启动 Agent", type="primary")
with col2:
    st.caption("Agent 自主规划，会按需调用 KB 检索产品细节")

if run_btn and goal:
    st.divider()
    st.subheader("🤖 Agent 执行过程")

    status = st.empty()
    log = st.container()

    steps, final = run_agent_streamlit(goal, max_steps=10, status_container=status, log_container=log)

    status.success(f"✅ Agent 完成，共执行 {len(steps)} 步")

    if final:
        st.divider()
        st.subheader("📋 最终方案")
        st.markdown(final)

        # 工具调用统计
        st.divider()
        st.markdown("**📊 工具调用统计**")
        tool_counts = {}
        for s in steps:
            tool_counts[s["action"]] = tool_counts.get(s["action"], 0) + 1

        if tool_counts:
            cols = st.columns(len(tool_counts))
            for col, (name, count) in zip(cols, tool_counts.items()):
                # KB 工具高亮显示
                if name == "search_workbuddy_kb":
                    col.metric(f"🔍 {name}", f"{count} 次", delta="Day 2 新增", delta_color="off")
                else:
                    col.metric(name, f"{count} 次")

        # 下载报告
        report = f"""# AI 销售跟进 Agent 方案（Day 2 · Agent + RAG）

## 目标
{goal}

## 执行步骤（共 {len(steps)} 步）
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
            file_name=f"销售跟进方案_Day2_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
        )

st.divider()
st.caption("💡 Week 7 Day 2 · Agent 自主规划 + RAG 知识库增强 · 6 个工具协同")