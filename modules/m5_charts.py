# -*- coding: utf-8 -*-
"""
模块⑤ 数据可视化
==================
使用 pyecharts 绘制图表，Streamlit 通过 st.components.html 嵌入网页，形成综合看板。
每个函数返回一个 pyecharts 图表对象，数据均来自清洗后的 DataFrame。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .m3_clean import AMOUNT_LABELS
from .m4_analysis import monthly_trend

from pyecharts import options as opts
from pyecharts.charts import Bar, Boxplot, Funnel, HeatMap, Line, Pie, Scatter, WordCloud
from pyecharts.globals import ThemeType

AMOUNT = "消费金额"
PALETTE = ["#5B8FF9", "#5AD8A6", "#F6BD16", "#E8684A", "#6DC8EC",
           "#9270CA", "#FF9D4D", "#269A99", "#FF99C3", "#5D7092"]


def _init(title: str, height: str = "360px") -> opts.InitOpts:
    return opts.InitOpts(theme=ThemeType.LIGHT, width="100%", height=height)


def _empty(title: str) -> Bar:
    chart = Bar(init_opts=_init(title))
    chart.add_xaxis(["暂无数据"])
    chart.add_yaxis("", [0])
    chart.set_global_opts(title_opts=opts.TitleOpts(title=title))
    return chart


# ---------------------------------------------------------------- ① 品类销售额
def chart_category_bar(df: pd.DataFrame) -> Bar:
    """各商品类别销售额（横向柱状图）。"""
    if df.empty or "商品类别" not in df.columns:
        return _empty("各商品类别销售额")
    # 金额转换为万元，避免坐标刻度过于拥挤
    table = df.groupby("商品类别", as_index=False)[AMOUNT].sum()
    table["销售额(万元)"] = table[AMOUNT] / 10000
    table = table.sort_values("销售额(万元)", ascending=True)
    chart = Bar(init_opts=_init("各商品类别销售额（万元）"))
    chart.add_xaxis(table["商品类别"].astype(str).tolist())
    chart.add_yaxis(
        "销售额(万元)",
        [round(float(v), 2) for v in table["销售额(万元)"]],
        category_gap="45%",
    )
    chart.reversal_axis()
    chart.set_series_opts(label_opts=opts.LabelOpts(position="right", formatter="{c}"))
    chart.set_global_opts(
        xaxis_opts=opts.AxisOpts(name="销售额(万元)", axislabel_opts=opts.LabelOpts(formatter="{value}")),
        yaxis_opts=opts.AxisOpts(name="商品类别"),
        legend_opts=opts.LegendOpts(is_show=False),
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="shadow"),
    )
    return chart


# ---------------------------------------------------------------- ② 月度趋势
def chart_monthly_line(df: pd.DataFrame) -> Line:
    """月度销售额 + 订单数（双 Y 轴折线图）。"""
    if df.empty or "月份" not in df.columns:
        return _empty("月度销售趋势")
    table = monthly_trend(df)
    chart = Line(init_opts=_init("月度销售趋势（销售额 / 订单数）"))
    chart.add_xaxis(table["月份"].astype(str).tolist())
    chart.add_yaxis(
        "销售额(万元)",
        [round(float(v) / 10000, 2) for v in table["销售额"]],
        is_smooth=True,
        symbol="circle",
        symbol_size=6,
        label_opts=opts.LabelOpts(is_show=False),
        linestyle_opts=opts.LineStyleOpts(width=3),
    )
    chart.add_yaxis(
        "订单数",
        [int(v) for v in table["订单数"]],
        yaxis_index=1,
        is_smooth=True,
        symbol="circle",
        symbol_size=6,
        label_opts=opts.LabelOpts(is_show=False),
        linestyle_opts=opts.LineStyleOpts(width=3, type_="dashed"),
    )
    chart.extend_axis(yaxis=opts.AxisOpts(name="订单数", position="right"))
    chart.set_global_opts(
        xaxis_opts=opts.AxisOpts(name="月份", axislabel_opts=opts.LabelOpts(rotate=45)),
        yaxis_opts=opts.AxisOpts(name="销售额(万元)"),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        legend_opts=opts.LegendOpts(pos_top="5%"),
    )
    return chart


# ---------------------------------------------------------------- ③ 性别占比
def chart_gender_pie(df: pd.DataFrame) -> Pie:
    """性别消费占比（环形饼图）。"""
    if df.empty or "性别" not in df.columns:
        return _empty("性别消费占比")
    table = df.groupby("性别", as_index=False)[AMOUNT].sum().sort_values(AMOUNT, ascending=False)
    data = [(str(k), round(float(v), 2)) for k, v in zip(table["性别"], table[AMOUNT])]
    chart = Pie(init_opts=_init("不同性别的消费占比"))
    chart.add(
        "",
        data,
        radius=["40%", "68%"],
        center=["50%", "55%"],
        rosetype=None,
        label_opts=opts.LabelOpts(formatter="{b}\n{d}%"),
    )
    chart.set_colors(PALETTE)
    chart.set_global_opts(
        title_opts=opts.TitleOpts(title="不同性别的消费占比"),
        legend_opts=opts.LegendOpts(orient="vertical", pos_left="2%", pos_top="15%"),
        tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{b}<br/>消费额：{c} 元<br/>占比：{d}%"),
    )
    return chart


# ---------------------------------------------------------------- ④ 支付方式
def chart_payment_rose(df: pd.DataFrame) -> Pie:
    """支付方式偏好（南丁格尔玫瑰图）。"""
    if df.empty or "支付方式" not in df.columns:
        return _empty("支付方式偏好")
    table = df.groupby("支付方式", as_index=False)[AMOUNT].sum().sort_values(AMOUNT, ascending=False)
    data = [(str(k), round(float(v), 2)) for k, v in zip(table["支付方式"], table[AMOUNT])]
    chart = Pie(init_opts=_init("支付方式偏好"))
    chart.add(
        "",
        data,
        radius=["18%", "58%"],
        center=["50%", "48%"],
        rosetype="area",
        label_opts=opts.LabelOpts(
            position="outside",
            formatter="{b}: {d}%",
            font_size=11,
        ),
        label_line_opts=opts.PieLabelLineOpts(length=12, length_2=12),
    )
    chart.set_colors(PALETTE)
    chart.set_global_opts(
        title_opts=opts.TitleOpts(title="各支付方式消费额（玫瑰图）"),
        # 图例置于底部，避免遮挡图表标签
        legend_opts=opts.LegendOpts(
            orient="horizontal", pos_bottom="0%", pos_left="center", item_gap=14
        ),
        tooltip_opts=opts.TooltipOpts(trigger="item"),
    )
    return chart


# ---------------------------------------------------------------- ⑤ 年龄-金额散点
def chart_scatter_age_amount(df: pd.DataFrame, sample: int = 600) -> Scatter:
    """年龄 vs 消费金额散点图（看主力客群和消费力）。"""
    if df.empty or "年龄" not in df.columns:
        return _empty("年龄与消费金额关系")
    work = df[[ "年龄", AMOUNT, "商品类别"]].dropna()
    if len(work) > sample:
        work = work.sample(sample, random_state=42)
    chart = Scatter(init_opts=_init("年龄与消费金额关系（抽样）"))
    # Scatter 会自动把 x 轴值与 y 值组合为 [x, y]，因此 y 轴只传入金额一列
    chart.add_xaxis([int(v) for v in work["年龄"]])
    chart.add_yaxis(
        "消费金额",
        [round(float(v), 2) for v in work[AMOUNT]],
        symbol_size=7,
        label_opts=opts.LabelOpts(is_show=False),
    )
    chart.set_global_opts(
        title_opts=opts.TitleOpts(title="年龄与消费金额关系"),
        xaxis_opts=opts.AxisOpts(name="年龄", type_="value", splitline_opts=opts.SplitLineOpts(is_show=False)),
        yaxis_opts=opts.AxisOpts(name="消费金额(元)"),
        tooltip_opts=opts.TooltipOpts(formatter="年龄 {c0}<br/>金额 {c1} 元"),
        legend_opts=opts.LegendOpts(is_show=False),
    )
    return chart


# ---------------------------------------------------------------- ⑥ 品类金额箱线图
def chart_boxplot_category(df: pd.DataFrame) -> Boxplot:
    """各品类消费金额分布（箱线图，看离散程度/异常）。"""
    if df.empty or "商品类别" not in df.columns:
        return _empty("各品类消费金额分布")
    cats, data = [], []
    for cat, group in df.groupby("商品类别"):
        values = pd.to_numeric(group[AMOUNT], errors="coerce").dropna()
        if values.empty:
            continue
        q1, q2, q3 = np.percentile(values, [25, 50, 75])
        cats.append(str(cat))
        data.append([round(float(values.min()), 2), round(float(q1), 2), round(float(q2), 2),
                     round(float(q3), 2), round(float(values.max()), 2)])
    chart = Boxplot(init_opts=_init("各品类消费金额分布"))
    chart.add_xaxis(cats)
    chart.add_yaxis("消费金额", data)
    chart.set_global_opts(
        title_opts=opts.TitleOpts(title="各品类消费金额箱线图"),
        xaxis_opts=opts.AxisOpts(name="商品类别", axislabel_opts=opts.LabelOpts(rotate=20)),
        yaxis_opts=opts.AxisOpts(name="消费金额(元)"),
        legend_opts=opts.LegendOpts(is_show=False),
        tooltip_opts=opts.TooltipOpts(trigger="item"),
    )
    return chart


# ---------------------------------------------------------------- ⑦ 城市热力图
def chart_heatmap_city_month(df: pd.DataFrame, top_cities: int = 10) -> HeatMap:
    """城市 × 月份 销售额热力图。"""
    if df.empty or "城市" not in df.columns or "月份" not in df.columns:
        return _empty("城市-月份销售热力")
    top = df.groupby("城市")[AMOUNT].sum().sort_values(ascending=False).head(top_cities).index.tolist()
    sub = df[df["城市"].isin(top)].copy()
    months = sorted(sub["月份"].astype(str).unique().tolist())
    cities = top
    pivot = (
        sub.pivot_table(index="城市", columns="月份", values=AMOUNT, aggfunc="sum", fill_value=0)
        .reindex(index=cities, columns=months)
        .fillna(0)
    )
    values = []
    for i, city in enumerate(cities):
        for j, month in enumerate(months):
            values.append([j, i, round(float(pivot.loc[city, month]), 2)])
    vmax = max((v[2] for v in values), default=1)
    chart = HeatMap(init_opts=_init("城市 × 月份 销售额热力图", height="420px"))
    chart.add_xaxis(months)
    chart.add_yaxis("销售额", cities, values, label_opts=opts.LabelOpts(is_show=False))
    chart.set_global_opts(
        title_opts=opts.TitleOpts(title="城市 × 月份 销售额热力图"),
        xaxis_opts=opts.AxisOpts(name="月份", axislabel_opts=opts.LabelOpts(rotate=45)),
        yaxis_opts=opts.AxisOpts(name="城市"),
        visualmap_opts=opts.VisualMapOpts(
            min_=0, max_=vmax, is_calculable=True, orient="horizontal",
            pos_left="center", pos_bottom="0",
        ),
        tooltip_opts=opts.TooltipOpts(formatter="{b}<br/>销售额：{c} 元"),
    )
    return chart


# ---------------------------------------------------------------- ⑧ 城市 TOP 10
def chart_top_cities(df: pd.DataFrame, top: int = 10) -> Bar:
    """消费额 TOP 城市。"""
    if df.empty or "城市" not in df.columns:
        return _empty("城市消费额 TOP10")
    table = df.groupby("城市", as_index=False)[AMOUNT].sum()
    table["销售额(万元)"] = table[AMOUNT] / 10000
    table = table.sort_values("销售额(万元)", ascending=True).tail(top)
    chart = Bar(init_opts=_init("城市消费额 TOP10"))
    chart.add_xaxis(table["城市"].astype(str).tolist())
    chart.add_yaxis(
        "销售额(万元)", [round(float(v), 2) for v in table["销售额(万元)"]], category_gap="45%"
    )
    chart.reversal_axis()
    chart.set_series_opts(label_opts=opts.LabelOpts(position="right", formatter="{c}"))
    chart.set_global_opts(
        xaxis_opts=opts.AxisOpts(name="销售额(万元)", axislabel_opts=opts.LabelOpts(formatter="{value}")),
        yaxis_opts=opts.AxisOpts(name="城市"),
        legend_opts=opts.LegendOpts(is_show=False),
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="shadow"),
    )
    return chart


# ---------------------------------------------------------------- ⑨ 金额分档漏斗
def chart_amount_funnel(df: pd.DataFrame) -> Funnel:
    """订单金额分档漏斗图。"""
    if df.empty or "金额分档" not in df.columns:
        return _empty("订单金额分档")
    # 使用短标签，避免漏斗内部标签重叠
    short_names = {
        "0至50元（含）": "0-50元",
        "50-100元": "50-100元",
        "100-200元": "100-200元",
        "200-500元": "200-500元",
        "500元以上": "500元+",
    }
    order = [short_names.get(k, k) for k in AMOUNT_LABELS]
    counts = df["金额分档"].astype(str).value_counts()
    data = []
    for key, short in zip(AMOUNT_LABELS, order):
        value = int(counts.get(key, 0))
        if value > 0:
            data.append((short, value))
    data.sort(key=lambda item: item[1], reverse=True)

    chart = Funnel(init_opts=_init("订单金额分档"))
    chart.add(
        "订单数",
        data,
        sort_="descending",
        gap=2,
        label_opts=opts.LabelOpts(position="inside", formatter="{b}: {c}"),
    )
    chart.set_colors(PALETTE)
    chart.set_global_opts(
        title_opts=opts.TitleOpts(title="订单金额分档漏斗图"),
        legend_opts=opts.LegendOpts(is_show=False),
        tooltip_opts=opts.TooltipOpts(trigger="item", formatter="{b}<br/>订单数：{c}"),
    )
    return chart


# ---------------------------------------------------------------- ⑩ 商品词云
def chart_wordcloud_products(df: pd.DataFrame) -> WordCloud:
    """热销商品词云（按销量）。"""
    if df.empty or "商品名称" not in df.columns:
        return _empty("热销商品词云")
    counts = df["商品名称"].astype(str).value_counts().head(40)
    data = [(str(k), int(v)) for k, v in counts.items()]
    chart = WordCloud(init_opts=_init("热销商品词云", height="400px"))
    chart.add("热销商品", data, word_size_range=[14, 60], shape="circle")
    chart.set_global_opts(
        title_opts=opts.TitleOpts(title="热销商品词云（按销量）"),
        tooltip_opts=opts.TooltipOpts(formatter="{b}：{c} 单"),
    )
    return chart


# ---------------------------------------------------------------- ⑪ 性别×年龄段
def chart_gender_age_bar(df: pd.DataFrame) -> Bar:
    """年龄段 × 性别 销售额堆叠柱状图。"""
    if df.empty or "年龄段" not in df.columns:
        return _empty("年龄段 × 性别 销售额")
    order = ["18-25岁", "26-35岁", "36-45岁", "46-55岁", "56-65岁", "65岁以上"]
    pivot = df.pivot_table(index="年龄段", columns="性别", values=AMOUNT, aggfunc="sum", fill_value=0)
    pivot = pivot.reindex([a for a in order if a in pivot.index])
    chart = Bar(init_opts=_init("年龄段 × 性别 销售额"))
    chart.add_xaxis(pivot.index.astype(str).tolist())
    for gender in pivot.columns:
        chart.add_yaxis(
            str(gender),
            [round(float(v) / 10000, 2) for v in pivot[gender]],
            stack="stack1",
        )
    chart.set_colors(PALETTE)
    chart.set_global_opts(
        title_opts=opts.TitleOpts(title="不同年龄段-性别的销售额"),
        xaxis_opts=opts.AxisOpts(name="年龄段"),
        yaxis_opts=opts.AxisOpts(name="销售额(万元)"),
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="shadow"),
    )
    return chart


# ---------------------------------------------------------------- ⑫ 折扣效果
def chart_discount_bar(df: pd.DataFrame) -> Bar:
    """是否使用折扣的消费对比。"""
    if df.empty or "是否使用折扣" not in df.columns:
        return _empty("折扣效果对比")
    table = df.groupby("是否使用折扣", as_index=False)[AMOUNT].mean()
    chart = Bar(init_opts=_init("折扣效果对比"))
    chart.add_xaxis([str(v) for v in table["是否使用折扣"]])
    chart.add_yaxis("平均消费额", [round(float(v), 2) for v in table[AMOUNT]], category_gap="40%")
    chart.set_colors(PALETTE)
    chart.set_global_opts(
        title_opts=opts.TitleOpts(title="是否使用折扣的平均消费额对比"),
        xaxis_opts=opts.AxisOpts(name="是否使用折扣"),
        yaxis_opts=opts.AxisOpts(name="平均消费额(元)"),
        legend_opts=opts.LegendOpts(is_show=False),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
    )
    return chart
