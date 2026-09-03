"""
Week 5: AI 销售助手——终极实战项目
把前面所有技术整合成一个真正能用的销售工具：
  1. 客户管理（查信息、算报价、记预约）
  2. 话术优化（粗糙 → 专业）
  3. 产品问答（RAG 知识库）
  4. 智能推荐（基于客户等级推荐方案）

技术栈：API 调用 + Prompt Engineering + Function Calling + RAG + Embedding
"""

import requests
import json
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

# ============ 客户数据库 ============

CUSTOMERS = {
    "比亚迪":   {"level": "A", "budget": 150, "contact": "张工",   "industry": "制造业", "note": "关心数据安全和 ERP 对接"},
    "美的":     {"level": "B", "budget": 60,  "contact": "李经理", "industry": "家电",   "note": "正在对比 3 家供应商"},
    "拼多多":   {"level": "A", "budget": 200, "contact": "王总",   "industry": "互联网", "note": "技术中台主导，要求 API 开放"},
    "腾讯云":   {"level": "A", "budget": 180, "contact": "陈总",   "industry": "云计算", "note": "已有内部 AI 团队，关注集成"},
    "宁德时代": {"level": "B", "budget": 80,  "contact": "刘工",   "industry": "新能源", "note": "Q4 预算审批中"},
}

BOOKINGS = []

# ============ 知识库（复用 Week 4） ============

