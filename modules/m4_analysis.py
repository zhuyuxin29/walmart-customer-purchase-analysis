# -*- coding: utf-8 -*-
"""
模块④ 数据分析与聚合（对应老师模块「4. 数据分析与聚合」）
==========================================================
核心指标 + 分组聚合 + 透视表 + 交叉分析，全部基于清洗后的数据。
"""
from __future__ import annotations

import pandas as pd

AMOUNT = "消费金额"
CATEGORY = "商品类别"
CITY = "城市"
GENDER = "性别"
AGE_GROUP = "年龄段"
MONTH = "月份"


def _rate(part: float, total: float) -> float:
    return round(part / total * 100, 2) if total else 0.0


def kpis(df: pd.DataFrame) -> dict:
    """看板顶部 KPI。"""
    total_amount = float(df[AMOUNT].sum())
    orders = int(len(df))
    customers = int(df["客户ID"].nunique()) if "客户ID" in df.columns else orders

    repeat_rate = 0.0
    if "是否复购" in df.columns:
        yes = df["是否复购"].astype(str).eq("是").sum()
        repeat_rate = _rate(yes, orders)

    discount_rate = 0.0
    if "是否使用折扣" in df.columns:
        yes = df["是否使用折扣"].astype(str).eq("是").sum()
        discount_rate = _rate(yes, orders)

    return {
        "总销售额(元)": round(total_amount, 2),
        "订单数": orders,
        "客户数": customers,
        "客单价(元)": round(total_amount / orders, 2) if orders else 0.0,
        "复购订单占比(%)": repeat_rate,
        "客户复购率(%)": _rate(df["客户ID"].value_counts().gt(1).sum(), customers)
        if "客户ID" in df.columns else 0.0,
        "折扣使用率(%)": discount_rate,
        "平均评分": round(float(df["评分"].mean()), 2) if "评分" in df.columns else 0.0,
    }


def group_summary(df: pd.DataFrame, by: str, top: int | None = None) -> pd.DataFrame:
    """按某个维度聚合：消费总额 / 订单数 / 客单价 / 客户数 / 平均评分。"""
    if by not in df.columns:
        return pd.DataFrame()
    table = (
        df.groupby(by, as_index=False)
        .agg(
            消费总额=(AMOUNT, "sum"),
            订单数=(AMOUNT, "size"),
            平均评分=("评分", "mean") if "评分" in df.columns else (AMOUNT, "size"),
        )
    )
    if "客户ID" in df.columns:
        customers = df.groupby(by)["客户ID"].nunique().rename("客户数").reset_index()
        table = table.merge(customers, on=by, how="left")
    table["客单价"] = (table["消费总额"] / table["订单数"]).round(2)
    table["消费占比(%)"] = (table["消费总额"] / df[AMOUNT].sum() * 100).round(2)
    table["消费总额"] = table["消费总额"].round(2)
    table["平均评分"] = table["平均评分"].round(2)
    table = table.sort_values("消费总额", ascending=False).reset_index(drop=True)
    return table.head(top) if top else table


def pivot_city_category(df: pd.DataFrame, top_cities: int = 15) -> pd.DataFrame:
    """城市 × 商品类别 的销售额透视表（老师要求的 pivot_table）。"""
    top = (
        df.groupby(CITY)[AMOUNT].sum().sort_values(ascending=False).head(top_cities).index
    )
    sub = df[df[CITY].isin(top)]
    pivot = pd.pivot_table(
        sub,
        values=AMOUNT,
        index=CITY,
        columns=CATEGORY,
        aggfunc="sum",
        fill_value=0,
    ).round(2)
    pivot["合计"] = pivot.sum(axis=1).round(2)
    return pivot.loc[pivot["合计"].sort_values(ascending=False).index]


def pivot_month_category(df: pd.DataFrame) -> pd.DataFrame:
    """月份 × 商品类别 的销售额透视表。"""
    return pd.pivot_table(
        df,
        values=AMOUNT,
        index=MONTH,
        columns=CATEGORY,
        aggfunc="sum",
        fill_value=0,
    ).round(2)


def discount_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """折扣使用 vs 未使用 的效果对比。"""
    table = group_summary(df, "是否使用折扣")
    return table


def repeat_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """复购客户 vs 新客户 的消费能力对比。"""
    return group_summary(df, "是否复购")


def gender_age_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """年龄段 × 性别 的销售额交叉表。"""
    return pd.pivot_table(
        df, values=AMOUNT, index=AGE_GROUP, columns=GENDER, aggfunc="sum", fill_value=0
    ).round(2)


def payment_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """支付方式偏好。"""
    return group_summary(df, "支付方式")


def top_products(df: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    """热销商品 TOP N。"""
    return group_summary(df, "商品名称", top=top)


def weekday_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """按星期聚合，看工作日 / 周末的消费规律。"""
    if "星期" not in df.columns:
        return pd.DataFrame()
    order = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    table = group_summary(df, "星期")
    table["星期"] = pd.Categorical(table["星期"], categories=order, ordered=True)
    return table.sort_values("星期").reset_index(drop=True)


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """月度趋势（订单数 + 销售额 + 环比）。"""
    table = (
        df.groupby(MONTH, as_index=False)
        .agg(订单数=(AMOUNT, "size"), 销售额=(AMOUNT, "sum"))
        .sort_values(MONTH)
    )
    table["销售额"] = table["销售额"].round(2)
    if not table.empty:
        months = pd.period_range(table[MONTH].iloc[0], table[MONTH].iloc[-1], freq="M")
        table = table.set_index(MONTH).reindex(months.astype(str), fill_value=0)
        table = table.rename_axis(MONTH).reset_index()
    previous = table["销售额"].shift()
    table["环比(%)"] = (table["销售额"].div(previous.where(previous.ne(0))).sub(1) * 100).round(2)
    return table


def all_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """一次性产出模块④要用的全部分析表（导出 / 报告用）。"""
    return {
        "分组-商品类别": group_summary(df, CATEGORY),
        "分组-城市": group_summary(df, CITY),
        "分组-性别": group_summary(df, GENDER),
        "分组-年龄段": group_summary(df, AGE_GROUP),
        "分组-支付方式": payment_analysis(df),
        "城市×类别透视": pivot_city_category(df),
        "月份×类别透视": pivot_month_category(df),
        "折扣分析": discount_analysis(df),
        "复购分析": repeat_analysis(df),
        "年龄段×性别": gender_age_matrix(df),
        "月度趋势": monthly_trend(df),
        "星期分析": weekday_analysis(df),
        "热销商品TOP10": top_products(df),
    }
