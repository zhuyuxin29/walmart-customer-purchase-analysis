# -*- coding: utf-8 -*-
"""
生成“有真实业务规律”的沃尔玛客户购买行为数据集
=============================================
原始数据是纯随机生成的（各字段独立、分布均匀），画出来的图非常平。
本脚本在**保持 12 个字段不变**的前提下，注入真实零售业务规律：

  1. 客户会复购：3 万客户 → 5 万多订单，复购字段按真实订单历史计算
  2. 金额服从对数正态（右偏长尾），不同品类基准价不同
  3. 评分右偏（4~5 分占大头），符合真实电商评分分布
  4. 年龄近正态、性别偏女性，并影响品类偏好
  5. 城市分层：一线城市贡献大、客单价高
  6. 季节规律：11-12 月旺季、1-2 月淡季、周末单量更高
  7. 折扣、支付方式分布集中，且折扣与客单价/评分相关
  8. 保留少量“脏数据”：缺失、异常值、重复、大小写不统一

运行：
    .venv\\Scripts\\python.exe tools\\build_realistic_dataset.py
输出：
    data/沃尔玛客户购买行为数据集.xlsx          （新版，覆盖）
    data/沃尔玛客户购买行为数据集_原始.xlsx      （旧版备份，只备份一次）
"""
from __future__ import annotations

import os
import shutil

import numpy as np
import pandas as pd

SEED = 20241108
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
TARGET = os.path.join(DATA_DIR, "沃尔玛客户购买行为数据集.xlsx")
BACKUP = os.path.join(DATA_DIR, "沃尔玛客户购买行为数据集_原始.xlsx")

N_CUSTOMERS = 30000

# ---------------------------------------------------------------- 城市权重
# (城市, 权重%, 城市等级) —— 一线/新一线贡献大部分销售额，长尾城市多
CITIES = [
    ("Beijing", 12.0, 1), ("Shanghai", 11.0, 1), ("Guangzhou", 8.0, 1), ("Shenzhen", 8.0, 1),
    ("Hangzhou", 5.0, 1), ("Chengdu", 4.5, 1),
    ("Nanjing", 3.0, 2), ("Wuhan", 3.0, 2), ("Xi'an", 2.8, 2), ("Chongqing", 2.8, 2),
    ("Tianjin", 2.5, 2), ("Suzhou", 2.5, 2), ("Changsha", 2.2, 2), ("Zhengzhou", 2.2, 2),
    ("Qingdao", 2.0, 2), ("Ningbo", 2.0, 2), ("Dongguan", 1.8, 2), ("Foshan", 1.8, 2),
    ("Hefei", 1.6, 3), ("Fuzhou", 1.5, 3), ("Xiamen", 1.5, 3), ("Jinan", 1.5, 3),
    ("Shenyang", 1.4, 3), ("Dalian", 1.3, 3), ("Kunming", 1.3, 3), ("Harbin", 1.2, 3),
    ("Changchun", 1.1, 3), ("Shijiazhuang", 1.1, 3), ("Nanning", 1.0, 3), ("Taiyuan", 1.0, 3),
    ("Guiyang", 0.9, 3), ("Nanchang", 0.9, 3), ("Wenzhou", 0.9, 3), ("Wuxi", 0.8, 3),
    ("Xuzhou", 0.7, 4), ("Luoyang", 0.6, 4), ("Yantai", 0.6, 4), ("Zhuhai", 0.6, 4),
    ("Huizhou", 0.5, 4), ("Jinhua", 0.5, 4), ("Quanzhou", 0.5, 4), ("Baoding", 0.4, 4),
    ("Linyi", 0.4, 4), ("Nantong", 0.4, 4), ("Zhongshan", 0.4, 4), ("Guilin", 0.3, 4),
    ("Sanya", 0.3, 4), ("Lhasa", 0.2, 4), ("Xining", 0.2, 4), ("Yinchuan", 0.2, 4),
]
CITY_NAMES = [c[0] for c in CITIES]
CITY_PROBS = np.array([c[1] for c in CITIES], dtype=float)
CITY_PROBS = CITY_PROBS / CITY_PROBS.sum()
CITY_TIER = {c[0]: c[2] for c in CITIES}

