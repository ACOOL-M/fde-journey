# Week 2 Day 4: 读写 CSV 文件——让周报能接你的真实数据
# 场景: 把昨天的周报生成器升级成"读文件版"
# 目标: 你以后 Excel 改数据 → Python 自动出周报 → 不用改代码

import pandas as pd

# ---------- 第 1 关: 写 CSV (先造一份"你的销售数据") ----------

data = [
    {"日期": "2026-09-01", "客户": "腾讯云", "动作": "电话", "金额": 120000},
    {"日期": "2026-09-01", "客户": " 腾讯云 ", "动作": "演示", "金额": 0},
    {"日期": "2026-09-02", "客户": "拼多多", "动作": "电话", "金额": 80000},
    {"日期": "2026-09-02", "客户": "拼多多", "动作": "报价", "金额": 0},
    {"日期": "2026-09-02", "客户": "美的", "动作": "电话", "金额": 95000},
    {"日期": "2026-09-03", "客户": "BYD", "动作": "拜访", "金额": 150000},
    {"日期": "2026-09-03", "客户": "byd", "动作": "报价", "金额": 0},
    {"日期": "2026-09-03", "客户": "顺丰", "动作": "电话", "金额": 60000},
]

df = pd.DataFrame(data)

# 保存成 CSV 文件 (以后你打开 Excel 直接改这个文件)
df.to_csv("sales_data.csv", index=False, encoding="utf-8-sig")
print("✅ 已创建 sales_data.csv")

# ---------- 第 2 关: 读 CSV (打开文件看看长什么样) ----------

print()
print("===== 读取 CSV 文件 =====")
loaded = pd.read_csv("sales_data.csv")
print(loaded)
print()
print(f"文件共有 {len(loaded)} 行, {len(loaded.columns)} 列")

# ---------- 第 3 关: 改完 CSV 再读一遍 (这才是真正的用法) ----------

# 模拟: 你打开 Excel 改了一笔数据(腾讯云演示变成成交了)
# 现在重新读进来, 金额变成 120000 而不是 0
print()
print("===== 假设你在 Excel 里改了数据, 重新读取 =====")
loaded2 = pd.read_csv("sales_data.csv")
loaded2["客户"] = loaded2["客户"].str.strip().str.lower()
name_map = {"byd": "比亚迪"}
loaded2["客户"] = loaded2["客户"].replace(name_map)

# 按日期+客户汇总
print()
print("===== 按客户汇总 =====")
summary = loaded2.groupby("客户").agg(
    跟进次数=("客户", "count"),
    意向金额=("金额", "sum"),
)
print(summary)

# 把汇总结果也存成 CSV (发给老板之前可以直接看)
summary.to_csv("summary.csv", encoding="utf-8-sig")
print()
print("✅ 汇总结果已保存到 summary.csv")
print("   打开方式: 右键 → 打开方式 → Excel")
