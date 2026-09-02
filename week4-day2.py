"""
Week 4 Day 2: 语义检索——让 AI 理解"意思相近"

升级点：
- 关键词检索（Day 1）：只认字面，换种说法就找不到
- 语义检索（今天）：把文字变成向量（数字），"意思相近"的数字距离就近

核心概念：
1. Embedding（向量化）：文字 → 一串数字
2. 余弦相似度：衡量两个向量多接近（越大越相关）
3. 语义检索 = 向量化问题 → 和所有片段算相似度 → 取最相关的
"""

import requests
import json
import re

# 读取 API Key
with open("key.txt", "r", encoding="utf-8") as f:
    API_KEY = f.read().strip()

EMBED_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
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
        "dimensions": 256   # 维度：数字越多越精确，256 教学够用
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


# ============ 加载知识库 ============

def load_chunks(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return [c.strip() for c in content.split("\n\n") if c.strip()]


# ============ 关键词检索（Day 1 的方法，用于对比） ============

def tokenize(text):
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", text)
    if len(text) < 2:
        return {text} if text else set()
    return {text[i:i+2] for i in range(len(text) - 1)}


def keyword_search(query, chunks, top_k=2):
    """关键词检索：算字面重叠"""
    query_terms = tokenize(query)
    scored = []
    for idx, chunk in enumerate(chunks):
        overlap = len(query_terms & tokenize(chunk))
        if overlap > 0:
            scored.append((overlap, idx, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


# ============ 语义检索（今天的新方法） ============

def semantic_search(query_vec, chunk_vecs, chunks, top_k=2):
    """语义检索：算意思相似度"""
    scored = []
    for idx, chunk in enumerate(chunks):
        sim = cosine_similarity(query_vec, chunk_vecs[idx])
        scored.append((sim, idx, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


# ============ RAG 回答 ============

def ask_with_context(question, hits):
    """基于检索到的片段让 AI 回答"""
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
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    resp = requests.post(CHAT_URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ============ 主程序 ============
if __name__ == "__main__":
    print("=" * 60)
    print("🧠 语义检索演示：关键词 vs 语义")
    print("=" * 60)

    # 加载知识库
    chunks = load_chunks("workbuddy_kb.txt")
    print(f"\n✅ 已加载 {len(chunks)} 段产品资料")

    # 预计算所有片段的向量（一次 API 调用）
    print("⏳ 正在把资料转成向量（embedding）...")
    chunk_vecs = get_embeddings_batch(chunks)
    print(f"✅ 完成！每段资料现在是一串 {len(chunk_vecs[0])} 个数字的向量")

    # ===== 概念演示：苹果 =====
    print("\n" + "-" * 60)
    print("【概念演示】'苹果'和谁更接近？（理解 embedding）")
    print("-" * 60)
    words = ["苹果", "水果", "华为", "汽车"]
    apple_vec = get_embeddings_batch(["苹果"])[0]
    for w in words:
        w_vec = get_embeddings_batch([w])[0]
        sim = cosine_similarity(apple_vec, w_vec)
        print(f"   '苹果' vs '{w}'   相似度 {sim:.4f}")
    print("   → 意思相近的（水果），数字上更接近 👆")

    # ===== 核心对比实验 =====
    questions = [
        # 灵魂拷问：没有一个字提到"安全/数据/部署"，关键词检索会扑空
        "客户资料都放在你们服务器上，会不会被看到？",
        # 常规问题：两种检索都能命中
        "AI 能帮我做 PPT 吗？",
    ]

    for q in questions:
        print("\n" + "=" * 60)
        print(f"👤 问题: {q}")
        print("=" * 60)

        # 方法 1：关键词检索
        kw_hits = keyword_search(q, chunks)
        print(f"\n🔤 关键词检索: {len(kw_hits)} 个命中")
        if kw_hits:
            for score, idx, chunk in kw_hits:
                print(f"   重叠{score} | {chunk[:35]}...")
        else:
            print("   ❌ 0 命中！字面都对不上，AI 无资料可用")

        # 方法 2：语义检索
        q_vec = get_embeddings_batch([q])[0]
        sem_hits = semantic_search(q_vec, chunk_vecs, chunks)
        print(f"\n🧠 语义检索: {len(sem_hits)} 个命中")
        for sim, idx, chunk in sem_hits:
            print(f"   相似度{sim:.3f} | {chunk[:35]}...")

        # 用语义检索结果回答
        print(f"\n🤖 AI 回答（基于语义检索到的资料）:")
        answer = ask_with_context(q, sem_hits)
        print(f"   {answer}")

    print("\n" + "=" * 60)
    print("今日要点：")
    print("1. 关键词检索：认字面，换个说法就找不到")
    print("2. 语义检索：认意思，'会不会被看到'也能命中'数据安全'")
    print("3. 向量 = 文字的数字指纹，意思近 → 数字近")
    print("4. 真正的知识库问答，语义检索是标配")
    print("=" * 60)
