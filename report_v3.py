# -*- coding: utf-8 -*-
# 周报生成器 V3: 智能版
# 相比 V2 新增两大能力:
#   1. 异常检测: 金额异常大的数据自动拦截预警 (try/except + 条件判断)
#   2. 超期提醒: 超过 3 天没跟进的客户自动标红提醒
# 数据还是来自 sales_data.csv, 改文件不改代码

import pandas as pd
from datetime import datetime, timedelta

# ============================================
# 第 1 步: 读数据 + 容错
# ============================================
try:
    df = pd.read_csv("sales_data.csv", encoding="utf-8-sig")
    print(f"读取成功, 共 {len(df)} 条记录")
except FileNotFoundError:
    print("找不到 sales_data.csv, 先跑 python week2-day4.py 生成它")
    exit()

# ============================================
# 第 2 步: 清洗 (老三样: strip / lower / 统一名称)
# ============================================
df["客户"] = df["客户"].str.strip()
df["金额"] = pd.to_numeric(df["金额"], errors="coerce")  # 脏数据变 NaN 而不是崩溃
df["日期"] = pd.to_datetime(df["日期"], errors="coerce")

name_map = {"byd": "比亚迪", "tencent": "腾讯云"}
df["客户"] = df["客户"].str.lower().replace(name_map)

# ============================================
# 第 3 步: 异常检测 (今天的核心新功能)
# ============================================
print()
print("=" * 40)
print("异常数据检测")
print("=" * 40)

MAX_AMOUNT = 10000000  # 单笔意向超过 1000 万视为可疑

abnormal = df[df["金额"] > MAX_AMOUNT]
if len(abnormal) > 0:
    for _, row in abnormal.iterrows():
        print(f"[拦截] {row['日期'].date()} {row['客户']}: "
              f"金额 {row['金额']:,.0f} 元异常偏大, 已从周报剔除, 请核对是否多打了零")
    df = df[df["金额"] <= MAX_AMOUNT]

invalid = df[df["金额"].isna()]
if len(invalid) > 0:
    print(f"[跳过] {len(invalid)} 条金额无法识别的记录被剔除")

df = df.dropna(subset=["金额"])
print(f"检测完成: 保留 {len(df)} 条有效记录")

# ============================================
# 第 4 步: 超期未跟进提醒 (第二个新功能)
# ============================================
print()
print("=" * 40)
print("超期未跟进提醒")
print("=" * 40)

today = datetime(2026, 9, 4)  # 假设今天是周五
ALERT_DAYS = 3

last_contact = df.groupby("客户")["日期"].max()
for customer, last_date in last_contact.items():
    days_idle = (today - last_date).days
    if days_idle >= ALERT_DAYS:
        print(f"[超期] {customer}: 已 {days_idle} 天未跟进 (最后跟进 {last_date.date()}), 今天必须联系")
    else:
        print(f"[正常] {customer}: {days_idle} 天前刚跟进过")

# ============================================
# 第 5 步: 生成周报 (V2 的老功能 + 分级)
# ============================================
print()
print("=" * 40)
print("           本周销售周报 V3 (自动生成)")
print("=" * 40)

summary = df.groupby("客户").agg(
    跟进次数=("客户", "count"),
    意向金额=("金额", "sum"),
)
summary = summary.sort_values("意向金额", ascending=False)

total_amount = df["金额"].sum()
total_actions = len(df)
top_customer = summary["意向金额"].idxmax()

print(summary.to_string())
print("-" * 40)
print(f"本周跟进客户: {summary.shape[0]} 家")
print(f"总跟进动作: {total_actions} 次")
print(f"有效意向金额: {total_amount:,.0f} 元")
print(f"意向金额最高客户: {top_customer}")

# 客户分级 (Day 5 第 1 关的知识点直接用上)
print()
print("客户分级建议:")
for customer, row in summary.iterrows():
    amount = row["意向金额"]
    if amount >= 100000:
        level = "A 级 - 重点攻坚"
    elif amount >= 50000:
        level = "B 级 - 保持节奏"
    else:
        level = "C 级 - 长期培育"
    print(f"  {customer}: 意向 {amount:>10,.0f} 元 -> {level}")

print("=" * 40)
print("周报生成完毕")
print("=" * 40)

# 存档
summary.to_csv("周报_智能版.csv", encoding="utf-8-sig")
print("明细已保存: 周报_智能版.csv")
