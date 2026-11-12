# -*- coding: utf-8 -*-
"""
一键跑通 6 个模块（命令行版，不依赖 Streamlit）
=============================================
作用：
  1. 验证数据读取 / 清洗 / 分析 / 导出整条链路是否正常
  2. 生成 outputs/ 里的清洗数据、分析表、业务结论（写报告直接用）

运行：
    .venv\\Scripts\\python.exe run_pipeline.py
    .venv\\Scripts\\python.exe run_pipeline.py                  # 生成 outputs 报表
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules import m2_eda, m3_clean, m4_analysis, m5_charts, m6_export  # noqa: E402
from modules.m1_load import load_raw  # noqa: E402

OUT_DIR = os.path.join(ROOT, "outputs")


def main() -> None:
    parser = argparse.ArgumentParser(description="沃尔玛客户购买行为分析 - 全流程脚本")
    parser.add_argument("--no-export", action="store_true", help="只跑分析，不导出文件")
    args = parser.parse_args()

    print("=" * 60)
    print("模块① 数据加载")
    print("=" * 60)
    raw = load_raw()
    print(f"数据源：沃尔玛客户购买行为数据集，原始数据 {raw.shape[0]} 行 × {raw.shape[1]} 列")
    print("字段：", list(raw.columns))

    print()
    print("=" * 60)
    print("模块② 数据探索 EDA")
    print("=" * 60)
    for key, value in m2_eda.overview(raw).items():
        print(f"  {key}: {value}")
    print("\n  缺失值：")
    miss = m2_eda.missing_table(raw)
    print("  无缺失" if miss.empty else miss.to_string(index=False))

    print()
    print("=" * 60)
    print("模块③ 数据清洗")
    print("=" * 60)
    clean_df, clean_log, clean_stats = m3_clean.clean(raw)
    for item in clean_log:
        print("  -", item)
    print("\n  清洗前后：")
    for key, value in clean_stats.items():
        print(f"  {key}: {value}")

    print()
    print("=" * 60)
    print("模块④ 数据分析与聚合")
    print("=" * 60)
    kpi = m4_analysis.kpis(clean_df)
    for key, value in kpi.items():
        print(f"  {key}: {value}")
    tables = m4_analysis.all_tables(clean_df)
    print("\n  商品类别汇总：")
    print(tables["分组-商品类别"].to_string(index=False))

    print()
    print("=" * 60)
    print("模块⑤ 数据可视化（图表生成检查）")
    print("=" * 60)
    chart_builders = {
        "品类销售额": m5_charts.chart_category_bar,
        "月度趋势": m5_charts.chart_monthly_line,
        "性别占比": m5_charts.chart_gender_pie,
        "支付方式": m5_charts.chart_payment_rose,
        "年龄金额散点": m5_charts.chart_scatter_age_amount,
        "品类金额箱线": m5_charts.chart_boxplot_category,
        "城市月份热力": m5_charts.chart_heatmap_city_month,
        "城市TOP10": m5_charts.chart_top_cities,
        "金额分档漏斗": m5_charts.chart_amount_funnel,
        "热销商品词云": m5_charts.chart_wordcloud_products,
        "年龄段性别": m5_charts.chart_gender_age_bar,
        "折扣对比": m5_charts.chart_discount_bar,
    }
    charts = {}
    for name, builder in chart_builders.items():
        chart = builder(clean_df)
        charts[name] = chart
        print(f"  [OK] {name} 生成成功")

    print()
    print("=" * 60)
    print("模块⑥ 业务结论与数据导出")
    print("=" * 60)
    conclusions = m6_export.build_conclusions(clean_df, kpi, tables)
    for item in conclusions:
        text = item["内容"].replace("**", "")
        print(f"  {item['标题']}")
        print(f"      {text}")

    if not args.no_export:
        written = m6_export.export_all(clean_df, kpi, tables, conclusions, OUT_DIR)
        # 额外把图表导出成 html，便于放进报告 / 答辩演示
        chart_dir = os.path.join(OUT_DIR, "charts")
        os.makedirs(chart_dir, exist_ok=True)
        for name, chart in charts.items():
            path = os.path.join(chart_dir, f"{name}.html")
            chart.render(path)
            written.append(path)
        print("\n  已导出文件：")
        for path in written:
            print(f"  - {path}")

    print("\n全部模块运行完成。")


if __name__ == "__main__":
    main()
