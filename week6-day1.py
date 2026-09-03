"""
Week 6 Day 1: Streamlit Web 界面入门
把 AI 工具从"终端黑窗口"变成"网页应用"

Streamlit 核心理解：
- 每次用户在网页上操作，整个脚本从头到尾重新跑一遍
- st.title / st.text_input / st.button = 网页上的元素
- 运行方式：streamlit run week6-day1.py（不是 python xxx.py！）
"""

import requests
import streamlit as st

# ============ 页面配置（必须放最前面） ============

st.set_page_config(
    page_title="AI 销售工作台",
    page_icon="💼",
    layout="wide"
)

# ============ API 配置 ============

with open("key.txt", "r", encoding="utf-8") as f:
    API_KEY = f.read().strip()

CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 客户数据
CUSTOMERS = {
    "比亚迪":   {"level": "A", "budget": 150, "contact": "张工"},
    "美的":     {"level": "B", "budget": 60,  "contact": "李经理"},
    "拼多多":   {"level": "A", "budget": 200, "contact": "王总"},
    "腾讯云":   {"level": "A", "budget": 180, "contact": "陈总"},
    "宁德时代": {"level": "B", "budget": 80,  "contact": "刘工"},
}


def call_llm(prompt):
    """调用通义千问"""
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    resp = requests.post(CHAT_URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ============ 页面结构 ============

# 标题
st.title("💼 AI 销售工作台")
st.caption("Week 6 Day 1 · Streamlit 入门 · FDE 学习项目")

# 侧边栏
with st.sidebar:
    st.header("📋 客户速查")
    customer = st.selectbox("选择客户", list(CUSTOMERS.keys()))
    info = CUSTOMERS[customer]
    st.metric("客户等级", info["level"])
    st.metric("预算（万元）", info["budget"])
    st.metric("联系人", info["contact"])
    st.divider()
    st.write("💡 这个面板就是 Streamlit 的**侧边栏**")

# 主区域分成两列
col1, col2 = st.columns(2)

# 左列：客户跟进话术生成
with col1:
    st.header("📝 跟进话术生成")
    scene = st.text_input(
        "跟进场景",
        value="初次拜访后微信跟进，希望推进到产品演示"
    )
    if st.button("生成话术", type="primary", use_container_width=True):
        with st.spinner("AI 正在撰写..."):
            prompt = f"""你是一位资深 B 端 SaaS 销售专家。请为以下场景写一段微信跟进话术：
- 客户：{customer}（等级{info['level']}，联系人{info['contact']}）
- 产品：WorkBuddy AI 办公平台
- 场景：{scene}
要求：痛点切入、价值导向、明确下一步、150字内、适合微信发送。直接输出话术。"""
            try:
                result = call_llm(prompt)
                st.success("生成完成！")
                st.write(result)
                st.download_button(
                    "下载话术",
                    data=result,
                    file_name=f"{customer}_跟进话术.txt",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"出错了: {e}")

# 右列：AI 问答
with col2:
    st.header("💬 AI 问答")
    question = st.text_input(
        "你的问题",
        value="WorkBuddy 支持私有化部署吗？"
    )
    if st.button("提问", type="primary", use_container_width=True):
        with st.spinner("思考中..."):
            try:
                answer = call_llm(question)
                st.info(answer)
            except Exception as e:
                st.error(f"出错了: {e}")

# 底部：Streamlit 元素演示
st.divider()
st.header("🎁 Streamlit 常用元素速览")

expander_col, metric_col = st.columns(2)

with expander_col:
    with st.expander("点击展开：这是什么技术？"):
        st.write("""
- **Streamlit**：把 Python 脚本一键变成网页
- 不用写 HTML / CSS / JavaScript
- 数据科学和 AI 应用的首选原型工具
- 运行方式：`streamlit run 文件名.py`
        """)
    st.code("streamlit run week6-day1.py", language="bash")

with metric_col:
    st.write("📊 指标卡片（st.metric）：")
    m1, m2, m3 = st.columns(3)
    m1.metric("客户数", "5", "+2 本月")
    m2.metric("预约数", "3", "+1")
    m3.metric("成交额", "¥280万", "+12%")

st.divider()
st.caption("学完今天你就有了自己的 Web 应用 · 明天把完整销售助手搬上网页")
