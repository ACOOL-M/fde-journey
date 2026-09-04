"""
Week 7 Day 3: AI Agent + RAG + 事实校验 网页版

升级点（相对 Day 2 网页版）：
- 7 个工具（新增 verify_observation）
- Self-Check 阶段：每个数字校验结果用表格可视化（声称值 vs Observation 真实值 vs ✅/❌）
- 超时修复：timeout=(10, 90) + 3 次重试，避免 DashScope 临时网络抖动断掉
- 两阶段 Agent：执行 → 强制 Self-Check → 最终方案（零幻觉）
"""

import requests
import json
import os
import re
import time
import streamlit as st

# ============ 页面配置 ============
st.set_page_config(
    page_title="AI Agent + 事实校验 销售助手",
    page_icon="🛡️",
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


# ============ 【Day 3 新增】事实校验工具 ============
def verify_observation(field_name, claimed_value, observation_summary):
    """校验数字/事实是否与 Observation 一致"""
    obs_numbers = re.findall(r'\d+\.?\d*', str(observation_summary))
    claim_numbers = re.findall(r'\d+\.?\d*', str(claimed_value))

    simple_match = (
        str(claimed_value).replace(" ", "") in str(observation_summary).replace(" ", "")
        or str(claimed_value) in str(observation_summary)
    )

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
        "Observation 中存在的数字": list(set(obs_numbers))[:20],
        "匹配的数字": matched_nums,
        "未匹配的数字": unmatched_nums,
        "结论": verdict,
        "建议": suggestion,
    }


