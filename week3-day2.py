"""
Week 3 Day 2: 提示词工程 Prompt Engineering
核心：同样的模型，提示词写得好不好，输出质量天差地别。
"""

import requests

# 读取 API Key
with open("key.txt", "r", encoding="utf-8") as f:
    API_KEY = f.read().strip()

URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def ask_ai(prompt, temperature=0.3):
    """调用通义千问，返回 AI 回复文本。"""
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature
    }
    resp = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ============ 实验 1: 烂提示词 vs 好提示词 ============

print("=" * 60)
print("实验 1：同一个问题，提示词质量对比")
print("=" * 60)

bad_prompt = "写个销售话术"

good_prompt = """
你是一位资深 B 端 SaaS 销售专家，擅长向企业 IT 负责人推销 AI 办公产品。

请为以下场景撰写一段销售跟进话术：
- 客户：比亚迪 IT 部门负责人
- 产品：WorkBuddy AI 办公平台（企业版）
- 场景：初次拜访后，发微信跟进，希望推进到 POC 试用阶段
- 要求：
  1. 语气专业但不生硬，体现对客户的尊重
  2. 提及上次拜访的关键点（客户关心数据安全和部署成本）
  3. 明确提出下一步：提供私有化部署方案 + 申请 30 天免费试用
  4. 控制在 150 字以内，适合微信发送

请直接输出话术内容，不要加解释。
"""

print("\n【烂提示词】输出：")
print(ask_ai(bad_prompt))

print("\n" + "-" * 60)
print("\n【好提示词】输出：")
print(ask_ai(good_prompt))


# ============ 实验 2: 角色设定 ============

print("\n" + "=" * 60)
print("实验 2：角色设定的威力")
print("=" * 60)

no_role = "解释什么是 API"
with_role = "你是一位给零基础销售同事做技术培训的专家。请用通俗的比喻解释什么是 API，要求：1) 举一个销售场景的例子 2) 不超过 100 字"

print("\n【无角色】输出：")
print(ask_ai(no_role))

print("\n" + "-" * 60)
print("\n【有角色】输出：")
print(ask_ai(with_role))


# ============ 实验 3: 给示例（Few-shot） ============

print("\n" + "=" * 60)
print("实验 3：给示例，让 AI 学会你的格式")
print("=" * 60)

few_shot_prompt = """
你是一位客户分级助手。请根据客户的描述，将其分级为 A/B/C/D，并给出理由。

分级标准：
- A：预算明确、决策链清晰、近期有采购计划
- B：有需求但预算或时间未定
- C：仅初步了解，无明确需求
- D：无效线索

请严格按以下格式输出：
分级: X
理由: XXX

示例 1：
输入："我们是美的集团，正在评估 AI 办公方案，Q4 有 200 万预算，已经对比了 3 家供应商"
分级: A
理由: 预算明确、时间清晰、已进入选型阶段

示例 2：
输入："我们公司 50 人，想了解下你们产品，现在还在用钉钉"
分级: C
理由: 仅初步了解，无明确采购意向和预算

现在请分析：
输入："我们是拼多多技术中台，目前 2000+ 人，内部系统在调研大模型接入，希望 11 月前完成试点，预算在走审批"
"""

print("\n【Few-shot 提示词】输出：")
print(ask_ai(few_shot_prompt))


# ============ 实验 4: 输出格式控制 ============

print("\n" + "=" * 60)
print("实验 4：强制 JSON 输出（程序友好）")
print("=" * 60)

json_prompt = """
请分析以下客户信息，提取关键字段，并以 JSON 格式输出。

客户信息：
"比亚迪股份有限公司，IT 中心，联系人张工，电话 138-xxxx-1234，
正在评估 WorkBuddy 企业版，需求：私有化部署 + U9 ERP 对接，
预算 150 万左右，希望 10 月底前完成 POC，决策链：IT 总监 → 采购部 → CIO"

要求 JSON 字段：
- company: 公司名称
- contact: 联系人
- phone: 电话
- product: 意向产品
- requirements: 需求列表（数组）
- budget: 预算
- timeline: 时间要求
- decision_chain: 决策链（数组）
- level: 客户分级（A/B/C/D）

只输出纯 JSON，不要 Markdown 代码块，不要解释。
"""

print("\n【JSON 格式提示词】输出：")
result = ask_ai(json_prompt)
print(result)

# 验证是否能解析为 JSON
import json
try:
    data = json.loads(result)
    print("\n✅ 成功解析为 JSON！")
    print(f"公司: {data.get('company')}, 分级: {data.get('level')}")
except Exception as e:
    print(f"\n❌ JSON 解析失败: {e}")


print("\n" + "=" * 60)
print("今日要点总结：")
print("1. 角色设定 → 让 AI 进入专业状态")
print("2. 具体约束 → 字数、格式、场景越具体越好")
print("3. 给示例（Few-shot）→ AI 会模仿你的格式")
print("4. 输出格式控制 → JSON/Markdown/表格，程序可直接用")
print("=" * 60)
