# 香港住宅数据集 | Hong Kong Residential Data

整理香港住宅成交、楼价、租金、按揭及宏观数据，供 Excel、Python 和 SQL 分析使用。数据统一从 **2002 年 1 月**开始；官方较晚才发布的指标保留实际起点，缺失值留空。

**GitHub 负责存放和更新数据，Python package 负责读取。** 数据采集程序可以独立运行，不依赖 AI、个人电脑常开或付费 API。当前数据以 [`residential-data-latest` Release](https://github.com/Hogan-cyber/Real-Estate-Data/releases/tag/residential-data-latest) 为准。

## 获取数据

| 使用方式 | 入口 |
| --- | --- |
| Excel：直接查看和筛选各工作表 | [HK_Residential_Data.xlsx](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/HK_Residential_Data.xlsx) |
| CSV：长表，适合 Python / R | [observations.csv](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/observations.csv) · [压缩 CSV](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/observations.csv.gz) |
| Parquet：Python 内部数据格式，可独立下载 | [observations.parquet](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/observations.parquet) |
| SQLite：数据库文件 | [observations.sqlite](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/observations.sqlite) |
| 数据更新时间、来源检查及异常 | [collection_status.json](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/collection_status.json) |
| Python：按指标和日期读取 GitHub 数据 | [Spyder 使用指南](PYTHON_PACKAGE.md#spyder) · [Jupyter 数据探索教程](#jupyter-notebook) · [SQL 示例](PYTHON_PACKAGE.md#sql) |

Excel、CSV 和 SQLite 来自同一批记录。Excel 的 `Data_Dictionary` 列出指标 ID、单位、来源和实际覆盖范围。下载到本地的文件是当时的快照；Python 首次读取 GitHub 已发布的 Parquet，并在本会话中复用该快照；`refresh=True` 可重新读取。

## 数据范围

| 分类 | 主要内容 | 官方来源 |
| --- | --- | --- |
| **Sales & Rent** | 住宅成交宗数与金额、一手／二手成交；平均售价和租金、价格和租金指数；住宅存量、落成量和空置量 | 土地注册处、差饷物业估价署（RVD） |
| **Mortgage** | 住宅按揭申请、批核、提款、未偿还贷款及相关比率；负资产统计；另列所有物业的按揭／押记登记宗数 | 香港金融管理局（HKMA）、土地注册处 |
| **Macro** | M1 / M2 / M3；每日 HIBOR；HSBC Prime 生效日期及利率；官方月平均利率 | HKMA、HSBC |

优先读取官方 CSV、Excel 或 API；较新的官方网页、PDF 公告用于补充。月度、季度、年度、每日及利率生效日保留各自频率，不插值、不用零填补缺失。

住宅成交、住宅按揭批核和所有物业按揭登记的统计范围不同，不能直接相减推算非银行贷款。RVD 平均售价不含一手成交。完整口径见[采集与数据说明](RESIDENTIAL_DATA.md#tables-and-definitions)。

## 自动更新

[Residential Excel collection](https://github.com/Hogan-cyber/Real-Estate-Data/actions/workflows/residential-data.yml) 设置为每天 **香港时间 18:00** 启动，配置为 [`0 10 * * *`（UTC）](.github/workflows/residential-data.yml)。成功采集后更新同一个 Release；也可以在 Actions 中手动运行。

这是计划启动时间，GitHub 排队可能延迟。每天检查不代表每个指标每天都有新值：月度指标仍按官方发布月份更新。检查时间、数据所属期间和利率生效日分别保存。[GitHub 定时任务说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## Python 快速开始

需要 **Python 3.10 或以上**，当前 package 为 **0.5.0**。安装的是代码包，不包含整套数据；无需克隆仓库。pandas 与 PyArrow 首次安装时自动安装，普通 `import hk_property_data` 不加载这两个库或访问网络。

### Spyder

在 Spyder 对应环境的 **IPython Console** 首次安装或升级：

```python
import sys
import subprocess

assert sys.version_info >= (3, 10), "请使用 Python 3.10 或以上。"
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "--upgrade",
    "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.5.0-py3-none-any.whl",
])
```

安装后重启 kernel。日常使用不用重复安装；在编辑器运行下方分析代码，在 **Variable Explorer** 打开 `df` 或 `all_data` 即可查看表格。独立版 Spyder 的环境设置见[完整指南](PYTHON_PACKAGE.md#spyder)。

### Jupyter Notebook

Run each code block below in a separate Jupyter cell, in order. Install only on first use or when upgrading, then **Restart Kernel**:

```python
import sys

assert sys.version_info >= (3, 10), "Please select a Python 3.10+ kernel."
%pip install --upgrade "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.5.0-py3-none-any.whl"
```

For everyday analysis, skip the installation cell and start below. **Use `.history()` to get a DataFrame.** The older `hk.fetch_residential()` returns a list of dictionaries; assigning it to a variable named `df` does not convert it into a table.

#### 1. Load multiple indicators as a DataFrame

Pass a list of IDs, just as you would choose several tickers. Every item must be a real indicator ID; do not include an empty string (`""`).

```python
import pandas as pd
import hk_property_data as hk
from IPython.display import display

print("Package version:", hk.__version__)  # 0.5.0 or newer

ticker_symbols = [
    "rvd_1_4_all_classes",  # Residential sales price index
    "rvd_1_3_all_classes",  # Residential rental index
    "hk_m3_hkd",           # Hong Kong dollar M3
]

df = hk.Residential(ticker_symbols).history(
    start="2025-01",
    end="2026-09",
)

df
```

Leave `df` as the last line of the cell, or use `display(df)`, to see a Jupyter table. Dates are the index; each indicator has its own readable column name and numeric (`float64`) values. `print(df)` produces a plain-text view.

#### 2. Load the full dataset

Create `Residential()` without an indicator selection to access all indicators and all available dates:

```python
market = hk.Residential()
all_data = market.history(labels="id")
catalog = market.catalog()

all_data
```

`labels="id"` gives the columns stable IDs for filtering. Use `market.history()` instead if you prefer readable names. `catalog` connects each ID to its name, unit and frequency.

Jupyter abbreviates large tables with `...`; **the complete result is still in `all_data`**. The full table aligns daily, monthly, quarterly, annual and effective-date observations on one date index, so many cells are `NaN`. A blank can mean no observation on that date or a missing source value; it is not zero. No values are automatically filled or resampled.

#### 3. Check the size, dates and data types

```python
print("Date rows:", all_data.shape[0])
print("Indicators:", all_data.shape[1])
print("Date range:", all_data.index.min(), "to", all_data.index.max())
print("Snapshot generated:", all_data.attrs["data_generated_at"])

display(all_data.head(5))  # First five dates
display(all_data.tail(5))  # Last five dates
all_data.info()           # Data types, non-missing counts and memory use
```

Rows here are dates, not individual source records. The last date in the whole table is not necessarily the latest date for every indicator. Use the catalog below to check each indicator's coverage.

#### 4. Browse all names and search for an indicator

Show every indicator, without Jupyter hiding the middle rows:

```python
catalog_columns = ["metric_name", "unit", "frequency", "first_date", "last_date"]

with pd.option_context("display.max_rows", None, "display.max_colwidth", None):
    display(catalog[catalog_columns])
```

The left-hand index is `metric_id`: copy it into `ticker_symbols` or `series`. Frequencies are `D` (daily), `M` (monthly), `Q` (quarterly), `A` (annual), and `E` (effective-date events). Coverage dates refer to recorded observations, which can include missing values.

Search by a word in either the name or ID. Change `keyword` to `"mortgage"`, `"M3"`, `"HIBOR"`, `"prime"`, or another term:

```python
keyword = "rent"
matches = catalog.loc[
    catalog["metric_name"].str.contains(keyword, case=False, na=False, regex=False)
    | catalog.index.str.contains(keyword, case=False, regex=False)
]

display(matches[catalog_columns])
```

To load all matching indicators for a chosen period:

```python
if matches.empty:
    print("No matching indicators. Try a different keyword.")
else:
    matching_data = market.history(
        series=matches.index.tolist(), start="2025-01", end="2026-09",
    )
    display(matching_data.tail(10))
```

#### 5. Select indicators and filter dates

For a focused table, select the indicators before aligning their dates. This reuses the cached dataset and avoids extra rows that belong only to unrelated indicators:

```python
indicator_ids = ["rvd_1_4_all_classes", "rvd_1_3_all_classes"]

selected = market.history(
    series=indicator_ids,
    start="2025-01",
    end="2026-09",
    labels="id",
)

selected
```

Both date bounds are **inclusive**. `"2026-09"` includes the whole month; `"2026-09-15"` ends on that specific day. Omitting a bound leaves that end unrestricted. Further filtering is ordinary pandas:

```python
# Choose dates and one column from the table already in memory.
price_2026 = selected.loc["2026-01":"2026-09", ["rvd_1_4_all_classes"]]
price_2026
```

You can also slice the full dataset directly:

```python
subset = all_data.loc["2025-01":"2026-09", indicator_ids]
subset
```

This last form keeps the full table's dates, including daily dates with no monthly value. Use `market.history(series=...)` above when you want only the selected indicators' observation dates. Neither form fills missing values.

#### 6. Find a specific value and its unit

For example, find Hong Kong dollar M3 for January 2025. Monthly observations use month-end dates:

```python
metric_id = "hk_m3_hkd"
observation_date = pd.Timestamp("2025-01-31")

value = all_data.at[observation_date, metric_id]
name = catalog.at[metric_id, "metric_name"]
unit = catalog.at[metric_id, "unit"]

print(name, observation_date.date(), value, unit)
```

`.at` requires an exact date and ID that exist in the table. If you only know the month, retrieve its observations as a DataFrame:

```python
m3_january = market.history(series="hk_m3_hkd", start="2025-01", end="2025-01")
m3_january
```

#### 7. Find dates that meet a condition, or the latest available value

Example: show dates when the residential price index was above 300. Check units before choosing a threshold; an index, a percentage and an amount are different measures.

```python
price_id = "rvd_1_4_all_classes"
price = market.history(series=price_id, start="2025-01", labels="id")

above_300 = price.loc[price[price_id] > 300]
display(above_300)

# Latest non-missing observation for this indicator, with its actual date.
display(price.dropna(subset=[price_id]).tail(1))
```

The condition excludes missing values. The final line skips missing values only for that latest-value view; it does not change `price` or fill any gaps.

#### 8. Inspect source records, notes and missing values

Use `observations()` when you want the full dataset as one row per indicator and observation, including its original metadata. It also returns a DataFrame, with numeric values and typed dates:

```python
observations = market.observations()
detail_columns = ["metric_id", "metric_name", "date", "value", "unit", "status", "note"]

print("Source records:", len(observations))
display(observations[detail_columns].head(10))

# Find the original record, including its source URL.
m3_record = observations.loc[
    (observations["metric_id"] == "hk_m3_hkd")
    & (observations["period"] == "2025-01"),
    detail_columns + ["source_url"],
]
display(m3_record)
```

`history()` is the numeric table for analysis; `catalog()` explains the indicators; `observations()` preserves per-record status, flags, notes and sources. Use `observations["value"].isna()` to identify missing values in actual source records, separately from blank cells created by aligning different frequencies.

For a **date-specific source lookup**, inspect the observation itself. For example, check where the December 2025 mortgage approval amount came from:

```python
mortgage_source = market.observations(
    series="hk_mortgage_approved_amount", start="2025-12", end="2025-12",
)

with pd.option_context("display.max_colwidth", None):
    display(mortgage_source[[
        "metric_name", "date", "value", "unit", "source_name", "source_url", "note",
    ]].T)
```

This record is **31,201 HKD million**, from HKMA's [Residential Mortgage Survey workbook, T0307.xlsx](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T0307.xlsx). It measures new approvals during December 2025, including primary-market purchases, secondary-market purchases and refinancing. Approvals are separate from drawdowns and outstanding balances. HKMA's survey covers authorised institutions representing about 99% of the banking sector's residential mortgage lending; co-financed loans include only the reporting institutions' portion. [HKMA survey definitions](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/banking/residential-mortgage-survey/)

For lender comparisons, label this series **banks / authorised institutions**. Licensed money lenders and property-developer finance require separate data; the current dataset does not provide a separate licensed-money-lender mortgage series. Land Registry registration totals are not a money-lender series and cannot be subtracted from HKMA approvals to calculate one. `catalog()["source_urls"]` lists sources across the indicator's history; `observations()["source_url"]` identifies the source for each particular record.

#### 9. Refresh when you want newer published data

The first read downloads the published Parquet; subsequent selections reuse a shared snapshot in the same kernel. It has no timed expiry. To fetch the latest publication explicitly:

```python
all_data = market.history(labels="id", refresh=True)
catalog = market.catalog()
print("Snapshot generated:", all_data.attrs["data_generated_at"])
```

Previously created variables such as `df`, `selected` and `observations` keep their old results; rerun their cells after refreshing. Restarting the kernel also clears the cache. The reader does not save dataset files; the shared Arrow cache is capped at 8 MiB, and returned DataFrames use additional memory. The snapshot timestamp records when that dataset was generated, not the observation date of every indicator.

The analysis cells also work in Spyder; browse `df` and `all_data` in Variable Explorer. Use the Excel / CSV links above if you want files for manual inspection.

详细示例见 [Python 指南](PYTHON_PACKAGE.md)、[数据集概览](PYTHON_PACKAGE.md#explore-dataset)和[缓存说明](PYTHON_PACKAGE.md#faster-access)。

## 开发与维护

在仓库根目录的 **终端** 执行以下命令，可以独立抓取官方数据并生成全部格式：

```bash
python -m pip install -r requirements-residential.txt
python scripts/collect_residential.py
```

输出目录为 `outputs/residential_2002/`。这属于采集端；只分析已发布数据的用户直接使用上面的 package 即可。

- [采集运行方法、覆盖范围和数据口径](RESIDENTIAL_DATA.md)
- [Python 接口、Spyder / Jupyter 安装与使用](PYTHON_PACKAGE.md)
- [代码结构、统一字段及后续维护边界](docs/RESIDENTIAL_ARCHITECTURE.md)

## Dashboard 状态

旧版 dashboard 代码保留在仓库中，旧更新流程已暂停，**尚未接入本次住宅数据集**。新数据的入口是本页的 Release 和 Python 接口；dashboard 接入与旧数据清理是后续迁移工作。
