# 沃尔玛客户购买行为数据分析与可视化

使用 Python、pandas、Streamlit 和 pyecharts 分析 **模拟零售订单**。数据由课程实训脚本生成，不代表沃尔玛真实经营数据。

## 运行

需要 Python 3.10 或更高版本。Windows 可双击「启动看板.bat」，也可以在项目目录运行：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## 看板与指标

- **经营概览**：按日期、城市、品类等筛选销售趋势和品类贡献。
- **深入分析**：查看分组汇总、交叉分析与图表。
- **数据质量**：检查原始字段、缺失值、重复记录及异常金额。保留原始金额用于汇总。
- **报告导出**：下载 CSV、Excel 和分析结论。导出 Excel 时回读核对订单数与金额。

全量模拟数据去重后有 52,500 笔订单、30,000 位客户，总销售额为 13,898,405.08 元。复购订单占比为 42.86%，所选范围内至少下单两次的客户占 55.50%。

命令行运行 `python run_pipeline.py` 会在 `outputs/` 生成明细、报表和图表。加 `--no-export` 可仅运行分析。部分深入分析图表需要联网加载 ECharts。
