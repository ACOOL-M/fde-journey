# Week 3 Day 1 主菜：客户纪要自动总结器
# 功能：输入客户会议纪要 -> AI 总结 -> 结构化 JSON -> 存 CSV
# 前置：同目录下要有 key.txt（阿里云百炼 API Key）

import requests
import json
import pandas as pd

# ===== 读取 API Key =====
with open("key.txt", "r", encoding="utf-8") as f:
    API_KEY = f.read().strip()


def summarize_meeting(notes):
    """把会议纪要发给 AI，返回 AI 的原始回复"""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    prompt = f"""你是一位B端销售助理。请分析以下客户会议纪要，并以 JSON 格式输出结果。

要求输出以下字段：
- customer: 客户名称
- contact: 对接人
- intent: 意向程度（高/中/低）
- budget: 预算金额
- pain_points: 客户痛点（一句话）
- next_step: 建议下一步动作
- deadline: 客户要求的时间节点

会议纪要：
{notes}
"""

    payload = {
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": "你只输出 JSON，不要输出其他内容。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        print(f"API 请求失败: {response.status_code}")
        print(response.text)
        return None

    result = response.json()
    return result["choices"][0]["message"]["content"]


def parse_json(text):
    """从 AI 回复中提取 JSON（处理可能的 markdown 代码块包裹）"""
    text = text.strip()
    # 去掉 ```json 和 ``` 包裹
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    # 只保留第一个 { 到最后一个 } 之间的内容
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


# ===== 测试：处理 3 条客户纪要 =====
meetings = [
    "与腾讯云王经理沟通：他们想用 AI 优化客服部门，现有客服团队 300 人。预算 100 万以内，希望 3 个月内看到效果。竞品已提交方案。",
    "拼多多运营部李总来电：咨询 AI 办公产品的员工培训方案，他们更看重易用性，预算 50 万左右，决策较快。",
    "美的集团 IT 部张工：目前没有明确预算，处于技术调研阶段，想了解我们的数据安全方案。",
]

print("开始处理", len(meetings), "条客户纪要...")
print("=" * 50)

results = []
for i, notes in enumerate(meetings, 1):
    print(f"第 {i}/{len(meetings)} 条：正在总结...")
    ai_output = summarize_meeting(notes)
    if ai_output:
        try:
            data = parse_json(ai_output)
            results.append(data)
            print(f"  ✅ 客户: {data.get('customer')} | 意向: {data.get('intent')} | 下一步: {data.get('next_step')}")
        except Exception as e:
            print(f"  ⚠️ AI 输出解析失败: {e}")
            print(f"     原始回复: {ai_output[:150]}")
    print("-" * 50)

# ===== 存成 CSV =====
if results:
    df = pd.DataFrame(results)
    df.to_csv("纪要总结.csv", index=False, encoding="utf-8-sig")
    print(f"已保存 {len(results)} 条总结到 纪要总结.csv")
    print()
    print("完整表格：")
    print(df.to_string(index=False))
else:
    print("没有成功解析任何结果，请检查 key.txt 是否正确")
