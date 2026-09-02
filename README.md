# FDE 学习之旅 (fde-journey)

> 从零开始学 Python + 数据清洗 + 自动化周报生成，目标：转型 FDE（前沿部署工程师）

---

## 我是谁

B 端销售背景，正在卖 AI 办公产品（WorkBuddy），利用现有销售数据边学边练。12 个月计划，当前处于第 2 周。

---

## 项目总览

| # | 项目名 | 核心技能 | 解决的问题 |
|---|--------|---------|-----------|
| ① | 客户名单清洗器 (`clean.py`) | `strip()` / `lower()` / `set()` / `is_valid()` | 销售拿到的客户名单有重复、空格、大小写混乱，手工清洗 500 条要 1 小时，Python 3 秒 |
| ② | 销售周报生成器 (`report.py` → `report_v2.py` → `report_v3.py`) | pandas / CSV 读写 / groupby / 异常处理 | 脏跟进记录 → 自动清洗 → 按客户汇总 → 生成可直接发给老板的周报 |
| ③ | 智能周报 V3 (`report_v3.py`) | `try-except` / 条件判断 / 防御式编程 | 自动拦截异常数据（如 15 亿错填金额）、超期未跟进提醒、客户 A/B/C 分级 |

---

## 快速体验

```bash
# 1. 安装依赖
python -m pip install pandas

# 2. 跑客户名单清洗器
python clean.py
# 输出: 清洗前 11 条，清洗后 4 条

# 3. 跑智能周报生成器
python report_v3.py
# 输出: 异常拦截 + 超期提醒 + 周报正文 + 客户分级建议
```

---

## 技术栈

- **Python 3.x** — 唯一编程语言
- **pandas** — 表格数据处理（DataFrame = 代码里的 Excel）
- **Git + GitHub** — 代码版本管理与作品集存档
- **Cursor** — AI 增强型代码编辑器

---

## 学习路线图

| 周次 | 阶段 | 目标 |
|------|------|------|
| Week 1 | 环境 + 基础 | Python 语法、列表、循环、if/else、Git 全流程 |
| Week 2 | 数据处理 | pandas、CSV 读写、清洗、汇总、异常处理、周报自动化 ✅ |
| Week 3 | LLM 应用 | 调用 OpenAI/通义千问 API，做客户纪要自动总结 |
| Week 4 | RAG 入门 | 向量数据库 + 检索增强生成，做企业知识库问答 |
| Week 5+ | 项目实战 | 用真实销售数据搭建完整 POC，对接 CRM 系统 |

---

## 核心代码片段

### 客户名单清洗（3 秒 vs 1 小时）

```python
def clean_name(name):
    return name.strip().lower()

cleaned = [clean_name(n) for n in raw_names]
unique = list(set(cleaned))  # 自动去重
```

### 异常数据拦截（避免 15 亿污染周报）

```python
MAX_AMOUNT = 10_000_000  # 1000 万预警线
abnormal = df[df["金额"] > MAX_AMOUNT]
if len(abnormal) > 0:
    print(f"[拦截] 金额 {row['金额']} 异常偏大, 已从周报剔除")
    df = df[df["金额"] <= MAX_AMOUNT]
```

### 客户自动分级

```python
def grade(amount):
    if amount >= 100000:
        return "A 级 - 重点攻坚"
    elif amount >= 50000:
        return "B 级 - 保持节奏"
    else:
        return "C 级 - 长期培育"
```

---

## 数据来源

所有数据均为模拟销售场景数据（客户名来自公开企业信息），不涉及真实客户隐私。

---

## 联系方式

正在学习 FDE 转型路线，欢迎交流。