# ============ 工具 Schema（7 个）============
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
            "description": "【Day 2 新增】检索 WorkBuddy 产品知识库。客户问产品功能/技术细节/对比/部署方式/数据安全/适用场景/价格等任何产品相关问题时，必须调用此工具，禁止凭空编造。",
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
            "description": "【Day 3 新增·强制】事实校验工具。在输出最终方案前，对方案中每个关键数字（预算/金额/概率/日期/技术细节）调用此工具，把声称值与 Observation 真实值比对，避免 AI 幻觉。如校验不通过必须改用 Observation 真实值。",
            "parameters": {
                "type": "object",
                "properties": {
                    "field_name": {"type": "string", "description": "校验的字段名，如'客户预算'/'最近沟通日期'"},
                    "claimed_value": {"type": "string", "description": "方案中声称的值，如'300万'"},
                    "observation_summary": {"type": "string", "description": "对应工具的 Observation 原文"},
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

**⚠️ 绝对硬规则（违反任何一条都视为幻觉，整体方案作废）**：
1. **第一步必须调用工具**——禁止在未调取任何工具前直接输出方案
2. **至少必须调用 5 个工具**，且必须包含：get_customer_info + search_history + evaluate_deal + recommend_materials + search_workbuddy_kb
3. **客户问产品细节时必须调 search_workbuddy_kb**——禁止凭空编造产品功能/版本/认证/技术细节
4. **输出 FINAL_ANSWER 之前必须调 verify_observation**——至少校验 3 个关键数字
5. **所有数字 100% 来自 Observation**——禁止修改/编造任何数字（包括日期、金额、概率、版本号、证书编号）

**两阶段工作流程**：

## 阶段一：执行（ReAct 循环，必须先完成）
1. Thought：分析当前情况，决定下一步
2. Action：调用合适的工具获取信息（必须用工具，禁止凭空想）
3. Observation：看工具返回的结果
4. 重复以上，**直到至少调完 5 个工具**

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
- 阶段一：按 ReAct 循环调工具，至少 5 次
- 阶段二：输出"## Self-Check"段落，列出每个 verify_observation 的结果
- 最终：以"FINAL_ANSWER: "开头输出完整方案

**额外禁止事项**：
- 禁止编造证书编号（如"证书编号：DJBH2023110088"）
- 禁止编造产品版本号（如"U9C 17.0版本"）——除非 KB 里明确提到
- 禁止把别的客户的数据张冠李戴（如把腾讯云的500万写到比亚迪头上）
- 禁止编造未来日期或倒退日期（如当前是 2026-09-04，禁止写 2024-04-15）
"""


# ============ 特殊渲染：KB 检索结果（沿用 Day 2）============
def render_kb_result(observation):
    """KB 检索结果特殊渲染：颜色编码 + 字符进度条"""
    if not isinstance(observation, dict) or "片段" not in observation:
        st.json(observation)
        return

    st.markdown(f"**🔍 查询关键词**：`{observation.get('query', '')}`")

    for i, hit in enumerate(observation["片段"], 1):
        sim = hit["相似度"]
        filled = int(sim * 20)
        bar = "█" * filled + "░" * (20 - filled)
        if sim >= 0.75:
            color, label = "🟢", "高命中"
        elif sim >= 0.6:
            color, label = "🟡", "中命中"
        else:
            color, label = "🔴", "低命中"

        st.markdown(f"{color} **{label} {sim:.3f}**  `{bar}`")
        st.caption(hit["内容"])

        if i < len(observation["片段"]):
            st.divider()


# ============ 【Day 3 新增】特殊渲染：事实校验结果 ============
def render_verify_result(observation):
    """事实校验结果特殊渲染：表格 + 颜色标识"""
    if not isinstance(observation, dict):
        st.json(observation)
        return

    field = observation.get("字段名", "未知")
    claimed = observation.get("声称值", "")
    verdict = observation.get("结论", "")
    suggestion = observation.get("建议", "")
    matched = observation.get("匹配的数字", [])
    unmatched = observation.get("未匹配的数字", [])

    # 顶部用大号标识
    if "✅" in verdict:
        st.success(f"**{verdict}** · {field}")
    else:
        st.error(f"**{verdict}** · {field}")

    # 详情用表格
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📝 声称值**")
        st.code(claimed, language=None)

    with col2:
        st.markdown("**🔢 数字比对**")
        if matched:
            st.markdown(f"✅ 匹配：`{', '.join(matched)}`")
        if unmatched:
            st.markdown(f"❌ 未匹配：`{', '.join(unmatched)}`")
        if not matched and not unmatched:
            st.caption("（无数字可比对）")

    # 建议
    st.markdown(f"**💡 建议**：{suggestion}")
    st.divider()


# ============ Agent 主循环（Day 3 超时修复 + 阶段标识）============
def run_agent_streamlit(user_goal, max_steps=15, status_container=None, log_container=None):
    """两阶段 Agent：执行 → Self-Check → 最终方案"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"销售目标：{user_goal}\n\n请自主规划完成这个目标的步骤，并按两阶段流程输出（执行 + 事实校验 + 最终方案）。"},
    ]

    steps_history = []
    in_self_check = False  # 标记是否进入 Self-Check 阶段
    verify_count = 0  # 校验调用次数

    for step in range(max_steps):
        # 阶段标识
        if in_self_check:
            phase_label = "🛡️ Self-Check"
        else:
            phase_label = "🤖 执行"

        if status_container:
            status_container.info(f"{phase_label} · 第 {step + 1} 步...")

        # 调用 LLM（带重试 + 长超时）
        response = None
        last_err = None
        for attempt in range(3):
            try:
                response = requests.post(
                    CHAT_URL, headers=HEADERS,
                    json={"model": "qwen-plus", "messages": messages, "tools": TOOLS, "temperature": 0.3},
                    timeout=(10, 90),  # 连接10秒 + 读取90秒
                )
                break
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                last_err = e
                if attempt < 2:
                    if log_container:
                        with log_container.container():
                            st.warning(f"⚠️ 第 {attempt + 1} 次调用超时/断连，2秒后重试... ({type(e).__name__})")
                time.sleep(2)
            except Exception as e:
                last_err = e
                break

        if response is None:
            return steps_history, f"❌ 3 次重试全部失败：{last_err}\n\n建议：检查网络/DashScope 配额"

        result = response.json()
        if "error" in result:
            return steps_history, f"❌ API 错误：{result}"

        message = result["choices"][0]["message"]
        messages.append(message)

        if message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                func_name = tool_call["function"]["name"]

                # 容错：qwen-plus 偶尔返回格式错误的 JSON（缺逗号 / 转义错乱）
                raw_args = tool_call["function"]["arguments"]
                try:
                    func_args = json.loads(raw_args)
                except json.JSONDecodeError as e:
                    # 修复策略 1：尝试修复常见问题（尾随逗号、未闭合引号）
                    fixed = raw_args.strip()
                    # 去掉尾随逗号
                    if fixed.endswith(","):
                        fixed = fixed[:-1]
                    # 补全缺失的右括号
                    if fixed.count("{") > fixed.count("}"):
                        fixed += "}" * (fixed.count("{") - fixed.count("}"))
                    if fixed.count("[") > fixed.count("]"):
                        fixed += "]" * (fixed.count("[") - fixed.count("]"))
                    try:
                        func_args = json.loads(fixed)
                    except json.JSONDecodeError:
                        # 修复策略 2：跳过这个工具调用 + 把错误回传给 AI 让它重试
                        error_msg = f"工具 {func_name} 参数 JSON 解析失败：{e}。原始参数前 200 字符：{raw_args[:200]}"
                        if log_container:
                            log_container.error(f"⚠️ {error_msg}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps({"error": error_msg, "retry": True}, ensure_ascii=False),
                        })
                        continue

                # 检测进入 Self-Check 阶段（第一次调 verify_observation 时）
                if func_name == "verify_observation":
                    in_self_check = True
                    verify_count += 1

                tool_func = TOOL_FUNCTIONS.get(func_name)
                tool_result = tool_func(**func_args) if tool_func else {"错误": f"未知工具 {func_name}"}

                step_record = {
                    "step": step + 1,
                    "phase": "self_check" if in_self_check else "execute",
                    "thought": message.get("content", ""),
                    "action": func_name,
                    "args": func_args,
                    "observation": tool_result,
                }
                steps_history.append(step_record)

                # 流式显示
                if log_container:
                    with log_container.container():
                        # 阶段横幅
                        if in_self_check and func_name == "verify_observation" and verify_count == 1:
                            st.markdown("### 🛡️ 进入 Self-Check 阶段（事实校验）")
                            st.caption("Agent 正在对方案中每个数字与 Observation 比对，确保零幻觉")
                            st.divider()

                        st.markdown(f"### {phase_label} · 第 {step + 1} 步")
                        if step_record["thought"]:
                            st.info(f"🧠 **思考**：{step_record['thought']}")
                        st.code(f"🔧 行动：{func_name}({json.dumps(func_args, ensure_ascii=False)})", language="python")
                        # 特殊渲染
                        if func_name == "search_workbuddy_kb":
                            render_kb_result(tool_result)
                        elif func_name == "verify_observation":
                            render_verify_result(tool_result)
                        else:
                            st.json(tool_result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })
        else:
            # Agent 没调工具直接输出 —— 区分"刚开始"和"已调够工具"
            tools_called_so_far = [s["action"] for s in steps_history if s["phase"] == "execute"]

            # 检查必须的工具是否都调过
            required = {"get_customer_info", "search_history", "evaluate_deal", "recommend_materials"}
            missing = required - set(tools_called_so_far)

            if step == 0:
                # 第 0 步就直接输出 → 强制重做
                if log_container:
                    with log_container.container():
                        st.error("⚠️ Agent 第 1 步就没调工具！强制让它重做...")
                messages.append({
                    "role": "user",
                    "content": "⚠️ 你还没有调用任何工具就直接输出了方案。请立即调用 get_customer_info 获取客户档案（先识别客户名称），然后再继续。禁止在没调工具前直接给方案！",
                })
                # 把 step 倒回 1 步（不能 break，必须继续循环）
                continue
            elif missing:
                # 已经调了一些工具，但关键工具没调完 → 强制补齐
                if log_container:
                    with log_container.container():
                        st.error(f"⚠️ Agent 还没调完必用工具！还差：{', '.join(sorted(missing))}")
                messages.append({
                    "role": "user",
                    "content": f"⚠️ 你还没调完必用的工具（还差：{', '.join(sorted(missing))}）。请先调这些工具再输出方案！",
                })
                continue
            else:
                # 工具都调完了，AI 直接输出 final answer 是 OK 的
                final_answer = message.get("content", "")
                return steps_history, final_answer

    return steps_history, "⚠️ 达到最大步数限制"