class KnowledgeBase:
    def __init__(self, filepath):
        self.chunks = self._load(filepath)
        self.vectors = self._embed(self.chunks)

    def _load(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return [c.strip() for c in content.split("\n\n") if c.strip()]

    def _embed(self, texts):
        payload = {"model": "text-embedding-v3", "input": texts, "dimensions": 256}
        resp = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in data]

    def search(self, query, top_k=2):
        q_vec = self._embed([query])[0]
        scored = []
        for idx, chunk in enumerate(self.chunks):
            sim = self._cosine(q_vec, self.vectors[idx])
            scored.append((sim, idx, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def _cosine(self, a, b):
        dot = sum(x * y for x, y in zip(a, b))
        return dot / ((sum(x * x for x in a) ** 0.5) * (sum(x * x for x in b) ** 0.5) + 1e-9)


# ============ AI 销售助手 ============

class SalesAssistant:
    """整合所有能力的 AI 销售助手"""

    def __init__(self, kb):
        self.kb = kb
        self.history = []
        self.records = []

    # ---- 工具 1：查客户 ----
    def get_customer_info(self, company_name):
        info = CUSTOMERS.get(company_name)
        if info:
            return json.dumps(info, ensure_ascii=False)
        return json.dumps({"error": f"未找到 {company_name}"}, ensure_ascii=False)

    # ---- 工具 2：算报价 ----
    def calc_discount(self, company_name, unit_price):
        info = CUSTOMERS.get(company_name)
        if not info:
            return json.dumps({"error": f"未找到 {company_name}"}, ensure_ascii=False)
        rate = {"A": 0.85, "B": 0.92}.get(info["level"], 1.0)
        final = round(unit_price * rate, 2)
        return json.dumps({
            "company": company_name, "level": info["level"],
            "unit_price": unit_price, "discount_rate": rate,
            "final_price": final, "saved": round(unit_price - final, 2)
        }, ensure_ascii=False)

    # ---- 工具 3：预约演示 ----
    def book_demo(self, company_name, date, time_slot):
        info = CUSTOMERS.get(company_name)
        if not info:
            return json.dumps({"error": f"未找到 {company_name}"}, ensure_ascii=False)
        booking = {"company": company_name, "contact": info["contact"],
                   "date": date, "time": time_slot, "status": "已预约"}
        BOOKINGS.append(booking)
        return json.dumps(booking, ensure_ascii=False)

    # ---- 工具 4：产品问答（RAG） ----
    def product_qa(self, question):
        hits = self.kb.search(question, top_k=2)
        context = "\n\n".join([chunk for _, _, chunk in hits])
        prompt = f"""你是一位 WorkBuddy 产品售前专家。请基于以下资料回答，没有就明确说没有。

【参考资料】
{context}

【问题】
{question}

回答要专业、简洁、口语化。"""
        return self._call_llm(prompt)

    # ---- 工具 5：话术优化 ----
    def optimize_script(self, raw_script, client_name):
        prompt = f"""你是一位资深 B 端 SaaS 销售总监。请把以下话术改写成专业版本。

【原始话术】
{raw_script}

【背景】
- 客户：{client_name}
- 产品：WorkBuddy AI 办公平台
- 渠道：微信

要求：痛点切入、价值导向、明确下一步、200字内、适合微信发送。

请输出 JSON（不要代码块）：
{{"optimized_script": "...", "key_highlights": ["..."], "next_action": "...", "tone_analysis": "..."}}"""
        result = self._call_llm(prompt)
        # 清理可能的 markdown
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1] if "```" in cleaned[3:] else cleaned[3:]
            cleaned = cleaned.strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        return json.loads(cleaned)

    # ---- 工具 6：智能推荐 ----
    def recommend_solution(self, company_name):
        info = CUSTOMERS.get(company_name)
        if not info:
            return f"未找到 {company_name} 的客户信息"

        prompt = f"""你是一位 WorkBuddy 解决方案架构师。

请根据以下客户信息，推荐最适合的产品方案和切入策略：

【客户信息】
- 公司：{company_name}
- 行业：{info['industry']}
- 等级：{info['level']} 级
- 预算：{info['budget']} 万
- 备注：{info['note']}

请输出：
1. 推荐产品版本（专业版/企业版/私有化）
2. 核心卖点（3 个，匹配客户痛点）
3. 切入策略（如何推进到 POC）
4. 风险提示（可能遇到的阻力）

控制在 300 字内。"""
        return self._call_llm(prompt)

    # ---- LLM 调用 ----
    def _call_llm(self, prompt, temperature=0.3):
        payload = {
            "model": "qwen-plus",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }
        resp = requests.post(CHAT_URL, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    # ---- 保存记录 ----
    def save_records(self, filename="销售助手记录.csv"):
        if not self.records:
            return
        file_exists = os.path.exists(filename)
        with open(filename, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["time", "action", "input", "output"])
            if not file_exists:
                writer.writeheader()
            for r in self.records:
                writer.writerow(r)
        print(f"📁 已保存 {len(self.records)} 条记录到 {filename}")
        self.records = []


# ============ 交互式菜单 ============

def print_menu():
    print("\n" + "=" * 50)
    print("💼 AI 销售助手")
    print("=" * 50)
    print("1. 查客户信息")
    print("2. 算折扣报价")
    print("3. 预约产品演示")
    print("4. 产品知识问答")
    print("5. 优化销售话术")
    print("6. 智能方案推荐")
    print("7. 查看演示预约")
    print("8. 保存并退出")
    print("=" * 50)


def main():
    print("⏳ 正在加载知识库...")
    kb = KnowledgeBase("workbuddy_kb.txt")
    assistant = SalesAssistant(kb)
    print("✅ 销售助手已就绪！\n")

    while True:
        print_menu()
        choice = input("请选择功能 (1-8): ").strip()

        if choice == "1":
            name = input("客户名称: ").strip()
            result = assistant.get_customer_info(name)
            print(f"\n📋 {result}")
            assistant.records.append({"time": datetime.now().strftime("%H:%M"), "action": "查客户", "input": name, "output": result})

        elif choice == "2":
            name = input("客户名称: ").strip()
            price = float(input("标准单价（万元）: ").strip())
            result = assistant.calc_discount(name, price)
            print(f"\n💰 {result}")
            assistant.records.append({"time": datetime.now().strftime("%H:%M"), "action": "算报价", "input": f"{name}/{price}万", "output": result})

        elif choice == "3":
            name = input("客户名称: ").strip()
            date = input("日期 (如 2026-09-10): ").strip()
            time = input("时间 (如 下午3点): ").strip()
            result = assistant.book_demo(name, date, time)
            print(f"\n📅 {result}")
            assistant.records.append({"time": datetime.now().strftime("%H:%M"), "action": "预约", "input": f"{name}/{date}/{time}", "output": result})

        elif choice == "4":
            q = input("客户问题: ").strip()
            print("\n🤖 思考中...")
            answer = assistant.product_qa(q)
            print(f"\n💬 {answer}")
            assistant.records.append({"time": datetime.now().strftime("%H:%M"), "action": "产品问答", "input": q, "output": answer[:100]})

        elif choice == "5":
            name = input("客户名称: ").strip()
            print("粘贴你的原始话术（多行，输入空行结束）:")
            lines = []
            while True:
                line = input()
                if line.strip() == "":
                    break
                lines.append(line)
            raw = "\n".join(lines)
            print("\n✨ 优化中...")
            result = assistant.optimize_script(raw, name)
            print(f"\n📝 优化后话术:\n{result['optimized_script']}")
            print(f"\n🎯 卖点: {' | '.join(result['key_highlights'])}")
            print(f"📌 下一步: {result['next_action']}")
            assistant.records.append({"time": datetime.now().strftime("%H:%M"), "action": "话术优化", "input": raw[:50], "output": result['optimized_script'][:100]})

        elif choice == "6":
            name = input("客户名称: ").strip()
            print("\n🔮 生成方案推荐...")
            result = assistant.recommend_solution(name)
            print(f"\n{result}")
            assistant.records.append({"time": datetime.now().strftime("%H:%M"), "action": "方案推荐", "input": name, "output": result[:100]})

        elif choice == "7":
            print("\n📅 当前演示预约:")
            if not BOOKINGS:
                print("   暂无预约")
            for b in BOOKINGS:
                print(f"   · {b['company']} | {b['date']} {b['time']} | {b['contact']} | {b['status']}")

        elif choice == "8":
            assistant.save_records()
            print("👋 销售助手已退出，记录已保存。")
            break

        else:
            print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    main()
