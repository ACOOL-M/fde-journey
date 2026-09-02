# Week 3 Day 1: 第一次调用大模型 API
# 目标：把一段客户会议纪要发给通义千问，让它自动总结
# 前置：同目录下要有 key.txt（里面是你从阿里云百炼复制的 API Key）

import requests
import json

# ===== 第 1 步：读取你的 API Key =====
with open("key.txt", "r", encoding="utf-8") as f:
    API_KEY = f.read().strip()

print("API Key 读取成功:", API_KEY[:6] + "..." + API_KEY[-4:])
print("=" * 50)

# ===== 第 2 步：准备要发给 AI 的消息 =====
meeting_notes = """
与比亚迪采购部李经理的会议纪要：
1. 他们正在评估 3 家 AI 办公产品供应商，我们是其中之一
2. 预算大约 200 万一年，需要覆盖 5000 人
3. 关注点：数据安全、与现有 ERP 系统的集成、员工培训成本
4. 竞品（某国外产品）已进入 POC 阶段
5. 李经理要求我们下周内提交方案和报价
6. 决策链：采购部初筛，CIO 终审，周期约 3 个月
"""

# ===== 第 3 步：构造 API 请求 =====
url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

payload = {
    "model": "qwen-plus",  # 通义千问中档模型，够用且便宜
    "messages": [
        {"role": "system", "content": "你是一位资深的B端销售助理，擅长从会议纪要中提取关键信息。"},
        {"role": "user", "content": f"请总结以下客户会议纪要，输出：1) 客户意向程度 2) 三个关键信息 3) 建议的下一步动作。\n\n{meeting_notes}"}
    ],
    "temperature": 0.3,  # 温度越低，回答越保守稳定
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

print("正在发送请求给通义千问...")

# ===== 第 4 步：发送请求并接收回复 =====
response = requests.post(url, headers=headers, json=payload, timeout=60)

# ===== 第 5 步：处理回复 =====
if response.status_code == 200:
    result = response.json()
    answer = result["choices"][0]["message"]["content"]
    print("=" * 50)
    print("AI 回复：")
    print(answer)
else:
    print(f"请求失败，状态码: {response.status_code}")
    print("错误信息:", response.text)
