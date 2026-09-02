"""
实战项目：WorkBuddy 智能产品顾问
功能：
  1. 加载知识库 → 向量化 → 语义检索
  2. 支持多轮对话（记住上下文）
  3. 自动保存问答记录到 CSV
  4. 支持追问模式（"那私有化部署呢？"AI 能承接上文）

技术栈：Embedding + 语义检索 + LLM + 对话记忆
"""

import requests
import json
import re
import csv
import os
from datetime import datetime

# 读取 API Key
with open("key.txt", "r", encoding="utf-8") as f:
    API_KEY = f.read().strip()

EMBED_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ============ 知识库引擎 ============

class KnowledgeBase:
    """知识库：加载 → 向量化 → 语义检索"""

    def __init__(self, filepath):
        self.chunks = self._load(filepath)
        self.vectors = self._embed(self.chunks)
        print(f"📚 知识库加载完成：{len(self.chunks)} 段资料")

    def _load(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return [c.strip() for c in content.split("\n\n") if c.strip()]

    def _embed(self, texts):
        """批量向量化"""
        payload = {
            "model": "text-embedding-v3",
            "input": texts,
            "dimensions": 256
        }
        resp = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in data]

    def search(self, query, top_k=2):
        """语义检索：返回最相关的 top_k 个片段"""
        q_vec = self._embed([query])[0]
        scored = []
        for idx, chunk in enumerate(self.chunks):
            sim = self._cosine(q_vec, self.vectors[idx])
            scored.append((sim, idx, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def _cosine(self, a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb + 1e-9)


# ============ 对话机器人 ============

class ProductAdvisor:
    """产品顾问：RAG + 多轮对话 + 记录保存"""

    def __init__(self, kb):
        self.kb = kb
        self.history = []  # 对话历史 [(role, content), ...]
        self.records = []  # 问答记录

    def ask(self, question):
        """处理用户提问，返回 AI 回答"""
        # 1. 检索相关片段
        hits = self.kb.search(question, top_k=2)
        context = "\n\n".join([chunk for _, _, chunk in hits])

        # 2. 组装 prompt（含上下文 + 检索资料）
        system_prompt = """你是一位 WorkBuddy 产品售前专家，正在通过对话为客户解答产品问题。

规则：
1. 优先基于参考资料回答，资料中没有的明确说"资料中没有相关内容"
2. 回答专业、简洁、口语化，适合直接发给客户
3. 如果用户在追问（如"那价格呢？""还有呢？"），结合上下文理解他的意图
4. 不要编造数字、功能或案例"""

        messages = [{"role": "system", "content": system_prompt}]

        # 加入最近 3 轮对话历史（让 AI 理解追问）
        for role, content in self.history[-6:]:
            messages.append({"role": role, "content": content})

        # 当前问题：附加上下文
        messages.append({
            "role": "user",
            "content": f"【参考资料】\n{context}\n\n【用户问题】\n{question}"
        })

        # 3. 调用 AI
        payload = {
            "model": "qwen-plus",
            "messages": messages,
            "temperature": 0.3
        }
        resp = requests.post(CHAT_URL, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"]

        # 4. 保存对话历史
        self.history.append(("user", question))
        self.history.append(("assistant", answer))

        # 5. 保存记录
        self.records.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "question": question,
            "answer": answer,
            "context": context[:200]  # 只存前 200 字
        })

        return answer, hits

    def save_records(self, filename="顾问问答记录.csv"):
        """保存问答记录到 CSV"""
        file_exists = os.path.exists(filename)
        with open(filename, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["time", "question", "answer", "context"])
            if not file_exists:
                writer.writeheader()
            for r in self.records:
                writer.writerow(r)
        print(f"📁 已保存 {len(self.records)} 条记录到 {filename}")
        self.records = []


# ============ 主程序 ============
if __name__ == "__main__":
    print("=" * 60)
    print("💼 WorkBuddy 智能产品顾问")
    print("=" * 60)

    # 初始化知识库
    kb = KnowledgeBase("workbuddy_kb.txt")
    advisor = ProductAdvisor(kb)

    # 自动演示：多轮对话
    demo_dialogue = [
        "WorkBuddy 是什么产品？",
        "那数据安全怎么样？",           # 追问：承接上文
        "支持私有化部署吗？",
        "企业版多少钱？",               # 追问：可能承接"企业版"
        "AI 能帮我做 PPT 吗？",
    ]

    print("\n【自动演示：多轮对话】")
    print("-" * 60)

    for q in demo_dialogue:
        print(f"\n👤 客户: {q}")
        answer, hits = advisor.ask(q)
        print(f"🤖 顾问: {answer}")
        print(f"   🔍 检索依据: {[chunk[:30] + '...' for _, _, chunk in hits]}")

    # 保存演示记录
    advisor.save_records()

    # 实战：自由对话
    print("\n" + "=" * 60)
    print("【实战练习】自由提问（输入 exit 退出）")
    print("试试追问：先问功能，再问价格，再问安全")
    print("=" * 60)

    while True:
        user_input = input("\n👤 客户: ").strip()
        if user_input.lower() in ("exit", "quit", "退出"):
            advisor.save_records()
            print("👋 产品顾问已下线，问答记录已保存。")
            break
        if not user_input:
            continue

        answer, hits = advisor.ask(user_input)
        print(f"🤖 顾问: {answer}")
        print(f"   🔍 检索依据: {[chunk[:30] + '...' for _, _, chunk in hits]}")
