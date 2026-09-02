"""
实战项目：销售话术优化器
功能：输入一段粗糙的销售话术，AI 帮你改写成专业 B 端销售话术
作者：FDE 学习项目
"""

import requests
import json
from datetime import datetime

# 读取 API Key
with open("key.txt", "r", encoding="utf-8") as f:
    API_KEY = f.read().strip()

URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def optimize_sales_script(raw_script, client_name, product="WorkBuddy"):
    """
    用结构化提示词优化销售话术。

    参数:
        raw_script: 用户随便写的原始话术
        client_name: 客户名称，用于个性化
        product: 产品名称，默认 WorkBuddy

    返回:
        dict，包含优化后的话术和配套建议
    """

    # ========== 核心：精心设计的提示词 ==========
    system_prompt = """你是一位拥有 15 年经验的 B 端 SaaS 销售总监，曾服务过腾讯、阿里、字节等大型企业客户。
你擅长将粗糙的销售话术改写为专业、有说服力、能推进商机的 B 端销售沟通内容。
你的改写风格：专业但不生硬、有逻辑层次、直击客户痛点、明确下一步动作。"""

    user_prompt = f"""请对以下销售话术进行专业改写。

【原始话术】
{raw_script}

【背景信息】
- 目标客户：{client_name}
- 推销产品：{product} AI 办公平台（企业版）
- 沟通渠道：微信/企业微信

【改写要求】
1. 开头用客户关心的痛点或上次沟通的关键点切入
2. 中间清晰阐述产品价值（用"你能获得什么"而非"我们有什么功能"）
3. 明确提出下一步动作（如：预约演示、发送方案、安排 POC）
4. 结尾留出互动空间，不要写成封闭句
5. 语气：专业、真诚、不卑不亢，适合 B 端 IT 负责人阅读
6. 字数控制在 200 字以内

【输出格式】
请严格按以下 JSON 格式输出（不要 Markdown 代码块，不要额外解释）：
{{
  "optimized_script": "优化后的完整话术",
  "key_highlights": ["话术中的 3 个关键卖点"],
  "next_action": "建议的下一步动作",
  "tone_analysis": "这段话传递的核心语气"
}}
"""

    payload = {
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3
    }

    resp = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()

    ai_text = resp.json()["choices"][0]["message"]["content"]

    # 清理可能的 Markdown 代码块
    cleaned = ai_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1] if "```" in cleaned[3:] else cleaned[3:]
        cleaned = cleaned.strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    return json.loads(cleaned)


def save_to_history(result, client_name, raw_script):
    """保存优化记录到 CSV"""
    import csv
    import os

    filename = "话术优化记录.csv"
    file_exists = os.path.exists(filename)

    with open(filename, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["时间", "客户", "原始话术", "优化后话术", "关键卖点", "下一步", "语气"])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            client_name,
            raw_script.replace("\n", " "),
            result["optimized_script"].replace("\n", " "),
            " | ".join(result["key_highlights"]),
            result["next_action"],
            result["tone_analysis"]
        ])

    print(f"📁 已保存到 {filename}")


# ============ 主程序 ============
if __name__ == "__main__":

    print("=" * 60)
    print("💼 销售话术优化器")
    print("=" * 60)

    # 示例 1：直接运行默认演示
    demo_raw = """张工你好，上次跟你聊的 WorkBuddy 你考虑得怎么样了？
我们产品功能挺全的，有 AI 助手、文档管理、会议什么的。
价格也不贵，你要不要试试？有空咱们再聊聊。"""

    print("\n【示例演示】")
    print(f"客户: 比亚迪")
    print(f"原始话术:\n{demo_raw}")
    print("\n正在优化...")

    try:
        result = optimize_sales_script(demo_raw, "比亚迪")

        print(f"\n✅ 优化后话术:\n{result['optimized_script']}")
        print(f"\n🎯 关键卖点:")
        for h in result["key_highlights"]:
            print(f"   • {h}")
        print(f"\n📌 下一步: {result['next_action']}")
        print(f"🎭 语气: {result['tone_analysis']}")

        save_to_history(result, "比亚迪", demo_raw)

    except Exception as e:
        print(f"❌ 优化失败: {e}")

    # 示例 2：你自己输入
    print("\n" + "=" * 60)
    print("【实战练习】输入你自己的话术")
    print("=" * 60)

    user_raw = input("\n粘贴你的原始话术（直接回车跳过）:\n").strip()

    if user_raw:
        client = input("客户名称: ").strip() or "未命名客户"
        print("\n正在优化...")

        try:
            result = optimize_sales_script(user_raw, client)

            print(f"\n✅ 优化后话术:\n{result['optimized_script']}")
            print(f"\n🎯 关键卖点:")
            for h in result["key_highlights"]:
                print(f"   • {h}")
            print(f"\n📌 下一步: {result['next_action']}")
            print(f"🎭 语气: {result['tone_analysis']}")

            save_to_history(result, client, user_raw)

        except Exception as e:
            print(f"❌ 优化失败: {e}")
    else:
        print("已跳过实战练习。下次运行时可以输入你自己的话术。")

    print("\n" + "=" * 60)
    print("完成！建议把优化后的话术保存到你的 CRM 或备忘录中。")
    print("=" * 60)
