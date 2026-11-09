# Python 使用指南：pandas DataFrame 与香港住宅数据

当前 package 为 **0.6.2**，需要 **Python 3.10+**。GitHub 负责独立采集、存放和更新数据，Python package 负责读取。普通分析无需运行爬虫、克隆仓库或下载 Excel。pandas 和 PyArrow 会随 package 安装；只有取数时才加载，普通 import 不联网。

`Residential.history()` 是推荐的分析入口：返回 **pandas DataFrame + DatetimeIndex + float64 数值列**。指标名称、单位、频率和来源集中在 `catalog()`；逐条备注和标记在 `observations()`。旧 `fetch_residential()` 的记录列表接口保持兼容。

先看 [README 指标组速查表](README.md#指标组速查)：同类面积、地区、期限和计量方式合并解释，按尾缀选择。需要精确来源时再查[完整指标字典](https://github.com/Hogan-cyber/Real-Estate-Data/blob/residential-data/INDICATORS.md)。

**最快上手：** 下载 [完整 Jupyter Notebook](examples/HK_Property_Data.ipynb) 或 [Spyder／Python 示例](examples/dataset_overview.py)，依次运行即可得到 `overview`（分组全貌）、`catalog`（指标目录）、`all_data`（完整数值表）和 `df`（所选组与日期）。0.6.0 已内置分组与 overview；旧版本请升级后重启 kernel。

## Built-in groups and overview

```python
import hk_property_data as hk

market = hk.Residential()
overview = market.overview()
df = market.history(group="Price indices", start="2025-01")
```

`overview` 是按组和频率汇总的 DataFrame：`indicators`、`records`、`available_values`、`first_date`、`last_date`。日期是所选指标记录范围的并集，包含原始缺失记录，不保证每个成员都有数值。总览覆盖完整历史；日期分析使用 `history(start=..., end=...)`。

| 调用 | 用途 |
| --- | --- |
| `market.catalog(group="Price indices")` | 查看这一组的 ID、名称、单位和覆盖范围 |
| `market.history(group=["Price indices", "Rent indices"])` | 多个组一起返回数值表 |
| `market.history(group="HIBOR", frequency="M")` | 只取已有官方月度 HIBOR |
| `market.history(group="HIBOR", frequency="D")` | 只取每日 HIBOR |
| `hk.Residential(group="Bank mortgages").history(start="2025-01")` | 给对象设定默认组，以后只传日期 |
| `market.overview(refresh=True)` | 重新读取已发布快照并生成总览 |

`group` 支持显示名称、大小写不敏感的名称和下划线别名（如 `price_indices`），也支持多个名称的可迭代对象。多个组取并集；组、频率和显式 `series` 同时指定时取交集。`frequency` 接受 `D/M/Q/A/E`，只筛选，不重新采样。方法中的非 `None` 参数覆盖对应构造器默认值，`None` 沿用默认值；全市场查询使用未绑定的 `hk.Residential()`。

拼错组名、空选择器或完全不匹配的组／频率组合会抛出 `ValueError`；日期内没有记录时仍保留所选数值列。`catalog()` 新增 `group` 列，`observations()` 的原始字段保持原样。未知新指标放在 `Other / new indicators`，已有推算放在 `Mortgage estimates`。所有查询复用现有缓存，旧 `series=` 和原始记录接口继续可用。

## Spyder

在 Spyder 的 **IPython Console** 检查当前解释器，并只在首次使用或升级时安装：

```python
import sys
import subprocess

print(sys.executable)
assert sys.version_info >= (3, 10), "请使用 Python 3.10 或以上。"
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "--upgrade",
    "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.6.2-py3-none-any.whl",
])
```

升级后 **Consoles → Restart kernel**。不要每天重新执行安装代码，数据更新不需要重装 package。独立安装版 Spyder 先通过 **Preferences → Python interpreter** 或 **Consoles → New console in environment** 连接自己的 Python 环境；缺少 `spyder-kernels` 时按提示安装，见 [Spyder 官方说明](https://docs.spyder-ide.org/current/faq.html#using-spyder)。

在编辑器新建 `.py` 文件并运行：

```python
import hk_property_data as hk

market = hk.Residential("rvd_1_4_all_classes")
prices = market.history(start="2025-01", end="2026-09")
print(prices.tail(10))
print(prices.dtypes)
```

在 **Variable Explorer** 双击 `prices` 浏览表格。后面的分析示例也可在 Spyder 运行；将 `display(...)` 改为 `print(...)`，或直接在 Variable Explorer 打开表格。

## Jupyter Notebook

选择 **Python 3.10+ kernel**。首次安装或升级时，在单独 cell 执行：

```python
%pip install --upgrade "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.6.2-py3-none-any.whl"
```

然后 **Restart Kernel**。`%pip` 安装到当前 kernel 环境，见 [IPython 官方说明](https://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-pip)。不要把 `%pip` 放入普通 `.py` 文件；日常分析直接从下一段运行即可。

```python
import hk_property_data as hk

print(hk.__version__)
market = hk.Residential()
prices = market.history(
    series=["rvd_1_4_all_classes", "rvd_1_3_all_classes"],
    start="2025-01",
    end="2026-09",
)
display(prices.tail(10))
print(prices.dtypes)
print(type(prices.index).__name__)
```

结果示例：

```text
            Price index — All Classes  Rental index — All Classes
Date
2026-07-31                      320.1                       207.4
2026-08-31                      320.2                       211.2
2026-09-30                      320.8                       212.2
```

两列均为 `float64`，日期索引是 `DatetimeIndex`，不需要手动执行 `pd.DataFrame(...)` 或 `pd.to_datetime(...)`。数值 `0` 保留为零，缺失值为 `NaN`。

## Explore dataset

`catalog()` 返回每个指标一行的目录，索引为稳定的 `metric_id`。目录的文字是定义和说明，不混入历史数值表。它包括可读名称、单位、原始频率、全部来源、首末观察日期、记录数和非空记录数：

```python
catalog = market.catalog()
display(catalog[[
    "metric_name", "unit", "frequency", "sources",
    "first_date", "last_date", "observations", "non_missing",
]])

# 搜索租金相关指标
rental_catalog = catalog.loc[
    catalog["metric_name"].str.contains("rent", case=False, na=False)
]
display(rental_catalog)

# 查看所有指标的历史数值矩阵，直接返回数字列
all_history = market.history(labels="id")
print(all_history.shape)
display(all_history.tail())
```

指标和记录总数以代码输出为准；数据集包含官方观察值及明确标记的月度按揭试算。`history()` 以日期为行、指标为列，因此行数不等于原始记录数。各列按实际观察日期对齐，不同频率产生的空位保留为 `NaN`。用 `observations()` 查看 `status`、`flags`、`note` 和数据源，区别推算与官方原始数据。

`D/M/Q/A` 分别表示每日／月度／季度／年度，`E` 表示按生效日记录。不要把事件型 Prime 数据当作每日数据，或直接把月度、季度、年度数值混合求和。package 不自动重采样或前向填充。`non_missing` 只计已有记录的非空值；日期首尾之间不保证每期都有数据。

## 筛选与计算

```python
# DataFrame 内的日期切片：不联网
price_2026 = prices.loc["2026-01":"2026-09"]
display(price_2026)

# 稳定 ID 适合长期脚本；可读名称适合直接展示
by_id = market.history(
    series="rvd_1_4_all_classes", start="2025-01", labels="id",
)
print(by_id["rvd_1_4_all_classes"].mean())

# 以已观察记录的相邻值计算变化率，不自动填补空值
# 先自行确认序列的实际频率和缺口；存在缺期时不能直接称为月环比。
change_percent = by_id.pct_change(fill_method=None) * 100
```

`history` / `observations` 的 `start`、`end` 都包含边界，接受 `YYYY-MM` 或 `YYYY-MM-DD`；省略一端表示不限制。构造对象时可选择一个或多个指标；方法中的 `series` 会覆盖对象选择：

```python
selected_market = hk.Residential(["rvd_1_4_all_classes", "rvd_1_3_all_classes"])
selected_history = selected_market.history(start="2025-01")
m3 = selected_market.history(series="hk_m3_hkd", start="2025-01")
```

新的 DataFrame 接口对未知 ID 抛出 `ValueError`，避免拼错后静默得到空表。若 ID 正确但日期无记录，返回保留该指标数值列的空 DataFrame。重复可读名称自动加上指标 ID；`labels="id"` 始终使用 ID。重复指标/日期或同一 ID 的单位、名称、频率冲突会报错，不会静默取平均。

## 单位、来源与逐条备注

```python
# 一个数值表的列定义与数据集生成时间
print(prices.attrs["series"])
print(prices.attrs["data_generated_at"])

# 保留原始字段的长表：date 为 datetime，value 为 float64，说明字段为 category
observations = market.observations(
    series="rvd_1_4_all_classes", start="2025-01", end="2026-09",
)
display(observations[["date", "value", "status", "flags", "note", "source_url"]])
```

`status`、`flags`、`note` 可随每条观察值变化，因此保留在 `observations()`。`checked_at` / `source_checked_at` 保留来源检查信息；`date` 才是观察日期。单位可能是指数、港元金额、百分率或宗数，不能因为列都是数字就认为可直接相加。来源跨时期变化时，目录会列出全部来源，逐条详情保留各自 URL。

## Faster access

所有 `Residential` 对象与旧记录接口共用一个已验证的 Arrow 会话快照。首次下载约 0.75 MB 的 Parquet，缓存目前占约 5.6 MB Arrow buffers，上限 8 MiB；pandas 在筛选后从 Arrow 直接转换，不先创建全库 Python 字典。

```python
# 同一 kernel 再次调用，包括切换指标，不会重新下载
rent = market.history(series="rvd_1_3_all_classes", start="2025-01")
print(hk.residential_cache_info())

# 主动获取 GitHub 最新快照；已有 DataFrame 不会自动变化
latest = market.history(series="rvd_1_4_all_classes", refresh=True)

# 释放共享缓存，下次读取重新下载
hk.clear_residential_cache()
```

缓存没有计时到期；关闭 kernel 也会清除。`refresh=True` 先清除旧缓存，再重新读取；失败会报错，不会静默返回旧快照。`cache=False` 可做一次不读写缓存的读取。返回的 DataFrame 是独立结果，修改它不影响其他查询。

缓存预算只包含保留的 Arrow buffers，不包含 pandas/NumPy 库或返回的表格。当前完整数值矩阵约 7.7 MB；完整带分类字段的观察值表约 3.0 MB（本机 pandas 内存估算）。选少数指标会更小。读取器不保存数据文件；需要 CSV/Excel 时才主动下载或导出。

0.4.0 公开包的基准为首次 8.35 秒，后续原始记录查询约 1–1.5 毫秒。0.5.0 新增 DataFrame 整理，不能把原始记录速度直接等同于 DataFrame 速度；当前本机两指标 DataFrame 查询约 6 毫秒。实际时间随网络、机器、指标数量变化。

接口参考 [yfinance.Ticker.history](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html) 的历史表格使用方式；数值转换使用 [Arrow 与 pandas 集成](https://arrow.apache.org/docs/python/pandas.html)。

## SQL

SQL 仍在本地内存执行，不是在 GitHub 远程执行：

```python
conn = hk.connect_residential(series="rvd_1_4_all_classes", start="2025-01")
try:
    print(conn.execute(
        "SELECT date, value FROM observations ORDER BY date DESC LIMIT 5"
    ).fetchall())
finally:
    conn.close()
```

## 原始记录与文件下载

已有代码继续使用 `fetch_residential()` 返回记录列表，`iter_residential()` 返回记录迭代器。它们保留原先的 ISO 日期字符串和完整字段；需要分析表格时改用 `Residential.history()`。

```python
rows = hk.fetch_residential(series="rvd_1_4_all_classes", start="2025-01")

print(hk.residential_url("excel"))
print(hk.residential_url("csv"))
print(hk.residential_url("parquet"))
print(hk.residential_url("sqlite"))
```

手动下载格式也可由 `pandas.read_excel(...)` / `pandas.read_csv(...)` / `pandas.read_parquet(...)` 读取。独立 SQLite 工具通常需要本地文件；`connect_residential()` 不保存文件。

## 状态与常见问题

```python
status = hk.fetch_residential_status()
print(status["generated_at"])
print(status["errors"])
print(status.get("rate_release_notes", []))
```

状态读取独立联网，可能比当前会话快照更新；快照时间见 `history.attrs["data_generated_at"]` 或 `hk.residential_cache_info()`。数据集生成时间不代表每个指标都已发布到当天。

| 情况 | 处理方法 |
| --- | --- |
| 没有 `Residential`、没有 `overview()`，或不接受 `group=` | 升级到 0.6.2，然后重启 kernel；检查 `hk.__version__` 和 `hk.__file__`。 |
| 数据仍有大量文本列 | 确认使用 `.history()`；`.observations()` 和旧 `fetch_residential()` 保留完整元数据。 |
| `requires a different Python` | 切换到 Python 3.10+ 环境。 |
| 找不到 package | 在实际 kernel 打印 `sys.executable`，安装到同一环境。 |
| `ValueError` | 检查日期、指标 ID、参数；用 `.catalog()` 查看有效 ID。 |
| `CloudDataError` | 网络、发布文件或定义冲突；恢复连接或检查源数据后重试。 |

旧 `fetch_dataset()` / `fetch_status()` 仍是旧 dashboard 兼容接口。当前住宅分析使用本页的 `Residential` 接口。独立采集方法见 [RESIDENTIAL_DATA.md](RESIDENTIAL_DATA.md)，维护结构见 [RESIDENTIAL_ARCHITECTURE.md](docs/RESIDENTIAL_ARCHITECTURE.md)。
