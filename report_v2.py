# 小项目③: 周报生成器 V2 — 从 CSV 读取真实数据
# 你的 Excel 改了数据, 这里不需要改代码, 跑一下周报自动更新

import pandas as pd

print("========================================")
print("     销售周报生成器 V2 (CSV 版)")
print("========================================")
print()

# 第 1 步: 读文件
df = pd.read_csv("sales_data.csv")
print(f"📄 读取 sales_data.csv: {len(df)} 条原始记录")

# 第 2 步: 清洗
df["客户"] = df["客户"].str.strip().str.lower()
df["客户"] = df["客户"].replace({"byd": "比亚迪"})

# 第 3 步: 汇总
summary = df.groupby("客户").agg(
    跟进次数=("客户", "count"),
    意向金额=("金额", "sum"),
)

# 第 4 步: 输出周报
print()
print("----------- 本周核心数据 -----------")
print(f"跟进客户数: {df['客户'].nunique()} 家")
print(f"总跟进次数: {len(df)} 次")
print(f"意向金额合计: {df['金额'].sum():,} 元")
top = df.groupby("客户")["金额"].sum().idxmax()
print(f"意向最高客户: {top}")
print()
print("----------- 按客户明细 -----------")
print(summary.to_string())
print()
print("====================================")
print("💡 想要更新周报? 打开 sales_data.csv 修改")
print("   然后重新运行: python report_v2.py")
print("====================================")

# 第 5 步: 把周报也存一份 CSV, 方便发给老板
summary.to_csv("周报_客户汇总.csv", encoding="utf-8-sig")
print()
print("✅ 周报明细已保存到: 周报_客户汇总.csv")
