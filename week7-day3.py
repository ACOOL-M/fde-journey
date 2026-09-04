"""
Week 7 Day 3: AI Agent + 事实校验（解决 AI 幻觉）

Day 2 发现的问题：
- KB 检索是对的（4 段全部命中）
- 但最终方案里数字错了（150万 → 300万，8月25日 → 4月15日）
- 原因：AI 拿到 Observation 后"自由发挥"时产生幻觉

Day 3 解法：
1. 新增工具 verify_observation：模糊匹配 Observation 里的数字
2. 修改 system prompt：强制 Agent 在输出方案前调 verify_observation 自检
3. 输出格式：FINAL_ANSWER 之前必须有 ## Self-Check 段

实战价值：
- 企业级 Agent 必须有"事实校验"，否则就是定时炸弹
- 这就是为什么大厂都用"两阶段 Agent"：执行 + 校验
"""

import requests
import json
import os
import re
import time


# ============ API 配置（三源自适应）============

def load_api_key():
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
        raise RuntimeError("未找到 API Key")


API_KEY = load_api_key()
CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
EMBED_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


# ============ Embedding 工具 ============
def get_embeddings_batch(texts):
    payload = {"model": "text-embedding-v3", "input": texts, "dimensions": 256}
    resp = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    data = sorted(resp.json()["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in data]


def cosine_similarity(vec_a, vec_b):
    dot = sum(x * y for x, y in zip(vec_a, vec_b))
    norm_a = sum(x * x for x in vec_a) ** 0.5
    norm_b = sum(x * x for x in vec_b) ** 0.5
    return dot / (norm_a * norm_b + 1e-9)


# ============ 知识库 ============
def load_chunks(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return [c.strip() for c in content.split("\n\n") if c.strip()]


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


# ============ 【Day 3 新增】事实校验工具 ============

def verify_observation(field_name, claimed_value, observation_summary):
    """
    校验数字/事实是否与 Observation 一致。
    提取 Observation 和 claimed_value 里的数字，逐项核对。
    """
    # 提取 Observation 里的所有数字（包括小数）
    obs_numbers = re.findall(r'\d+\.?\d*', str(observation_summary))
    # 提取 claimed_value 里的所有数字
    claim_numbers = re.findall(r'\d+\.?\d*', str(claimed_value))

    # 字符串包含检测（处理 "150 万" vs "150万元" 这类轻微差异）
    simple_match = (
        str(claimed_value).replace(" ", "") in str(observation_summary).replace(" ", "")
        or str(claimed_value) in str(observation_summary)
    )

    # 数字匹配
    matched_nums = [n for n in claim_numbers if n in obs_numbers]
    unmatched_nums = [n for n in claim_numbers if n not in obs_numbers]

    if simple_match or not unmatched_nums:
        verdict = "✅ 一致"
        suggestion = "可保留声称值"
    else:
        verdict = "❌ 不一致"
        suggestion = f"必须改用 Observation 真实值（不匹配的数字：{unmatched_nums}）"

    return {
        "字段名": field_name,
        "声称值": claimed_value,
        "声称中包含的数字": claim_numbers,
        "Observation 中存在的数字": list(set(obs_numbers))[:20],  # 限 20 个防爆
        "匹配的数字": matched_nums,
        "未匹配的数字": unmatched_nums,
        "结论": verdict,
        "建议": suggestion,
    }


# ============ 销售工具集（沿用 Day 2）============

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


# ============ 工具 Schema（7 个，新增 verify_observation）============

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
            "description": "【必用】检索 WorkBuddy 产品知识库。客户问产品功能/技术细节/对比/部署方式/数据安全/适用场景/价格等任何产品相关问题时，必须调用此工具，禁止凭空编造。",
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
    {
        "type": "function",
        "function": {
            "name": "verify_observation",
            "description": "【Day 3 新增·必用】事实校验工具。校验方案中的数字/日期/事实是否与工具 Observation 一致。在准备 FINAL_ANSWER 之前，必须对方案中每个关键数字（预算、日期、概率、金额等）调用一次。",
            "parameters": {
                "type": "object",
                "properties": {
                    "field_name": {"type": "string", "description": "字段名（如：客户预算、最近沟通日期、成交概率）"},
                    "claimed_value": {"type": "string", "description": "方案中声称的值"},
                    "observation_summary": {"type": "string", "description": "对应的 Observation 原文摘要（从历史消息中复制）"},
                },
                "required": ["field_name", "claimed_value", "observation_summary"],
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
    "verify_observation": verify_observation,
}


# ============ 【Day 3 关键】两阶段 System Prompt ============

SYSTEM_PROMPT = """你是一个 B 端销售总监 Agent + 事实校验机制。

**两阶段工作流程**：

## 阶段一：执行（ReAct 循环）
1. Thought：分析当前情况，决定下一步
2. Action：调用工具获取信息（必须用工具，不能凭空想）
3. Observation：看工具返回结果
4. 重复直到能写出方案

## 阶段二：事实校验（Day 3 新增·强制）
在输出 FINAL_ANSWER 之前，必须对方案中每个关键数字调用 verify_observation 工具校验：

**校验清单（至少校验以下字段）**：
- 客户预算（必须来自 get_customer_info）
- 目标金额（必须来自 evaluate_deal）
- 成交概率（必须来自 evaluate_deal）
- 最近沟通日期（必须来自 search_history）
- 产品技术细节（必须来自 search_workbuddy_kb）

**校验步骤**：
1. 列出方案中的所有关键数字
2. 对每个数字调用 verify_observation(field_name, claimed_value, observation_summary)
3. 如果结论是"❌ 不一致"，必须改用 Observation 的真实值重写方案
4. 所有校验通过后，才输出 "FINAL_ANSWER: " 开头的最终方案

**输出格式要求**：
- 阶段一：按 ReAct 循环调工具
- 阶段二：输出"## Self-Check"段落，列出每个 verify_observation 的结果
- 最终：以"FINAL_ANSWER: "开头输出完整方案

**绝对规则**：
- 数字必须 100% 来自 Observation，禁止幻觉
- 不允许修改 Observation 中的数字
- 客户问产品细节时必须调 search_workbuddy_kb
"""


def run_agent(user_goal, max_steps=15, verbose=True):
    """运行两阶段 Agent（执行 + 事实校验）"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"销售目标：{user_goal}\n\n请自主规划完成这个目标的步骤，并按两阶段流程输出（执行 + 事实校验 + 最终方案）。"},
    ]
    executed_tools = []  # 已调用的工具列表（用于硬约束）

    for step in range(max_steps):
        if verbose:
            print(f"\n{'=' * 60}")
            print(f"🤖 Agent 第 {step + 1} 步")
            print("=" * 60)

        # 调用 LLM（带重试 + 长超时，应对 DashScope 临时网络抖动）
        response = None
        last_err = None
        for attempt in range(3):
            try:
                response = requests.post(
                    CHAT_URL, headers=HEADERS,
                    json={
                        "model": "qwen-plus",
                        "messages": messages,
                        "tools": TOOLS,
                        "temperature": 0.3,
                    },
                    timeout=(10, 90),  # 连接10秒 + 读取90秒
                )
                break  # 成功就跳出
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                last_err = e
                if verbose and attempt < 2:
                    print(f"⚠️ 第 {attempt + 1} 次调用超时/断连，2秒后重试... ({type(e).__name__})")
                time.sleep(2)
            except Exception as e:
                last_err = e
                if verbose:
                    print(f"❌ 非可重试错误：{e}")
                break

        if response is None:
            if verbose:
                print(f"❌ 3 次重试全部失败：{last_err}")
                print(f"   建议：检查网络/DashScope 配额，或把 timeout 调到 120")
            return None

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
                executed_tools.append(func_name)

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
            # Agent 没调工具直接输出 —— 区分"刚开始"和"已调够工具"
            required = {"get_customer_info", "search_history", "evaluate_deal", "recommend_materials"}
            missing = required - set(executed_tools)

            if step == 0:
                if verbose:
                    print("⚠️ Agent 第 1 步就没调工具！强制让它重做...")
                messages.append({
                    "role": "user",
                    "content": "⚠️ 你还没有调用任何工具就直接输出了方案。请立即调用 get_customer_info 获取客户档案（先识别客户名称），然后再继续。禁止在没调工具前直接给方案！",
                })
                continue
            elif missing:
                if verbose:
                    print(f"⚠️ Agent 还没调完必用工具！还差：{', '.join(sorted(missing))}")
                messages.append({
                    "role": "user",
                    "content": f"⚠️ 你还没调完必用的工具（还差：{', '.join(sorted(missing))}）。请先调这些工具再输出方案！",
                })
                continue
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
    print("🎯 AI Agent + 事实校验演示（Week 7 Day 3）")
    print("=" * 60)
    print()
    print("对比 Day 2：")
    print("  Day 2：6 个工具，最终方案有幻觉（150万→300万，8月25日→4月15日）")
    print("  Day 3：7 个工具，新增 verify_observation，强制 Agent 自检数字")
    print()
    print("效果：方案中每个关键数字都标注来源 + 校验通过")
    print()

    # 演示场景（沿用 Day 2 的混合场景，便于对比）
    goal = "比亚迪关心数据安全和 ERP 集成，请基于 WorkBuddy 产品文档准备针对性方案"
    print(f"📋 演示场景：{goal}")
    print()

    run_agent(goal, max_steps=15)

    print("\n" + "=" * 60)
    print("🎓 关键学习")
    print("=" * 60)
    print("""
1. KB 检索正确 ≠ 最终输出正确（Day 2 的教训）
2. AI 在"自由发挥"阶段最容易幻觉
3. 事实校验是企业级 Agent 的必修课
4. 两阶段架构：执行 + 校验 → 输出才可信

对比：
  - 普通 Agent：调工具 → 输出方案（可能编）
  - 企业级 Agent：调工具 → 自检 → 输出方案（数字有源可查）

实战价值：
  - B 端销售方案发给客户前，先过一遍事实校验
  - 监管/医疗/金融场景必备（不能容忍任何数字错误）
""")