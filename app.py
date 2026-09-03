"""
AI 销售助手 · 网页版（部署版）
Week 6 项目升级：支持云端部署

整合全部能力：
  1. 客户速查（侧边栏实时显示）
  2. 算折扣报价（A 级 85 折 / B 级 92 折）
  3. 预约产品演示（存到会话，可查看）
  4. 产品知识问答（RAG + Embedding 语义检索）
  5. 优化销售话术（Prompt Engineering）
  6. 智能方案推荐（LLM + 客户画像）

运行方式：
  本地：python -m streamlit run app.py
  云端：由 Streamlit Cloud / Hugging Face 自动执行
"""

import os
import requests
import json
import streamlit as st
from datetime import datetime

# ============ 页面配置（必须放最前面） ============

st.set_page_config(
    page_title="AI 销售助手 · 网页版",
    page_icon="💼",
    layout="wide"
)

# ============ API Key 配置（云端/本地自适应） ============

def get_api_key():
    """获取 API Key，按优先级：
    1. 云端 Secrets（Streamlit Cloud 设置里配置）
    2. 环境变量 DASHSCOPE_API_KEY
    3. 本地 key.txt（.gitignore 已屏蔽，不会上传）
    """
    # 方式 1：云端 Secrets（st.secrets）
    try:
        return st.secrets["DASHSCOPE_API_KEY"]
    except Exception:
        pass
    # 方式 2：环境变量
    env_key = os.environ.get("DASHSCOPE_API_KEY")
    if env_key:
        return env_key
    # 方式 3：本地 key.txt
    with open("key.txt", "r", encoding="utf-8") as f:
        return f.read().strip()


API_KEY = get_api_key()

EMBED_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ============ 客户数据库 ============

CUSTOMERS = {
    "比亚迪":   {"level": "A", "budget": 150, "contact": "张工",   "industry": "制造业", "note": "关心数据安全和 ERP 对接"},
    "美的":     {"level": "B", "budget": 60,  "contact": "李经理", "industry": "家电",   "note": "正在对比 3 家供应商"},
    "拼多多":   {"level": "A", "budget": 200, "contact": "王总",   "industry": "互联网", "note": "技术中台主导，要求 API 开放"},
    "腾讯云":   {"level": "A", "budget": 180, "contact": "陈总",   "industry": "云计算", "note": "已有内部 AI 团队，关注集成"},
    "宁德时代": {"level": "B", "budget": 80,  "contact": "刘工",   "industry": "新能源", "note": "Q4 预算审批中"},
}


# ============ 知识库（复用 Week 4，缓存避免重复向量化） ============

@st.cache_resource(show_spinner="⏳ 正在加载知识库并向量化（只需一次）...")
def load_kb(filepath="workbuddy_kb.txt"):
    """加载知识库并向量化，返回 (chunks, vectors)"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    chunks = [c.strip() for c in content.split("\n\n") if c.strip()]

    # 批量向量化
    payload = {"model": "text-embedding-v3", "input": chunks, "dimensions": 256}
    resp = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    data = sorted(resp.json()["data"], key=lambda x: x["index"])
    vectors = [item["embedding"] for item in data]
    return chunks, vectors


def cosine(a, b):
    """余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    return dot / ((sum(x * x for x in a) ** 0.5) * (sum(x * x for x in b) ** 0.5) + 1e-9)


def semantic_search(question, chunks, vectors, top_k=2):
    """语义检索：把问题也向量化，找最相似的片段"""
    q_vec = requests.post(EMBED_URL, headers=HEADERS,
                          json={"model": "text-embedding-v3", "input": [question], "dimensions": 256},
                          timeout=60).json()["data"][0]["embedding"]
    scored = []
    for idx, chunk in enumerate(chunks):
        scored.append((cosine(q_vec, vectors[idx]), chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


# ============ LLM 调用 ============

def call_llm(prompt, temperature=0.3):
    """调用通义千问"""
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature
    }
    resp = requests.post(CHAT_URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ============ 会话状态（预约记录、操作日志） ============

if "bookings" not in st.session_state:
    st.session_state.bookings = []
if "log" not in st.session_state:
    st.session_state.log = []


def log_action(action, input_text, output_text):
    """记录一次操作"""
    st.session_state.log.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "action": action,
        "input": input_text,
        "output": output_text
    })


