# -*- coding: utf-8 -*-
"""
模块② 数据探索 EDA（对应老师模块「2. 数据探索（EDA）」）
=========================================================
输出：数据规模、字段类型、缺失情况、重复值、描述统计、类别频数、时间跨度
所有函数都只做计算，不涉及界面，方便单独运行 / 写进报告。
"""
from __future__ import annotations

import pandas as pd

# 数值列 / 类别列（清洗前也适用）
NUMERIC_COLS = ["年龄", "消费金额", "评分"]
CATEGORY_COLS = ["性别", "城市", "商品类别", "支付方式", "是否使用折扣", "是否复购"]


def overview(df: pd.DataFrame) -> dict:
    """整体概况：行数、列数、缺失总数、重复行数、客户数、时间范围。"""
    result = {
        "样本行数": int(df.shape[0]),
        "字段个数": int(df.shape[1]),
        "缺失单元格总数": int(df.isna().sum().sum()),
        "重复行数": int(df.duplicated().sum()),
    }
    if "客户ID" in df.columns:
        result["客户数"] = int(df["客户ID"].nunique())
    dates = pd.to_datetime(df.get("购买日期"), errors="coerce")
    if dates.notna().any():
        result["最早购买日期"] = str(dates.min().date())
        result["最晚购买日期"] = str(dates.max().date())
    return result


def dtypes_table(df: pd.DataFrame) -> pd.DataFrame:
    """字段类型表（报告的「数据概况」小节可以直接贴这张表）。"""
    table = pd.DataFrame(
        {
            "字段": df.columns,
            "数据类型": [str(t) for t in df.dtypes],
            "非空数量": [int(df[c].notna().sum()) for c in df.columns],
        }
    )
    table["缺失数量"] = len(df) - table["非空数量"]
    table["缺失率"] = (table["缺失数量"] / max(len(df), 1) * 100).round(2).astype(str) + "%"
    table["唯一值个数"] = [int(df[c].nunique(dropna=True)) for c in df.columns]
    return table.reset_index(drop=True)


def missing_table(df: pd.DataFrame) -> pd.DataFrame:
    """缺失值明细（只保留有缺失的字段）。"""
    miss = df.isna().sum()
    table = pd.DataFrame(
        {
            "字段": miss.index,
            "缺失数量": miss.values,
            "缺失率(%)": (miss.values / max(len(df), 1) * 100).round(2),
        }
    )
    return table[table["缺失数量"] > 0].reset_index(drop=True)


def describe_table(df: pd.DataFrame) -> pd.DataFrame:
    """数值字段描述统计。"""
    cols = [c for c in NUMERIC_COLS if c in df.columns]
    if not cols:
        return pd.DataFrame()
    data = df[cols].apply(pd.to_numeric, errors="coerce")
    desc = data.describe().T
    desc.index.name = "字段"
    keep = [c for c in ["count", "mean", "std", "min", "25%", "50%", "75%", "max"] if c in desc.columns]
    desc = desc[keep].round(2)
    desc.columns = ["样本数", "均值", "标准差", "最小值", "下四分位", "中位数", "上四分位", "最大值"][: len(keep)]
    return desc.reset_index()


def category_freq(df: pd.DataFrame, column: str, top: int | None = None) -> pd.DataFrame:
    """某个类别字段的频数分布（次数 + 占比）。"""
    if column not in df.columns:
        return pd.DataFrame()
    counts = df[column].astype(str).value_counts(dropna=False)
    if top:
        counts = counts.head(top)
    table = counts.rename_axis(column).reset_index(name="出现次数")
    table["占比(%)"] = (table["出现次数"] / max(len(df), 1) * 100).round(2)
    return table


def time_trend(df: pd.DataFrame) -> pd.DataFrame:
    """按月统计订单数与销售额（EDA 阶段用，清洗模块会再生成正式字段）。"""
    if "购买日期" not in df.columns:
        return pd.DataFrame()
    work = df.copy()
    work["购买日期"] = pd.to_datetime(work["购买日期"], errors="coerce")
    work = work.dropna(subset=["购买日期"])
    work["月份"] = work["购买日期"].dt.to_period("M").astype(str)
    work["消费金额"] = pd.to_numeric(work["消费金额"], errors="coerce")
    table = (
        work.groupby("月份", as_index=False)
        .agg(订单数=("消费金额", "size"), 销售额=("消费金额", "sum"))
        .sort_values("月份")
    )
    table["销售额"] = table["销售额"].round(2)
    return table


def value_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """关键数值字段的取值区间，用于发现异常/占位值。"""
    rows = []
    for col in NUMERIC_COLS:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        rows.append(
            {
                "字段": col,
                "最小值": None if s.dropna().empty else round(float(s.min()), 2),
                "最大值": None if s.dropna().empty else round(float(s.max()), 2),
                "为0/负数的条数": int((s <= 0).sum()),
                "无法转数值的条数": int(s.isna().sum() - df[col].isna().sum()),
            }
        )
    return pd.DataFrame(rows)
