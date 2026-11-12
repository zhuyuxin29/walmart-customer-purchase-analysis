# -*- coding: utf-8 -*-
"""
模块① 数据加载（对应老师模块「1. 自动生成模拟电商数据」）
=========================================================
本项目的做法：
- 数据是「按真实业务规律生成的模拟数据集」，已固化在 data/ 目录下（可复现，
  生成脚本见 tools/build_realistic_dataset.py，随机种子固定）；
- 本模块负责把它读进来、统一成中文列名，并处理原始表的两个坑：
  1) 第 1 行是「中文列名行」（客户ID、年龄……），不是真实数据，需要剔除；
  2) 表头是英文，需要映射成中文。
"""
from __future__ import annotations

import os

import pandas as pd

# ---------------------------------------------------------------- 常量配置
# 英文列名 -> 中文列名
COLUMN_MAP = {
    "Customer_ID": "客户ID",
    "Age": "年龄",
    "Gender": "性别",
    "City": "城市",
    "Category": "商品类别",
    "Product_Name": "商品名称",
    "Purchase_Date": "购买日期",
    "Purchase_Amount": "消费金额",
    "Payment_Method": "支付方式",
    "Discount_Applied": "是否使用折扣",
    "Rating": "评分",
    "Repeat_Customer": "是否复购",
}

DATA_FILENAME = "沃尔玛客户购买行为数据集.xlsx"

# xlsx 第二个 sheet「字段说明」缺失时的兜底数据字典
FIELD_DICT = [
    ("客户ID", "每位客户的唯一标识符"),
    ("年龄", "客户年龄"),
    ("性别", "客户性别：Male / Female / Other"),
    ("城市", "客户所在城市"),
    ("商品类别", "购买商品的类别"),
    ("商品名称", "购买的具体商品名称"),
    ("购买日期", "购买发生的日期"),
    ("消费金额", "本次消费的金额（元）"),
    ("支付方式", "支付方式"),
    ("是否使用折扣", "是否使用折扣（是 / 否）"),
    ("评分", "客户对这次购买的评价分数（1~5 分）"),
    ("是否复购", "该客户此前是否购买过（是 / 否）"),
]


# ---------------------------------------------------------------- 路径工具
def project_root() -> str:
    """返回项目根目录（大数据实训/）"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_data_path() -> str:
    """默认数据文件路径：项目根目录/data/沃尔玛客户购买行为数据集.xlsx"""
    return os.path.join(project_root(), "data", DATA_FILENAME)


# ---------------------------------------------------------------- 读取
def load_raw(path: str | None = None) -> pd.DataFrame:
    """读取原始 xlsx，统一成中文列名，并剔除「中文列名行」。

    Returns
    -------
    DataFrame  列名全为中文，值为原始（未清洗）数据
    """
    path = path or default_data_path()
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"找不到数据文件：{path}\n"
            f"请确认 data/ 目录下有《{DATA_FILENAME}》，"
            f"或运行 python tools/build_realistic_dataset.py 重新生成。"
        )

    df = pd.read_excel(path, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]

    # 兼容两种情况：表头是英文（需要映射）或表头本来就是中文
    if any(c in COLUMN_MAP for c in df.columns):
        df = df.rename(columns=COLUMN_MAP)

    # 剔除「客户ID | 年龄 | 性别 ...」这种中文列名行
    if "客户ID" in df.columns and len(df) > 0:
        first = str(df["客户ID"].iloc[0]).strip()
        if first in {"客户ID", "客户 Id", "客户id", "Customer_ID"}:
            df = df.iloc[1:].reset_index(drop=True)

    return df


def load_dictionary(path: str | None = None) -> list[tuple[str, str]]:
    """读取 xlsx 第二个 sheet「字段说明」，返回 [(字段, 说明), ...]；读不到就用兜底字典。"""
    path = path or default_data_path()
    try:
        raw = pd.read_excel(path, sheet_name=1, header=None)
        items: list[tuple[str, str]] = []
        for value in raw.itertuples(index=False):
            text = str(value[0]).strip() if value and value[0] is not None else ""
            if not text or text.lower() == "nan":
                continue
            # 形如「Age（年龄） – 客户年龄。」，拆成 字段 / 解释
            if "–" in text:
                head, tail = text.split("–", 1)
            elif "-" in text:
                head, tail = text.split("-", 1)
            else:
                head, tail = text, ""
            items.append((head.strip(), tail.strip()))
        if len(items) >= 3:
            return items
    except Exception:  # noqa: BLE001 - 说明 sheet 不存在时直接使用兜底
        pass
    return FIELD_DICT
