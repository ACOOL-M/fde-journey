"""
Week 4 Day 1: RAG 入门——让 AI 基于你的资料回答问题
RAG = Retrieval-Augmented Generation（检索增强生成）

完整流程四步：
1. 加载文档（真实项目：PDF / Word / 网页 / 数据库）
2. 切块（把长文档切成小片段）
3. 检索（用户提问时，找出最相关的片段）
4. 生成（把"问题 + 相关片段"一起给 AI，AI 基于资料回答）

本文件用最简实现演示全流程，不依赖任何额外库。
"""

import requests
import json
import re

# 读取 API Key
with open("key.txt", "r", encoding="utf-8") as f:
    API_KEY = f.read().strip()

URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ============ 第 1 步：加载文档 ============

def load_documents(filepath):
    """读取知识库文件，按空行切块，返回片段列表"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # 按空行分成段落块
    chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
    return chunks


# ============ 第 2 步：切块（上面已按段落切好） ============

# ============ 第 3 步：检索（关键词重叠打分） ============

def tokenize(text):
    """把文本切成二元词组（bigram），适合中文检索"""
    # 只保留中英文和数字
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", text)
    if len(text) < 2:
        return {text} if text else set()
    # 切成连续的 2 字词组："私有化部署" -> {"私有","有化","化部","部署"}
    return {text[i:i+2] for i in range(len(text) - 1)}


def search_documents(query, chunks, top_k=2):
    """计算问题和每个片段的重叠词组数，返回最相关的 top_k 个片段"""
    query_terms = tokenize(query)
    scored = []
    for idx, chunk in enumerate(chunks):
        chunk_terms = tokenize(chunk)
        overlap = len(query_terms & chunk_terms)
        if overlap > 0:
            scored.append((overlap, idx, chunk))

    # 按重叠度从高到低排序
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


# ============ 第 4 步：生成（组装 RAG prompt） ============

def ask_with_rag(question, chunks):
    """完整 RAG：检索 + 基于资料回答"""
    # 1. 检索相关片段
    hits = search_documents(question, chunks, top_k=2)
    print(f"🔍 检索到 {len(hits)} 个相关片段:")
    for score, idx, chunk in hits:
        print(f"   · 重叠度 {score} | {chunk[:40]}...")

    if not hits:
        print("⚠️ 没有检索到相关资料，AI 将直接回答（可能不准）")

    # 2. 组装 prompt：把检索到的片段作为"参考资料"
    context = "\n\n".join([chunk for _, _, chunk in hits])
    prompt = f"""你是一位 WorkBuddy 产品售前专家。

请严格基于以下参考资料回答用户问题。如果资料里没有相关信息，就明确说"资料中没有相关内容"，不要编造。

【参考资料】
{context}

【用户问题】
{question}

【回答要求】
- 只依据参考资料回答
- 回答要专业、简洁、口语化，适合直接发给客户
"""

    # 3. 发给 AI
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    resp = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def ask_without_rag(question):
    """对照组：不带资料，直接问 AI（会胡说）"""
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.3
    }
    resp = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ============ 主程序 ============
if __name__ == "__main__":
    print("=" * 60)
    print("📚 RAG 演示：WorkBuddy 产品知识库问答")
    print("=" * 60)

    # 加载知识库
    chunks = load_documents("workbuddy_kb.txt")
    print(f"\n✅ 已加载 {len(chunks)} 段产品资料")

    questions = [
        "WorkBuddy 支持私有化部署吗？数据安全怎么样？",
        "企业版多少钱？怎么定价的？",
        "WorkBuddy 能和腾讯会议打通吗？",
    ]

    for q in questions:
        print("\n" + "=" * 60)
        print(f"👤 问题: {q}")
        print("=" * 60)

        # 对照组：不带资料
        print("\n【对照】不带资料直接问 AI:")
        print(f"🤖 {ask_without_rag(q)[:150]}...")

        # 实验组：RAG
        print("\n【实验】RAG 流程（检索 + 基于资料回答）:")
        answer = ask_with_rag(q, chunks)
        print(f"🤖 {answer}")

    print("\n" + "=" * 60)
    print("今日要点：")
    print("1. AI 不知道你的产品细节 → 会胡说八道")
    print("2. RAG = 先检索相关资料，再让 AI 基于资料回答")
    print("3. 四步流程：加载 → 切块 → 检索 → 生成")
    print("4. 关键词检索是入门版，明天升级为语义检索（更聪明）")
    print("=" * 60)
