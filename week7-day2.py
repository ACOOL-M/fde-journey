"""
Week 7 Day 2: AI Agent + RAG 增强（教学演示）

升级点：
- Day 1: Agent 有 5 个工具（客户/评估/历史/资料/任务）
- Day 2: 加第 6 个工具 search_workbuddy_kb，让 Agent 能查产品文档

关键设计：
1. 启动时把 workbuddy_kb.txt 全部转成 embedding（一次 API 调用，缓存到内存）
2. 客户问产品细节（功能/对比/部署/安全/适用场景等）时，Agent 自动调用 KB 检索
3. Agent 自己决定调用顺序和次数，不需要人写流程

演示场景：
A. 30 天推动比亚迪签 50 万（销售为主，KB 少量介入）
B. 客户比较 WorkBuddy 和飞书（产品为主，KB 必然介入）
C. 比亚迪关心数据安全和 ERP 集成（混合场景，看 Agent 自己调度）
"""

import requests
import json
import os


# ============ API 配置（三源自适应）============

def load_api_key():
    """优先从环境变量/secrets 取，本地回退 key.txt"""
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
EMBED_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


# ============ Embedding 工具 ============

def get_embeddings_batch(texts):
    """批量把多段文字转成向量（一次 API 调用）"""
    payload = {
        "model": "text-embedding-v3",
        "input": texts,
        "dimensions": 256
    }
    resp = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    data = sorted(resp.json()["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in data]


def cosine_similarity(vec_a, vec_b):
    """余弦相似度：-1 到 1，越接近 1 表示意思越接近"""
    dot = sum(x * y for x, y in zip(vec_a, vec_b))
    norm_a = sum(x * x for x in vec_a) ** 0.5
    norm_b = sum(x * x for x in vec_b) ** 0.5
    return dot / (norm_a * norm_b + 1e-9)


# ============ 知识库加载 + 启动时向量化 ============

def load_chunks(filepath):
    """按空行切分知识库文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return [c.strip() for c in content.split("\n\n") if c.strip()]


# 启动时一次：把整个 KB 转成向量
print("⏳ 启动：把产品知识库转成向量...")
CHUNKS = load_chunks("workbuddy_kb.txt")
CHUNK_VECS = get_embeddings_batch(CHUNKS)
print(f"✅ 完成！{len(CHUNKS)} 段资料，每段现在是 {len(CHUNK_VECS[0])} 维向量\n")


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
            {"相似度": round(sim, 3), "内容": chunk[:120] + ("..." if len(chunk) > 120 else "")}
            for sim, _, chunk in top
        ]
    }


# ============ 销售工具集（沿用 Day 1）============

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
    """推荐准备资料（销售物料）"""
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


# ============ 工具 Schema ============

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


# ============ ReAct Agent 主循环 ============

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

        if message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                func_name = tool_call["function"]["name"]
                func_args = json.loads(tool_call["function"]["arguments"])

                if verbose:
                    print(f"🧠 思考：{message.get('content', '(继续)')}")
                    print(f"🔧 行动：{func_name}({json.dumps(func_args, ensure_ascii=False)})")

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
    print("🎯 AI Agent + RAG 增强演示（Week 7 Day 2）")
    print("=" * 60)
    print()
    print("对比 Day 1:")
    print("  Day 1：5 个工具（销售相关）")
    print("  Day 2：6 个工具，新增 search_workbuddy_kb（产品知识库）")
    print()
    print("效果：客户问产品细节时，Agent 自动调 KB 检索真实资料")
    print()

    # 演示场景（默认场景 3：混合场景，最考验 Agent 自主判断）
    scenarios = {
        "1": "30 天内推动比亚迪签约 50 万 WorkBuddy 企业版订单（销售为主）",
        "2": "客户在比较 WorkBuddy 和飞书，帮我准备差异化卖点话术（产品为主）",
        "3": "比亚迪关心数据安全和 ERP 集成，请基于 WorkBuddy 产品文档准备针对性方案（混合场景）",
    }

    print("可选演示场景：")
    for k, v in scenarios.items():
        print(f"  {k}. {v}")
    print()
    print("💡 默认跑场景 3（最能体现 KB 介入）")
    print("   想换场景：python week7-day2.py 后手动改下面的 choice 变量")
    print()

    # 默认场景：混合场景，看 Agent 是否自主调度 6 个工具
    choice = "3"
    goal = scenarios[choice]

    print(f"📋 演示场景：{goal}")
    print()

    run_agent(goal, max_steps=10)

    print("\n" + "=" * 60)
    print("🎓 关键学习")
    print("=" * 60)
    print("""
1. Agent + RAG = 自主决策 + 真实知识
2. 工具描述（description）是关键：告诉 AI "何时该调这个工具"
3. Agent 自动决定调几次、调顺序、调哪个
4. 客户问产品细节 → Agent 必须调 KB，否则就是编
5. 这就是"专家 Agent"：不会编，所有回答都有据可查

对比普通 LLM：
  - 普通 LLM：客户问"WorkBuddy 数据安全吗" → 可能编"我们用 256 位加密"
  - 我们的 Agent：客户问同样问题 → 自动调 KB → 拿到"等保三级/国密算法/审计日志"真实答案
""")