# ============ 侧边栏：客户速查 + 预约列表 ============

with st.sidebar:
    st.header("📋 客户速查")
    customer = st.selectbox("选择客户", list(CUSTOMERS.keys()))
    info = CUSTOMERS[customer]

    c1, c2 = st.columns(2)
    c1.metric("客户等级", f"{info['level']} 级")
    c2.metric("预算", f"{info['budget']} 万")
    st.metric("联系人", info["contact"])
    st.caption(f"🏭 {info['industry']} ｜ 📌 {info['note']}")

    st.divider()
    st.subheader("📅 演示预约")
    if not st.session_state.bookings:
        st.caption("暂无预约")
    for b in st.session_state.bookings:
        st.markdown(f"**{b['company']}** ｜ {b['date']} {b['time']}\n\n👤 {b['contact']} ｜ ✅ {b['status']}")
        st.divider()

    # 导出记录按钮
    if st.session_state.log:
        csv_text = "time,action,input,output\n"
        for r in st.session_state.log:
            csv_text += f"{r['time']},{r['action']},{r['input']},{r['output'][:60]}\n"
        st.download_button(
            "⬇️ 导出操作记录 CSV",
            data=csv_text.encode("utf-8-sig"),
            file_name=f"销售助手网页记录_{datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True
        )

# ============ 主页面 ============

st.title("💼 AI 销售助手 · 网页版")
st.caption("AI 销售助手 · Streamlit 全功能整合 · 部署版 app.py")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["💰 报价计算", "📅 预约演示", "💬 产品问答", "✨ 话术优化", "🔮 方案推荐"]
)

# ---------- Tab 1: 报价计算 ----------
with tab1:
    st.subheader(f"报价计算 · {customer}")
    st.caption(f"等级 {info['level']} → {'A 级客户享 85 折' if info['level'] == 'A' else 'B 级客户享 92 折'}")

    unit_price = st.number_input("标准单价（万元）", min_value=1.0, value=100.0, step=10.0)

    if st.button("计算报价", type="primary"):
        rate = {"A": 0.85, "B": 0.92}.get(info["level"], 1.0)
        final = round(unit_price * rate, 2)
        saved = round(unit_price - final, 2)

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("标准单价", f"{unit_price:.0f} 万")
        col_b.metric("折扣率", f"{rate:.0%}")
        col_c.metric("最终报价", f"{final:.0f} 万", f"省 {saved:.0f} 万")

        st.success(f"**{customer}**（{info['level']}级）最终报价：**{final:.0f} 万元**，比标准价省了 {saved:.0f} 万。")
        log_action("报价计算", f"{customer}/{unit_price}万", f"报价 {final} 万")

# ---------- Tab 2: 预约演示 ----------
with tab2:
    st.subheader(f"预约产品演示 · {customer}")

    col_date, col_time = st.columns(2)
    demo_date = col_date.date_input("选择日期")
    demo_time = col_time.selectbox("选择时段", ["上午10点", "下午2点", "下午3点", "下午4点"])

    if st.button("确认预约", type="primary"):
        booking = {
            "company": customer,
            "contact": info["contact"],
            "date": str(demo_date),
            "time": demo_time,
            "status": "已预约"
        }
        st.session_state.bookings.append(booking)
        log_action("预约演示", f"{customer}/{demo_date}/{demo_time}", "预约成功")
        st.success(f"✅ 已为 **{customer}**（{info['contact']}）预约 {demo_date} {demo_time}，预约信息已加入侧边栏列表。")