# ---------------------------------------------------------------- 品类配置
# 基准价（中位数，元）、对数正态 sigma、折扣概率、商品名称
CATEGORY_CONF = {
    "Clothing":    dict(median=120.0, sigma=0.50, discount=0.45, share=0.35,
                        products=["T-Shirt", "Jeans", "Jacket", "Dress", "Hoodie"]),
    "Home":        dict(median=300.0, sigma=0.55, discount=0.30, share=0.20,
                        products=["Sofa", "Blender", "Lamp", "Coffee Maker", "Desk"]),
    "Grocery":     dict(median=50.0, sigma=0.40, discount=0.25, share=0.20,
                        products=["Milk", "Bread", "Rice", "Coffee", "Fruit Basket"]),
    "Electronics": dict(median=600.0, sigma=0.62, discount=0.20, share=0.15,
                        products=["Smartphone", "Laptop", "Tablet", "Headphones", "Camera"]),
    "Beauty":      dict(median=90.0, sigma=0.45, discount=0.40, share=0.10,
                        products=["Perfume", "Lipstick", "Face Cream", "Shampoo", "Makeup Kit"]),
}

PAYMENTS = ["Credit Card", "Debit Card", "PayPal", "Cash on Delivery", "UPI"]
PAYMENT_PROBS = np.array([0.34, 0.26, 0.14, 0.12, 0.14])

# 月份权重：11 月双十一、12 月年末旺季，1-2 月春节淡季
MONTH_WEIGHT = np.array([0.80, 0.70, 0.85, 0.90, 0.95, 0.95, 0.90, 0.92, 1.00, 1.05, 1.45, 1.30])
WEEKEND_BOOST = 1.12

FIELD_DICT = [
    ("Customer_ID", "每位客户的唯一标识符"),
    ("Age", "客户年龄"),
    ("Gender", "客户性别：Male / Female / Other"),
    ("City", "客户所在城市"),
    ("Category", "购买商品的类别"),
    ("Product_Name", "购买的具体商品名称"),
    ("Purchase_Date", "购买发生的日期"),
    ("Purchase_Amount", "本次消费的金额（元）"),
    ("Payment_Method", "支付方式"),
    ("Discount_Applied", "是否使用折扣（Yes / No）"),
    ("Rating", "客户对这次购买的评价分数（1~5 分）"),
    ("Repeat_Customer", "该客户此前是否购买过（Yes / No）"),
]


