# -*- coding: utf-8 -*-
"""
沃尔玛客户购买行为数据分析与可视化
=====================================
基于 Streamlit + pyecharts 的分析看板，包含经营概览、深入分析、
数据质量、报告导出四个视图。

运行方式：
    python -m streamlit run app.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# 保证从任意目录启动都能 import 到 modules
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules import m2_eda, m3_clean, m4_analysis, m5_charts, m6_export  # noqa: E402
from modules.m1_load import default_data_path, load_raw, load_dictionary  # noqa: E402

OUT_DIR = os.path.join(ROOT, "outputs")
AMOUNT = "消费金额"

st.set_page_config(
    page_title="沃尔玛客户购买行为数据分析与可视化",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------- 工具函数
@st.cache_data(show_spinner="正在读取并清洗数据…")
def prepare():
    """读取数据 + 清洗，带缓存，避免每次交互都重跑。"""
    raw = load_raw()
    clean_df, clean_log, clean_stats = m3_clean.clean(raw)
    return raw, clean_df, clean_log, clean_stats


@st.cache_data(show_spinner=False)
def get_dictionary():
    return load_dictionary()


def show_chart(chart, height: int = 380) -> None:
    """把 pyecharts 图表嵌入 Streamlit；单张图渲染出错时给出提示，不影响整页。"""
    try:
        components.html(chart.render_embed(), height=height, scrolling=False)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"图表渲染失败：{exc}")


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """侧边栏筛选，返回筛选后的数据。"""
    st.sidebar.markdown("#### 筛选订单")
    result = df.copy()

    for col in ["性别", "商品类别", "年龄段", "支付方式"]:
        if col in result.columns:
            options = sorted(result[col].dropna().astype(str).unique().tolist())
            chosen = st.sidebar.multiselect(col, options, default=[], placeholder="全部", key=f"flt_{col}")
            if chosen:
                result = result[result[col].astype(str).isin(chosen)]

    if "城市" in result.columns:
        city_amount = result.groupby("城市")[AMOUNT].sum().sort_values(ascending=False)
        city_options = city_amount.index.astype(str).tolist()
        chosen_cities = st.sidebar.multiselect(
            "城市（不选=全部）", city_options, default=[], placeholder="全部", key="flt_city"
        )
        if chosen_cities:
            result = result[result["城市"].astype(str).isin(chosen_cities)]

    if "购买日期" in result.columns:
        dates = result["购买日期"].dropna()
        if len(dates) and dates.min() < dates.max():
            start, end = dates.min().date(), dates.max().date()
            rng = st.sidebar.date_input(
                "购买日期范围", value=(start, end), min_value=start, max_value=end, key="flt_date"
            )
            if isinstance(rng, tuple) and len(rng) == 2:
                result = result[
                    (result["购买日期"].dt.date >= rng[0]) & (result["购买日期"].dt.date <= rng[1])
                ]

    st.sidebar.caption(f"当前筛选：{len(result):,} 条 / 共 {len(df):,} 条")
    return result


# ---------------------------------------------------------------- 主体
STYLE = """
<style>
[data-testid="stAppViewContainer"],.stMain {background:#f5f6f2}
section[data-testid="stSidebar"] {background:#e9eee8;border-right:1px solid #d4ddd5}
.block-container {max-width:1480px;padding-top:3.2rem}
[data-testid="stMetric"] {background:white;border:1px solid #d8dfd8;border-radius:12px;padding:14px 18px}
[data-testid="stMetricValue"] {font-variant-numeric:tabular-nums;color:#183e35}
.retail-hero {background:linear-gradient(110deg,#123f35,#215846);color:#fff;border-radius:16px;padding:24px 30px;margin-bottom:6px}
.retail-hero h1 {color:white;font-size:clamp(26px,3vw,42px);margin:3px 0 8px;padding:0;line-height:1.3}
.retail-hero small {color:#c4dfcd;letter-spacing:.08em}
.retail-hero p {color:#e0ece2;margin:0;font-size:14px}
</style>
"""


def render_overview(df, kpi, tables):
    dates = df["购买日期"]
    st.markdown(
        f'<div class="retail-hero"><small>沃尔玛客户购买行为 · 模拟订单</small>'
        f'<h1>沃尔玛客户购买行为数据分析与可视化</h1><p>{dates.min():%Y.%m.%d} — {dates.max():%Y.%m.%d}'
        f'　｜　当前样本 {len(df):,} 笔订单</p></div>', unsafe_allow_html=True
    )
    cards = st.columns(4)
    cards[0].metric("销售额（万元）", f"{kpi['总销售额(元)']/10000:,.2f}")
    cards[1].metric("订单数", f"{len(df):,}")
    cards[2].metric("客户数", f"{kpi['客户数']:,}")
    cards[3].metric("客单价（元）", f"{kpi['客单价(元)']:,.2f}")

    trend, categories = tables["月度趋势"], tables["分组-商品类别"]
    left, right = st.columns([3, 2])
    with left.container(border=True):
        st.subheader("月度销售趋势")
        month_data = trend.assign(销售额万元=trend["销售额"].div(10000))
        st.vega_lite_chart(month_data, {
            "height":230, "mark":{"type":"line","color":"#147459","strokeWidth":3,"point":True},
            "encoding":{"x":{"field":"月份","type":"ordinal","axis":{"title":None,"labelOverlap":True}},
                        "y":{"field":"销售额万元","type":"quantitative","title":"万元"},
                        "tooltip":[{"field":"月份"},{"field":"销售额","type":"quantitative","format":",.2f"},{"field":"订单数","type":"quantitative"}]}
        }, use_container_width=True)
    with right.container(border=True):
        st.subheader("品类销售贡献")
        st.vega_lite_chart(categories, {
            "height":230,"mark":{"type":"bar","color":"#528574","cornerRadiusEnd":4},
            "encoding":{"y":{"field":"商品类别","type":"nominal","sort":"-x","title":None},
                        "x":{"field":"消费占比(%)","type":"quantitative","title":"销售额占比（%）"},
                        "tooltip":[{"field":"商品类别"},{"field":"消费总额","type":"quantitative","format":",.2f"},{"field":"消费占比(%)","type":"quantitative"}]}
        }, use_container_width=True)
    st.subheader("客户与订单")
    for col, (label, key, unit) in zip(st.columns(4), [
        ("客户复购率","客户复购率(%)","%"), ("复购订单占比","复购订单占比(%)","%"),
        ("折扣使用率","折扣使用率(%)","%"), ("平均评分","平均评分"," / 5")]):
        col.metric(label, f"{kpi[key]:.2f}{unit}")
    st.caption("客户复购率按当前筛选内至少下单两次的客户计算。复购订单占比按订单的历史复购标记计算。")


def main() -> None:
    st.markdown(STYLE, unsafe_allow_html=True)
    st.sidebar.title("零售分析台")
    page = st.sidebar.radio("分析视图", ["经营概览", "深入分析", "数据质量", "报告导出"])
    st.sidebar.divider()
    with st.spinner("正在加载数据…"):
        raw_df, clean_df, clean_log, clean_stats = prepare()

    filtered = sidebar_filters(clean_df)

    if filtered.empty:
        st.info("当前条件下没有订单，请调整左侧筛选。")
        return
    kpi = m4_analysis.kpis(filtered)
    tables = m4_analysis.all_tables(filtered)
    if page == "经营概览":
        render_overview(filtered, kpi, tables)
        return

    st.title(page)
    if page == "数据质量":
        st.caption("查看完整源表的字段、异常和清洗记录。")
        tab1, tab2, tab3 = st.tabs(["数据来源", "探索统计", "清洗记录"])
        # ---------------- 数据加载 ----------------
        with tab1:
            st.subheader("数据加载")
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("**数据概况**")
                st.write(
                    {
                        "数据来源": "课程模拟零售订单（Walmart_customer_purchases）",
                        "原始行数": int(raw_df.shape[0]),
                        "字段个数": int(raw_df.shape[1]),
                        "清洗后行数": int(clean_df.shape[0]),
                    }
                )
                st.markdown("**数据字典（字段说明 sheet）**")
                st.dataframe(
                    pd.DataFrame(get_dictionary(), columns=["字段", "说明"]),
                    use_container_width=True,
                    hide_index=True,
                )
            with c2:
                st.markdown("**原始数据预览（前 20 行）**")
                st.dataframe(raw_df.head(20), use_container_width=True)

        # ---------------- 数据探索 ----------------
        with tab2:
            st.subheader("数据探索 EDA")
            overview = m2_eda.overview(raw_df)
            cols = st.columns(len(overview))
            for col, (key, value) in zip(cols, overview.items()):
                col.metric(key, value)

            left, right = st.columns(2)
            with left:
                st.markdown("**字段类型 / 缺失 / 唯一值**")
                st.dataframe(m2_eda.dtypes_table(raw_df), use_container_width=True, hide_index=True)
            with right:
                st.markdown("**缺失值明细**")
                miss = m2_eda.missing_table(raw_df)
                if miss.empty:
                    st.success("原始数据没有缺失值 ✅")
                else:
                    st.dataframe(miss, use_container_width=True, hide_index=True)
                st.markdown("**数值字段描述统计**")
                st.dataframe(m2_eda.describe_table(raw_df), use_container_width=True, hide_index=True)

            st.markdown("**类别字段分布**")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.dataframe(
                    m2_eda.category_freq(raw_df, "商品类别"), use_container_width=True, hide_index=True
                )
            with c2:
                st.dataframe(m2_eda.category_freq(raw_df, "性别"), use_container_width=True, hide_index=True)
            with c3:
                st.dataframe(
                    m2_eda.category_freq(raw_df, "支付方式"), use_container_width=True, hide_index=True
                )

            st.markdown("**时间趋势（原始数据）**")
            trend = m2_eda.time_trend(raw_df)
            st.dataframe(trend, use_container_width=True, hide_index=True)

        # ---------------- 数据清洗 ----------------
        with tab3:
            st.subheader("数据清洗")
            st.markdown("**清洗步骤日志**")
            for item in clean_log:
                st.markdown(f"- {item}")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**清洗前后对比**")
                st.dataframe(
                    pd.DataFrame(
                        {"指标": list(clean_stats.keys()), "数值": list(clean_stats.values())}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            with c2:
                st.markdown("**清洗后数据预览**")
                st.dataframe(clean_df.head(15), use_container_width=True)

            st.markdown("**清洗后缺失值检查**")
            miss = m2_eda.missing_table(clean_df)
            if miss.empty:
                st.success("清洗后无缺失值 ✅")
            else:
                st.dataframe(miss, use_container_width=True, hide_index=True)

    if page == "深入分析":
        st.caption(f"当前筛选包含 {len(filtered):,} 笔订单")
        tab4, tab5 = st.tabs(["分组与交叉分析", "图表浏览"])
        # ---------------- 分析与聚合 ----------------
        with tab4:
            st.subheader("数据分析与聚合")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**各商品类别汇总**")
                st.dataframe(tables["分组-商品类别"], use_container_width=True, hide_index=True)
                st.markdown("**城市汇总（TOP 15）**")
                st.dataframe(tables["分组-城市"].head(15), use_container_width=True, hide_index=True)
                st.markdown("**折扣效果对比**")
                st.dataframe(tables["折扣分析"], use_container_width=True, hide_index=True)
            with c2:
                st.markdown("**性别 / 年龄段汇总**")
                st.dataframe(tables["分组-性别"], use_container_width=True, hide_index=True)
                st.dataframe(tables["分组-年龄段"], use_container_width=True, hide_index=True)
                st.markdown("**复购分析**")
                st.dataframe(tables["复购分析"], use_container_width=True, hide_index=True)
                st.markdown("**支付方式分析**")
                st.dataframe(tables["分组-支付方式"], use_container_width=True, hide_index=True)

            st.markdown("**城市 × 商品类别 透视表**")
            st.dataframe(tables["城市×类别透视"], use_container_width=True)
            st.markdown("**月份 × 商品类别 透视表**")
            st.dataframe(tables["月份×类别透视"], use_container_width=True)

        # ---------------- 可视化看板 ----------------
        with tab5:
            st.subheader("数据可视化（综合看板）")
            st.caption("共 12 张图：品类、趋势、性别、支付方式、年龄-金额、箱线、热力、城市 TOP、金额分档、词云、年龄段、折扣对比。")

            c1, c2 = st.columns(2)
            with c1:
                show_chart(m5_charts.chart_category_bar(filtered), 380)
            with c2:
                show_chart(m5_charts.chart_monthly_line(filtered), 380)

            c1, c2 = st.columns(2)
            with c1:
                show_chart(m5_charts.chart_gender_pie(filtered), 380)
            with c2:
                show_chart(m5_charts.chart_payment_rose(filtered), 380)

            c1, c2 = st.columns(2)
            with c1:
                show_chart(m5_charts.chart_scatter_age_amount(filtered), 380)
            with c2:
                show_chart(m5_charts.chart_boxplot_category(filtered), 380)

            c1, c2 = st.columns(2)
            with c1:
                show_chart(m5_charts.chart_heatmap_city_month(filtered), 430)
            with c2:
                show_chart(m5_charts.chart_top_cities(filtered), 430)

            c1, c2 = st.columns(2)
            with c1:
                show_chart(m5_charts.chart_amount_funnel(filtered), 400)
            with c2:
                show_chart(m5_charts.chart_wordcloud_products(filtered), 400)

            c1, c2 = st.columns(2)
            with c1:
                show_chart(m5_charts.chart_gender_age_bar(filtered), 380)
            with c2:
                show_chart(m5_charts.chart_discount_bar(filtered), 380)

    # ---------------- 业务结论与导出 ----------------
    if page == "报告导出":
        st.caption(f"导出范围为当前筛选的 {len(filtered):,} 笔订单")
        workbook = m6_export.excel_bytes(filtered, kpi, tables)
        conclusions = m6_export.build_conclusions(filtered, kpi, tables)
        st.markdown("**导出结果**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "⬇ 清洗后明细数据（CSV）",
                data=filtered.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                file_name="cleaned_walmart_data.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "⬇ 分析表（Excel）",
                data=workbook,
                file_name="analysis_tables.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with c3:
            st.download_button(
                "⬇ 业务结论（Markdown）",
                data=m6_export.conclusions_to_markdown(conclusions, kpi).encode("utf-8"),
                file_name="business_conclusions.md",
                mime="text/markdown",
                use_container_width=True,
            )
        if st.button("📂 一键写入 outputs/ 文件夹"):
            written = m6_export.export_all(filtered, kpi, tables, conclusions, OUT_DIR)
            st.success("已导出：\n\n" + "\n".join(f"- {os.path.basename(w)}" for w in written))

        st.divider()
        st.subheader("分析结论")
        for item in conclusions:
            st.markdown(f"#### {item['标题']}")
            st.markdown(item["内容"])


if __name__ == "__main__":
    main()