# ---------- Tab 3: 产品问答（RAG） ----------
with tab3:
    st.subheader("💬 产品知识问答")
    st.caption("基于 WorkBuddy 产品知识库 + 语义检索（Embedding），AI 不会胡说八道")

    question = st.text_input("输入客户的问题", value="WorkBuddy 支持私有化部署吗？数据安全怎么保证？")

    if st.button("提问", type="primary"):
        with st.spinner("🔍 语义检索中..."):
            chunks, vectors = load_kb()
            hits = semantic_search(question, chunks, vectors, top_k=2)

        st.caption("🔍 检索到的相关资料：")
        for score, chunk in hits[:2]:
            title = chunk.split("】")[0].lstrip("【")
            st.markdown(f"- 📄 `{title}」相关` （相似度 {score:.2f}）")

        with st.spinner("🤖 AI 正在回答..."):
            context = "\n\n".join([chunk for _, chunk in hits])
            prompt = f"""你是一位 WorkBuddy 产品售前专家。请基于以下资料回答客户问题，资料里没有的明确说没有，不要编造。

【参考资料】
{context}

【问题】
{question}

回答要专业、简洁、口语化，控制在 200 字内。"""
            answer = call_llm(prompt)
        st.info(answer)
        log_action("产品问答", question, answer[:80])

# ---------- Tab 4: 话术优化 ----------
with tab4:
    st.subheader(f"✨ 销售话术优化 · {customer}")

    raw_script = st.text_area(
        "粘贴你的原始话术（随手写的、口语化的都行）",
        value="张工，我们产品功能挺全的，价格也不贵，你们要不要了解一下？",
        height=120
    )

    if st.button("优化话术", type="primary"):
        with st.spinner("✨ AI 正在改写..."):
            prompt = f"""你是一位资深 B 端 SaaS 销售总监。请把以下话术改写成专业版本。

【原始话术】
{raw_script}

【背景】
- 客户：{customer}（{info['industry']}行业，{info['level']}级客户）
- 联系人：{info['contact']}
- 客户备注：{info['note']}
- 产品：WorkBuddy AI 办公平台
- 渠道：微信

要求：痛点切入、价值导向、明确下一步、200字内、适合微信发送。

请输出 JSON（不要代码块）：
{{"optimized_script": "优化后话术", "key_highlights": ["卖点1", "卖点2", "卖点3"], "next_action": "下一步动作", "tone_analysis": "语气分析"}}"""
            result_text = call_llm(prompt)

        # 清理 markdown 并解析 JSON
        cleaned = result_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            result = json.loads(cleaned)
            st.success("优化完成！")
            st.markdown("#### 📝 优化后话术")
            st.write(result.get("optimized_script", cleaned))
            st.markdown("#### 🎯 关键卖点")
            for h in result.get("key_highlights", []):
                st.markdown(f"- {h}")
            st.markdown(f"**📌 下一步**：{result.get('next_action', '')}")
            st.caption(f"💡 语气分析：{result.get('tone_analysis', '')}")
            st.download_button("⬇️ 下载优化话术", data=result.get("optimized_script", ""),
                               file_name=f"{customer}_优化话术.txt")
            log_action("话术优化", raw_script[:50], result.get("optimized_script", "")[:80])
        except Exception:
            st.warning("AI 输出格式异常，直接展示原文：")
            st.write(cleaned)

# ---------- Tab 5: 方案推荐 ----------
with tab5:
    st.subheader(f"🔮 智能方案推荐 · {customer}")

    if st.button("生成推荐方案", type="primary"):
        with st.spinner("🔮 AI 正在制定方案..."):
            prompt = f"""你是一位 WorkBuddy 解决方案架构师。

请根据以下客户信息，推荐最适合的产品方案和切入策略：

【客户信息】
- 公司：{customer}
- 行业：{info['industry']}
- 等级：{info['level']} 级
- 预算：{info['budget']} 万
- 备注：{info['note']}

请输出：
1. 推荐产品版本（专业版/企业版/私有化部署版）
2. 核心卖点（3 个，匹配客户痛点）
3. 切入策略（如何推进到 POC）
4. 风险提示（可能遇到的阻力）

控制在 300 字内。"""
            result = call_llm(prompt)
        st.info(result)
        log_action("方案推荐", customer, result[:80])

# ============ 底部 ============

st.divider()
st.caption(f"💾 本次会话已记录 {len(st.session_state.log)} 次操作 · 点侧边栏「导出操作记录 CSV」下载 · FDE 学习项目")
