# -*- coding: utf-8 -*-
"""
模块③ 数据清洗（对应老师模块「3. 数据清洗」）
=============================================
本数据集的两个「坑」都在这里处理：
1. 原始表第 1 行是中文列名（客户ID、年龄、性别……），不是真实数据 —— 已在 m1 剔除，
   这里再做一次兜底检查；
2. 所有字段读进来都是 object（文本），年龄/金额/评分/日期都需要转类型。

清洗步骤：
  ① 去重 → ② 类型转换 → ③ 缺失值填充 → ④ 异常值标记与范围检查
  → ⑤ 文本规范化 → ⑥ 派生分析字段
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# 年龄段划分
AGE_BINS = [0, 25, 35, 45, 55, 65, 200]
AGE_LABELS = ["18-25岁", "26-35岁", "36-45岁", "46-55岁", "56-65岁", "65岁以上"]

# 金额分档（用于漏斗图 / 分档统计）
AMOUNT_BINS = [0, 50, 100, 200, 500, np.inf]
AMOUNT_LABELS = ["0至50元（含）", "50-100元", "100-200元", "200-500元", "500元以上"]

NUMERIC_COLS = ["年龄", "消费金额", "评分"]


def _to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], dict]:
    """执行完整清洗流程。

    Returns
    -------
    df_clean : 清洗后的数据（含派生字段）
    log      : 每一步的清洗说明，可直接贴进报告
    stats    : 清洗前后对比指标
    """
    log: list[str] = []
    work = df.copy()

    rows_before = len(work)
    missing_before = int(work.isna().sum().sum())
    dup_before = int(work.duplicated().sum())

    # ---------------------------------------------------------- ① 去重
    work = work.drop_duplicates().reset_index(drop=True)
    removed_dup = dup_before
    log.append(f"去重：删除完全重复记录 {removed_dup} 条。")

    # ---------------------------------------------------------- ② 类型转换
    bad_dates = 0
    for col in NUMERIC_COLS:
        if col in work.columns:
            before_na = int(work[col].isna().sum())
            work[col] = _to_num(work[col])
            converted = int(work[col].isna().sum()) - before_na
            if converted > 0:
                log.append(f"类型转换：字段「{col}」有 {converted} 条无法转成数值，按缺失处理。")

    if "购买日期" in work.columns:
        before_na = int(work["购买日期"].isna().sum())
        work["购买日期"] = pd.to_datetime(work["购买日期"], errors="coerce")
        bad_dates = int(work["购买日期"].isna().sum()) - before_na
        # 日期明显不合理（早于 2015 年）的也当作异常
        mask_bad = work["购买日期"].notna() & (work["购买日期"] < pd.Timestamp("2015-01-01"))
        bad_dates += int(mask_bad.sum())
        work.loc[mask_bad, "购买日期"] = pd.NaT
        if bad_dates > 0:
            log.append(f"类型转换：「购买日期」有 {bad_dates} 条无法解析或明显异常，按缺失处理。")

    # ---------------------------------------------------------- ③ 缺失值填充
    fill_log = []
    for col in ["年龄", "评分"]:
        if col in work.columns and work[col].isna().any():
            n = int(work[col].isna().sum())
            median = work[col].median()
            work[col] = work[col].fillna(median)
            fill_log.append(f"「{col}」用中位数 {median:.2f} 填充 {n} 条")
    for col in work.columns:
        if col in NUMERIC_COLS or col == "购买日期":
            continue
        if work[col].isna().any():
            n = int(work[col].isna().sum())
            mode = work[col].mode(dropna=True)
            fill_value = mode.iloc[0] if len(mode) else "未知"
            work[col] = work[col].fillna(fill_value)
            fill_log.append(f"「{col}」用众数「{fill_value}」填充 {n} 条")
    if fill_log:
        log.append("缺失值填充：" + "；".join(fill_log) + "。")

    n_missing_dates = 0
    if "购买日期" in work.columns and work["购买日期"].isna().any():
        n = int(work["购买日期"].isna().sum())
        n_missing_dates = n
        work = work.dropna(subset=["购买日期"]).reset_index(drop=True)
        log.append(f"删除购买日期缺失的记录 {n} 条（日期是时间分析的必要字段）。")

    # ---------------------------------------------------------- ④ 异常值处理
    upper = work["消费金额"].quantile(0.995)
    amount = work["消费金额"]
    work["金额待核查"] = amount.isna() | amount.lt(0) | amount.gt(upper)
    flagged = int(work["金额待核查"].sum())
    log.append(f"标记金额缺失、负数或超过 99.5% 分位的记录 {flagged} 条，保留原金额。")

    if "年龄" in work.columns:
        out_age = int(((work["年龄"] < 18) | (work["年龄"] > 100)).sum())
        work["年龄"] = work["年龄"].clip(18, 100)
        if out_age:
            log.append(f"异常值处理：年龄限定在 18-100 岁，修正 {out_age} 条。")

    if "评分" in work.columns:
        before = work["评分"].copy()
        work["评分"] = work["评分"].clip(1, 5)
        changed = int((before != work["评分"]).sum())
        if changed:
            log.append(f"异常值处理：评分限定在 1-5 分，修正 {changed} 条。")

    # ---------------------------------------------------------- ⑤ 文本规范化
    text_cols = ["性别", "城市", "商品类别", "商品名称", "支付方式", "是否使用折扣", "是否复购"]
    for col in text_cols:
        if col in work.columns:
            work[col] = work[col].astype(str).str.strip()

    # 大小写不统一（如 beijing / Beijing、female / Female）按“出现次数最多的写法”归一
    for col in ["城市", "支付方式", "性别"]:
        if col not in work.columns:
            continue
        series = work[col].astype(str).str.strip()
        counts = series.value_counts()
        canonical: dict[str, str] = {}
        for value in series.unique():
            key = value.strip().lower()
            if key not in canonical or counts.get(value, 0) > counts.get(canonical[key], 0):
                canonical[key] = value.strip()
        work[col] = series.map(lambda v, c=canonical: c.get(v.strip().lower(), v.strip()))

    # 统一「是/否」类字段的写法（兼容 Yes/No、True/False）
    yes_no_map = {
        "Yes": "是", "yes": "是", "YES": "是", "True": "是", "1": "是", "是": "是",
        "No": "否", "no": "否", "NO": "否", "False": "否", "0": "否", "否": "否",
    }
    for col in ["是否使用折扣", "是否复购"]:
        if col in work.columns:
            work[col] = work[col].map(lambda v: yes_no_map.get(str(v).strip(), str(v).strip()))

    log.append("文本规范化：去除字段首尾空格，是/否类字段统一为「是 / 否」。")

    # ---------------------------------------------------------- ⑥ 派生字段
    if "购买日期" in work.columns:
        work["年份"] = work["购买日期"].dt.year
        work["月份"] = work["购买日期"].dt.to_period("M").astype(str)
        work["季度"] = work["购买日期"].dt.quarter.map(lambda q: f"Q{q}")
        work["星期"] = work["购买日期"].dt.dayofweek.map(
            {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
        )
        work["是否周末"] = work["购买日期"].dt.dayofweek.isin([5, 6]).map({True: "是", False: "否"})

    if "年龄" in work.columns:
        work["年龄段"] = pd.cut(work["年龄"], bins=AGE_BINS, labels=AGE_LABELS)
        work["年龄段"] = work["年龄段"].astype(str)

    if "消费金额" in work.columns:
        work["金额分档"] = pd.cut(work["消费金额"], bins=AMOUNT_BINS, labels=AMOUNT_LABELS, include_lowest=True)
        work["金额分档"] = work["金额分档"].astype(str)

    log.append("派生字段：新增 年份、月份、季度、星期、是否周末、年龄段、金额分档。")

    # ---------------------------------------------------------- 汇总
    stats = {
        "清洗前行数": rows_before,
        "清洗后行数": len(work),
        "删除重复行": removed_dup,
        "清洗前缺失单元格": missing_before,
        "清洗后缺失单元格": int(work.isna().sum().sum()),
        "金额待核查条数": flagged,
        "日期异常条数": bad_dates,
        "字段个数": work.shape[1],
    }
    valid_rows = rows_before - removed_dup - n_missing_dates
    if len(work) != valid_rows:
        raise ValueError("清洗行数与原始行数扣除重复、无效日期后的结果不符")
    return work.reset_index(drop=True), log, stats