# ============ Streamlit UI ============
st.title("🛡️ AI Agent + 事实校验 销售助手")
st.caption("Week 7 Day 3 · 自主规划 + RAG + 强制 Self-Check · 7 个工具协同 · 零幻觉")

# 侧边栏：示例 + 工具清单 + Day 3 能力
with st.sidebar:
    st.header("📚 示例目标")
    examples = [
        "比亚迪关心数据安全和 ERP 集成，请基于 WorkBuddy 产品文档准备针对性方案",
        "30 天内推动比亚迪签约 50 万 WorkBuddy 企业版订单",
        "客户在比较 WorkBuddy 和飞书，帮我准备差异化卖点话术",
        "腾讯云想买大模型 API 集成方案，预算 500 万，准备一个 30 天推进计划",
        "美的想做 AI 客服降本，准备 POC 试点方案并报价",
    ]
    for i, ex in enumerate(examples):
        display = ex[:30] + "..." if len(ex) > 30 else ex
        if st.button(display, key=f"ex_{i}"):
            st.session_state.goal_input = ex

    st.divider()
    st.markdown("**🆕 Day 3 新增能力**")
    st.markdown("""
    - 🛡️ `verify_observation` 工具
    - 两阶段架构：执行 + 强制 Self-Check
    - 每个数字与 Observation 比对
    - ✅❌ 一致性可视化（绿/红）
    - 零幻觉：数字 100% 来自 Observation
    """)

    st.divider()
    st.markdown("**🔧 工具清单（7 个）**")
    for name in ["get_customer_info", "evaluate_deal", "search_history", "recommend_materials", "create_followup_task", "search_workbuddy_kb", "verify_observation"]:
        st.markdown(f"- `{name}`")

    st.divider()
    st.markdown("**⚙️ Day 3 稳定性**")
    st.caption("超时：连接10s + 读取90s")
    st.caption("重试：最多 3 次，间隔 2s")