def build() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)

    # ---------------- 1. 客户层属性 ----------------
    # 年龄：正态（均值 38、标准差 12），截断 18~70
    ages = np.clip(rng.normal(38, 12, N_CUSTOMERS), 18, 70).round().astype(int)
    # 性别：女性 55%、男性 40%、其他 5%
    genders = rng.choice(["Female", "Male", "Other"], size=N_CUSTOMERS, p=[0.55, 0.40, 0.05])
    # 城市
    cities = rng.choice(CITY_NAMES, size=N_CUSTOMERS, p=CITY_PROBS)
    tiers = np.array([CITY_TIER[c] for c in cities])

    # 每个客户下多少单：约 45% 客户会复购（2~5 单）
    n2, n3, n4, n5 = int(N_CUSTOMERS * 0.40), int(N_CUSTOMERS * 0.12), int(N_CUSTOMERS * 0.03), int(N_CUSTOMERS * 0.005)
    orders_per_customer = np.ones(N_CUSTOMERS, dtype=int)
    perm = rng.permutation(N_CUSTOMERS)
    orders_per_customer[perm[:n2]] = 2
    orders_per_customer[perm[n2:n2 + n3]] = 3
    orders_per_customer[perm[n2 + n3:n2 + n3 + n4]] = 4
    orders_per_customer[perm[n2 + n3 + n4:n2 + n3 + n4 + n5]] = 5

    customer_index = np.repeat(np.arange(N_CUSTOMERS), orders_per_customer)
    n_orders = len(customer_index)

    # ---------------- 2. 订单层属性 ----------------
    # 日期：按月份权重 + 周末加成，在 2024-01-01 ~ 2025-12-31 内抽样
    days = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    day_w = MONTH_WEIGHT[days.month - 1] * np.where(days.dayofweek >= 5, WEEKEND_BOOST, 1.0)
    day_w = day_w / day_w.sum()
    order_dates = days[rng.choice(len(days), size=n_orders, p=day_w)]

    # 品类：基础占比 + 年龄/性别偏好（年轻人偏 Electronics/Beauty，年长偏 Home/Grocery）
    cat_names = list(CATEGORY_CONF.keys())
    base_share = np.array([CATEGORY_CONF[c]["share"] for c in cat_names])
    categories = np.empty(n_orders, dtype=object)
    for i, ci in enumerate(customer_index):
        age, gender = ages[ci], genders[ci]
        w = base_share.copy()
        if age < 30:
            w[cat_names.index("Electronics")] *= 1.5
            w[cat_names.index("Beauty")] *= 1.3
            w[cat_names.index("Home")] *= 0.7
        elif age > 50:
            w[cat_names.index("Home")] *= 1.6
            w[cat_names.index("Grocery")] *= 1.3
            w[cat_names.index("Electronics")] *= 0.7
        if gender == "Female":
            w[cat_names.index("Beauty")] *= 1.8
            w[cat_names.index("Clothing")] *= 1.25
            w[cat_names.index("Electronics")] *= 0.8
        elif gender == "Male":
            w[cat_names.index("Electronics")] *= 1.35
            w[cat_names.index("Beauty")] *= 0.5
        categories[i] = cat_names[rng.choice(len(cat_names), p=w / w.sum())]

    # 商品名称
    product_names = np.array([CATEGORY_CONF[c]["products"][rng.integers(0, 5)] for c in categories])

    # 金额：品类基准中位数 × 对数正态波动 × 城市等级 × 季节 × 折扣
    month_factor = np.where(np.isin(order_dates.month, [11, 12]), 1.20,
                            np.where(np.isin(order_dates.month, [1, 2]), 0.88, 1.0))
    tier_factor = np.where(tiers[customer_index] == 1, 1.22,
                           np.where(tiers[customer_index] == 2, 1.0, 0.86))
    median = np.array([CATEGORY_CONF[c]["median"] for c in categories])
    sigma = np.array([CATEGORY_CONF[c]["sigma"] for c in categories])
    amounts = median * np.exp(rng.normal(0, sigma)) * month_factor * tier_factor

    # 折扣：按品类概率
    discount_p = np.array([CATEGORY_CONF[c]["discount"] for c in categories])
    discounted = rng.random(n_orders) < discount_p
    amounts = np.where(discounted, amounts * rng.uniform(0.82, 0.95, n_orders), amounts)
    amounts = np.round(np.clip(amounts, 5, None), 2)

    # 支付方式
    payments = rng.choice(PAYMENTS, size=n_orders, p=PAYMENT_PROBS)

    # 评分：右偏（4~5 分占大头），折扣/复购略高
    rating_p = np.tile(np.array([0.02, 0.03, 0.10, 0.40, 0.45]), (n_orders, 1))
    rating_p[discounted] *= np.array([0.7, 0.8, 0.9, 1.0, 1.05])
    rating_p = rating_p / rating_p.sum(axis=1, keepdims=True)
    ratings = np.array([rng.choice([1, 2, 3, 4, 5], p=rating_p[i]) for i in range(n_orders)]).astype(float)
    ratings = np.clip(ratings + rng.normal(0, 0.35, n_orders), 1, 5).round(1)

    df = pd.DataFrame({
        "Customer_ID": [f"CU{100000 + ci:06d}" for ci in customer_index],
        "Age": ages[customer_index],
        "Gender": genders[customer_index],
        "City": cities[customer_index],
        "Category": categories,
        "Product_Name": product_names,
        "Purchase_Date": order_dates,
        "Purchase_Amount": amounts,
        "Payment_Method": payments,
        "Discount_Applied": np.where(discounted, "Yes", "No"),
        "Rating": ratings,
    })

    # 复购：按客户、按时间排序，第一单为 No，之后的都为 Yes
    df = df.sort_values(["Customer_ID", "Purchase_Date"]).reset_index(drop=True)
    seq = df.groupby("Customer_ID").cumcount()
    df["Repeat_Customer"] = np.where(seq == 0, "No", "Yes")

    # ---------------- 3. 注入“脏数据”（真实感的关键） ----------------
    n = len(df)

    # 3.1 缺失值：评分 5%、支付方式 2%、城市 1%
    df.loc[rng.random(n) < 0.05, "Rating"] = np.nan
    df.loc[rng.random(n) < 0.02, "Payment_Method"] = np.nan
    df.loc[rng.random(n) < 0.01, "City"] = np.nan

    # 3.2 异常值：少量批发大额订单 + 少量 0 元订单（退款）+ 极端年龄
    big_idx = rng.choice(n, size=15, replace=False)
    df.loc[big_idx, "Purchase_Amount"] = np.round(rng.uniform(3000, 8000, 15), 2)
    zero_idx = rng.choice(np.setdiff1d(np.arange(n), big_idx), size=8, replace=False)
    df.loc[zero_idx, "Purchase_Amount"] = 0.0
    age_idx = rng.choice(n, size=5, replace=False)
    df.loc[age_idx, "Age"] = rng.choice([0, 150, 200], size=5)

    # 3.3 文本不规范：大小写/空格不统一
    noise_city = rng.random(n) < 0.03
    df.loc[noise_city, "City"] = df.loc[noise_city, "City"].astype(str).str.lower()
    noise_gender = rng.random(n) < 0.02
    df.loc[noise_gender, "Gender"] = df.loc[noise_gender, "Gender"].map(
        {"Male": "male", "Female": "female", "Other": "other"}
    ).fillna(df.loc[noise_gender, "Gender"])
    noise_pay = rng.random(n) < 0.02
    df.loc[noise_pay, "Payment_Method"] = df.loc[noise_pay, "Payment_Method"].astype(str).str.lower()

    # 3.4 重复订单：系统重复推送 50 条
    dup = df.sample(50, random_state=SEED)
    df = pd.concat([df, dup], ignore_index=True)

    # 打乱顺序，让数据看起来像自然导出的
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)

    # 购买日期恢复成“日期”格式（Excel 里显示为日期）
    df["Purchase_Date"] = pd.to_datetime(df["Purchase_Date"]).dt.date
    return df


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(TARGET) and not os.path.exists(BACKUP):
        shutil.copy2(TARGET, BACKUP)
        print(f"已备份原始数据 -> {BACKUP}")

    df = build()
    print(f"生成订单数: {len(df):,}  客户数: {df['Customer_ID'].nunique():,}")
    print("复购订单占比: %.1f%%" % (df["Repeat_Customer"].eq("Yes").mean() * 100))
    print("缺失值:\n", df.isna().sum()[df.isna().sum() > 0].to_string())
    print("重复行:", int(df.duplicated().sum()))
    print("\n品类占比:\n", (df["Category"].value_counts(normalize=True) * 100).round(1).to_string())
    print("\n品类销售额占比:\n",
          (df.groupby("Category")["Purchase_Amount"].sum()
           / df["Purchase_Amount"].sum() * 100).round(1).to_string())
    print("\n性别占比:\n", (df["Gender"].value_counts(normalize=True) * 100).round(1).to_string())
    print("\n评分分布:\n", df["Rating"].value_counts().sort_index().to_string())
    print("\n月度订单数:\n", df["Purchase_Date"].astype(str).str[:7].value_counts().sort_index().to_string())

    # 写回 xlsx：保持原文件结构（英文表头 + 中文列名行 + 字段说明 sheet）
    label_row = {c: c for c in df.columns}
    label_row = {"Customer_ID": "客户ID", "Age": "年龄", "Gender": "性别", "City": "城市",
                 "Category": "商品类别", "Product_Name": "商品名称", "Purchase_Date": "购买日期",
                 "Purchase_Amount": "消费金额", "Payment_Method": "支付方式",
                 "Discount_Applied": "是否使用折扣", "Rating": "评分", "Repeat_Customer": "是否复购"}
    df_out = pd.concat([pd.DataFrame([label_row]), df.astype(object)], ignore_index=True)

    with pd.ExcelWriter(TARGET, engine="openpyxl") as writer:
        df_out.to_excel(writer, sheet_name="Walmart_customer_purchases", index=False)
        pd.DataFrame([f"{k} – {v}" for k, v in FIELD_DICT]).to_excel(
            writer, sheet_name="字段说明", index=False, header=False
        )
    print(f"\n已写入: {TARGET}")
    print(f"文件大小: {os.path.getsize(TARGET) / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
