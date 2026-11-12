# -*- coding: utf-8 -*-
"""
模块⑥ 业务结论与数据导出（对应老师模块「6. 业务结论与数据导出」）
=================================================================
1. build_conclusions()：根据当前数据自动生成业务结论（数字全部现算，不是写死的）
2. export_all()：把清洗数据、分析表、图表、结论导出到 outputs/
"""
from __future__ import annotations

import io
import os

import pandas as pd

AMOUNT = "消费金额"
CATEGORY = "商品类别"
CITY = "城市"
MONTH = "月份"


def _pct(part: float, total: float) -> str:
    return f"{(part / total * 100):.1f}%" if total else "0.0%"


def build_conclusions(df: pd.DataFrame, kpi: dict, tables: dict[str, pd.DataFrame]) -> list[dict]:
    """根据数据动态生成 6~8 条业务结论。"""
    if df.empty:
        return [{"标题": "暂无数据", "内容": "请先在左侧选择数据源。"}]

    total = float(df[AMOUNT].sum())
    conclusions: list[dict] = []

    # 1. 整体规模
    conclusions.append(
        {
            "标题": "1. 整体经营规模",
            "内容": (
                f"数据共 **{kpi['订单数']}** 笔订单、**{kpi['客户数']}** 位客户，"
                f"总销售额 **{kpi['总销售额(元)']:,.2f} 元**，客单价 **{kpi['客单价(元)']:,.2f} 元**，"
                f"平均评分 **{kpi['平均评分']}** 分。"
            ),
        }
    )

    # 2. 品类表现
    cat_table = tables.get("分组-商品类别", pd.DataFrame())
    if not cat_table.empty:
        top = cat_table.iloc[0]
        bottom = cat_table.iloc[-1]
        top2_share = float(cat_table["消费占比(%)"].head(2).sum())
        if float(top["消费占比(%)"]) >= 35:
            judge = f"销售明显向 **{top[CATEGORY]}** 集中，属于典型的头部品类驱动。"
        elif top2_share >= 60:
            judge = f"前两大品类（{top[CATEGORY]} 等）合计占 {top2_share:.1f}%，是主要营收来源。"
        else:
            judge = "各品类销售额分布相对均衡，没有绝对主力，适合做全品类运营。"
        conclusions.append(
            {
                "标题": "2. 品类表现",
                "内容": (
                    f"**{top[CATEGORY]}** 销售额最高，为 {top['消费总额']:,.2f} 元、占比 {top['消费占比(%)']}%；"
                    f"贡献最低的是 **{bottom[CATEGORY]}**（占比 {bottom['消费占比(%)']}%）。{judge}"
                ),
            }
        )

    # 3. 客群画像
    gender_table = tables.get("分组-性别", pd.DataFrame())
    age_table = tables.get("分组-年龄段", pd.DataFrame())
    gender_text = ""
    if not gender_table.empty:
        g = gender_table.iloc[0]
        gender_text = f"性别上 **{g['性别']}** 贡献最高（{g['消费占比(%)']}%）；"
    age_text = ""
    if not age_table.empty:
        a = age_table.iloc[0]
        age_text = f"年龄上 **{a['年龄段']}** 是主力客群（{a['消费占比(%)']}%）。"
    if gender_text or age_text:
        conclusions.append({"标题": "3. 核心客群画像", "内容": gender_text + age_text})

    # 4. 地域分布
    city_table = tables.get("分组-城市", pd.DataFrame())
    if not city_table.empty:
        top3 = city_table.head(3)
        names = "、".join(top3[CITY].astype(str).tolist())
        top10_share = float(city_table["消费占比(%)"].head(10).sum())
        total_cities = len(city_table)
        if top10_share >= 50:
            judge = f"TOP10 城市合计占 {top10_share:.1f}%，重点市场集中，可优先在这些城市投放和备货。"
        else:
            judge = (
                f"数据中共有 {total_cities} 个城市，TOP10 城市合计仅占 {top10_share:.1f}%，"
                f"城市分布分散、长尾明显，建议先选头部城市做试点再复制。"
            )
        conclusions.append(
            {
                "标题": "4. 地域分布",
                "内容": f"消费额 TOP3 城市为 **{names}**。{judge}",
            }
        )

    # 5. 时间规律
    month_table = tables.get("月度趋势", pd.DataFrame())
    if not month_table.empty and len(month_table) >= 2:
        peak = month_table.loc[month_table["销售额"].idxmax()]
        low = month_table.loc[month_table["销售额"].idxmin()]
        conclusions.append(
            {
                "标题": "5. 时间规律",
                "内容": (
                    f"销售峰值出现在 **{peak[MONTH]}**（{peak['销售额']:,.2f} 元），"
                    f"低谷在 **{low[MONTH]}**（{low['销售额']:,.2f} 元）；"
                    f"旺季需提前备货，淡季可通过促销拉动。"
                ),
            }
        )

    # 6. 折扣效果
    discount_table = tables.get("折扣分析", pd.DataFrame())
    if not discount_table.empty and len(discount_table) >= 2 and "是否使用折扣" in discount_table.columns:
        used = discount_table[discount_table["是否使用折扣"].astype(str).eq("是")]
        not_used = discount_table[discount_table["是否使用折扣"].astype(str).eq("否")]
        if not used.empty and not not_used.empty:
            a = float(used["客单价"].iloc[0])
            b = float(not_used["客单价"].iloc[0])
            diff = (a - b) / b * 100 if b else 0
            trend = "高于" if diff >= 0 else "低于"
            conclusions.append(
                {
                    "标题": "6. 折扣效果",
                    "内容": (
                        f"使用折扣的订单客单价 **{a:,.2f} 元**，{trend}未使用折扣的订单（{b:,.2f} 元）"
                        f"{abs(diff):.1f}%；折扣使用率 {kpi['折扣使用率(%)']}%，"
                        f"可用于判断让利是否换来了更高客单。"
                    ),
                }
            )

    # 7. 复购
    repeat_table = tables.get("复购分析", pd.DataFrame())
    if not repeat_table.empty and "是否复购" in repeat_table.columns:
        conclusions.append(
            {
                "标题": "7. 复购情况",
                "内容": f"当前样本的复购订单占比 **{kpi['复购订单占比(%)']}%**，"
                f"当前筛选范围内购买至少两次的客户占 **{kpi['客户复购率(%)']}%**。",
            }
        )

    # 8. 行动建议
    conclusions.append(
        {
            "标题": "8. 经营建议",
            "内容": (
                "① 主推高贡献品类并补齐长尾品类；"
                "② 针对主力客群做客单价提升（搭配套餐/满减）；"
                "③ 重点城市加大投放，低贡献城市做本地化促销；"
                "④ 用折扣和会员体系提升复购率。"
            ),
        }
    )
    return conclusions