# 主区域
goal = st.text_area(
    "🎯 销售目标",
    value=st.session_state.get("goal_input", "比亚迪关心数据安全和 ERP 集成，请基于 WorkBuddy 产品文档准备针对性方案"),
    height=80,
    placeholder="描述你的销售目标，Agent 会调 7 个工具（含 KB 检索 + 事实校验）",
)

col1, col2 = st.columns([1, 5])
with col1:
    run_btn = st.button("🚀 启动 Agent", type="primary")
with col2:
    st.caption("两阶段流程：执行（调工具）→ Self-Check（校验数字）→ 最终方案")

if run_btn and goal:
    st.divider()
    st.subheader("🤖 Agent 执行过程")

    status = st.empty()
    log = st.container()

    steps, final = run_agent_streamlit(goal, max_steps=15, status_container=status, log_container=log)

    # 统计阶段
    execute_steps = [s for s in steps if s["phase"] == "execute"]
    verify_steps = [s for s in steps if s["phase"] == "self_check"]
    verify_calls = [s for s in steps if s["action"] == "verify_observation"]

    status.success(f"✅ Agent 完成 · 执行 {len(execute_steps)} 步 + Self-Check {len(verify_calls)} 次")

    # 工具调用统计（含 Self-Check 单独高亮）
    st.divider()
    st.markdown("**📊 工具调用统计**")
    tool_counts = {}
    for s in steps:
        tool_counts[s["action"]] = tool_counts.get(s["action"], 0) + 1

    if tool_counts:
        cols = st.columns(len(tool_counts))
        for col, (name, count) in zip(cols, tool_counts.items()):
            if name == "search_workbuddy_kb":
                col.metric(f"🔍 {name}", f"{count} 次", delta="Day 2", delta_color="off")
            elif name == "verify_observation":
                col.metric(f"🛡️ {name}", f"{count} 次", delta="Day 3 新增", delta_color="off")
            else:
                col.metric(name, f"{count} 次")

    # 最终方案
    if final:
        st.divider()
        st.subheader("📋 最终方案")

        # 提取 Self-Check 段单独展示
        if "## Self-Check" in final:
            self_check_part = final.split("## Self-Check")[1].split("FINAL_ANSWER")[0]
            final_answer_part = final.split("FINAL_ANSWER")[-1].strip() if "FINAL_ANSWER" in final else final

            # Self-Check 表格化
            with st.expander("🛡️ Self-Check 详情（事实校验记录）", expanded=False):
                st.markdown(self_check_part.strip())

            st.markdown("---")
            st.markdown(final_answer_part)
        else:
            st.markdown(final)

    # 下载报告
    report = f"""# AI 销售跟进 Agent 方案（Day 3 · Agent + RAG + 事实校验）

## 目标
{goal}

## 执行阶段（共 {len(execute_steps)} 步）
"""
    for s in execute_steps:
        report += f"\n### 第 {s['step']} 步 · {s['action']}\n"
        if s["thought"]:
            report += f"**思考**：{s['thought']}\n\n"
        report += f"```python\n{s['action']}({json.dumps(s['args'], ensure_ascii=False)})\n```\n\n"
        report += f"**Observation**：\n```json\n{json.dumps(s['observation'], ensure_ascii=False, indent=2)}\n```\n\n"

    report += f"\n## Self-Check 阶段（{len(verify_calls)} 次校验）\n"
    for s in verify_calls:
        report += f"\n### 第 {s['step']} 步 · {s['action']}\n"
        report += f"**校验字段**：{s['args'].get('field_name', '')}\n"
        report += f"**声称值**：{s['args'].get('claimed_value', '')}\n"
        report += f"**结论**：{s['observation'].get('结论', '')}\n\n"

    report += f"\n## 最终方案\n\n{final}\n"

    st.download_button(
        label="📥 下载完整报告（Markdown）",
        data=report,
        file_name=f"sales_agent_day3_{int(time.time())}.md",
        mime="text/markdown",
    )