# -*- coding: utf-8 -*-
# Week 2 Day 5: 条件判断升级 + 异常处理
# 主题: elif 多分支 / and or 组合条件 / try except 容错
# 场景: 全部用销售跟进的真实判断逻辑

# ============================================
# 第 1 关: elif 多分支 - 客户分级
# ============================================
# 销售按意向金额给客户分级, 不同级别不同策略
# if / elif / else 是从上往下逐个判断, 命中一个就停

def grade_customer(amount):
    if amount >= 100000:
        return "A 级客户 (重点攻坚, 每周必跟)"
    elif amount >= 50000:
        return "B 级客户 (保持节奏, 两周一次)"
    elif amount > 0:
        return "C 级客户 (养着, 逢节日问候)"
    else:
        return "无效线索 (金额为 0, 判断是被刷掉的)"

print("=" * 40)
print("第 1 关: 客户自动分级")
print("=" * 40)

test_amounts = [120000, 80000, 30000, 0]
for a in test_amounts:
    print(f"意向金额 {a:>7} 元 -> {grade_customer(a)}")

# ============================================
# 第 2 关: and / or 组合条件 - 跟进优先级
# ============================================
# 现实判断往往不止一个维度:
#   金额大 或者 是老客户 -> 今天必须跟进
#   金额大 并且 已成交 -> 请老板陪访

print()
print("=" * 40)
print("第 2 关: 组合条件判断")
print("=" * 40)

deals = [
    {"客户": "腾讯云", "金额": 120000, "已成交": True},
    {"客户": "拼多多", "金额": 80000, "已成交": False},
    {"客户": "美的", "金额": 20000, "已成交": True},
]

for d in deals:
    # or: 两边只要有一个成立就是 True
    if d["金额"] >= 100000 or d["已成交"]:
        print(f"{d['客户']}: 今天必须跟进")
    # and: 两边都成立才是 True
    if d["金额"] >= 100000 and d["已成交"]:
        print(f"{d['客户']}: 金额大且已成交, 请老板陪访争取增购")

# not: 把 True 变 False, False 变 True
has_quote = False
if not has_quote:
    print("美的: 还没报过价, 本周补一份报价单")

# ============================================
# 第 3 关: try / except - 让程序崩不掉
# ============================================
# 真实数据一定有脏东西: 文本里混着数字、文件读不到、用户乱填
# 没有容错的程序遇到一条脏数据就整个崩溃, 后面的全不跑了
# try: 试着跑这段代码
# except: 出错了就执行这里, 程序继续活下去

print()
print("=" * 40)
print("第 3 关: 异常处理")
print("=" * 40)

# 场景: 财务发来的金额列, 有的填了数字, 有的填了"待定"
raw_amounts = ["120000", "待定", "80000", "", "95000"]

print("没有容错时 (演示崩溃):")
try:
    for x in raw_amounts:
        value = int(x)  # int("待定") 会直接抛 ValueError
        print(f"  转换成功: {value}")
except ValueError as e:
    print(f"  程序崩了, 错误是: {e}")
    print("  注意: 后面 3 条数据全没处理, 这就是没容错的代价")

print()
print("加了容错后 (脏数据跳过, 好数据照跑):")
total = 0
skipped = 0
for x in raw_amounts:
    try:
        value = int(x)
        total = total + value
    except ValueError:
        skipped = skipped + 1
        print(f"  跳过脏数据: '{x}' 不是数字")

print(f"有效金额合计: {total} 元, 跳过脏数据 {skipped} 条")

# ============================================
# 第 4 关: 防御式编程 - 异常金额检测
# ============================================
# 昨天你的 sales_data.csv 里有一条 15 亿的 BYD
# 明显是手抖多打了几个零. 程序要能自己发现它

print()
print("=" * 40)
print("第 4 关: 异常金额检测")
print("=" * 40)

def check_amount(amount):
    if amount <= 0:
        return False, "金额必须大于 0"
    if amount > 10000000:  # 超过 1000 万就预警
        return False, "金额异常偏大, 请人工核对"
    return True, "正常"

for amount in [120000, 0, 1500000000, 60000]:
    ok, msg = check_amount(amount)
    flag = "通过" if ok else "拦截"
    print(f"金额 {amount:>12} -> [{flag}] {msg}")

print()
print("=" * 40)
print("全部 4 关跑通! 接下来跑 report_v3.py 看智能周报")
print("=" * 40)