def conclusions_to_markdown(conclusions: list[dict], kpi: dict | None = None) -> str:
    """把结论拼成 Markdown（可直接贴进实训报告）。"""
    lines = ["# 沃尔玛客户购买行为分析 —— 业务结论", ""]
    if kpi:
        lines.append("## 核心指标")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("| --- | --- |")
        for key, value in kpi.items():
            lines.append(f"| {key} | {value} |")
        lines.append("")
    lines.append("## 业务结论")
    lines.append("")
    for item in conclusions:
        lines.append(f"### {item['标题']}")
        lines.append("")
        lines.append(item["内容"])
        lines.append("")
    return "\n".join(lines)


def excel_bytes(df, kpi, tables):
    """回读 Excel，核对明细、看板指标、导出指标和品类汇总。"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"指标": list(kpi.keys()), "数值": list(kpi.values())}).to_excel(
            writer, sheet_name="KPI", index=False
        )
        for name, table in tables.items():
            if table is None or table.empty:
                continue
            sheet = str(name)[:31]
            table.to_excel(writer, sheet_name=sheet)
    buffer.seek(0)
    with pd.ExcelFile(buffer, engine="openpyxl") as book:
        exported = book.parse("KPI").set_index("指标")["数值"]
        groups = book.parse("分组-商品类别") if not df.empty else tables["分组-商品类别"]
    totals = [df[AMOUNT].sum(), kpi["总销售额(元)"], exported["总销售额(元)"], groups["消费总额"].sum()]
    counts = [len(df), kpi["订单数"], exported["订单数"], groups["订单数"].sum()]
    if len({round(float(value) * 100) for value in totals}) != 1 or len(set(counts)) != 1:
        raise ValueError("明细、看板与 Excel 的金额或订单数不一致，请检查汇总规则。")
    return buffer.getvalue()


def export_all(
    df_clean: pd.DataFrame,
    kpi: dict,
    tables: dict[str, pd.DataFrame],
    conclusions: list[dict],
    out_dir: str,
) -> list[str]:
    """导出全部结果到 out_dir，返回生成的文件列表。"""
    workbook = excel_bytes(df_clean, kpi, tables)
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []

    # 1) 清洗后的明细数据
    csv_path = os.path.join(out_dir, "cleaned_walmart_data.csv")
    df_clean.to_csv(csv_path, index=False, encoding="utf-8-sig")
    written.append(csv_path)

    # 2) 分析表（多个 sheet 的 Excel）
    xlsx_path = os.path.join(out_dir, "analysis_tables.xlsx")
    with open(xlsx_path, "wb") as stream:
        stream.write(workbook)
    written.append(xlsx_path)

    # 3) 结论
    md_path = os.path.join(out_dir, "business_conclusions.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(conclusions_to_markdown(conclusions, kpi))
    written.append(md_path)

    return written
