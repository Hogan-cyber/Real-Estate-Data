# 香港住宅数据集 | Hong Kong Residential Data

整理香港住宅成交、楼价、租金、按揭及宏观数据，供 Excel、Python 和 SQL 分析使用。数据统一从 **2002 年 1 月**开始；官方较晚才发布的指标保留实际起点，缺失值留空。

**GitHub 负责存放和更新数据，Python package 负责读取。** 数据采集程序可以独立运行，不依赖 AI、个人电脑常开或付费 API。当前数据以 [`residential-data-latest` Release](https://github.com/Hogan-cyber/Real-Estate-Data/releases/tag/residential-data-latest) 为准。

**快速入口：** [指标组速查](#指标组速查) · [Jupyter 全貌与筛选](#jupyter-notebook) · [可直接运行的 Notebook](examples/HK_Property_Data.ipynb)

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

## 指标组速查

先找数据组，再按尾缀选择面积、地区或统计口径。下表的 `*` 是命名示意；调用 package 时使用目录中的完整 ID，或用下面的前缀／尾缀筛选代码。

| 主题 | Python 组名 | ID 模式 | 包含内容与分组方式 | 频率／来源 |
| --- | --- | --- | --- | --- |
| Sales & Rent | `Transactions` | `hk_residential_*sales_*`、`hk_all_building_sales_count` | 住宅成交宗数／金额；总住宅、一手 `primary`、二手 `secondary`；另有全部楼宇成交宗数 | M · LR |
| Sales & Rent | `Average rents` | `rvd_1_1_{class}_{district}` | 平均租金，HKD／平方米／月；5 类面积 × 3 地区 | M · RVD |
| Sales & Rent | `Average prices` | `rvd_1_2_{class}_{district}` | 平均售价，HKD／平方米；5 类面积 × 3 地区，不含一手成交 | M · RVD |
| Sales & Rent | `Rent indices` | `rvd_1_3_{class}` | 租金指数，1999=100；全部、A–E、ABC／DE 合并类别 | M · RVD |
| Sales & Rent | `Price indices` | `rvd_1_4_{class}` | 售价指数，1999=100；全部、A–E、ABC／DE 合并类别 | M · RVD |
| Sales & Rent | `Popular developments` | `rvd_1_5_{class}_{area}` | 选定屋苑售价指数，1999=100；整体／ABC／DE × 全部／市区／新界 | M · RVD |
| Sales & Rent | `Annual supply` | `rvd_stock_*`、`rvd_completions_*`、`rvd_vacancy_*`、`rvd_takeup_*` | 存量、落成、空置、净吸纳；按面积和合计拆分。单位为住宅单位数或比例，以目录为准 | A · RVD |
| Mortgage | `Bank mortgages` | `hk_mortgage_*` | 申请 `applications`、批核 `approved`、提款 `drawn`、余额 `outstanding`；另含 LTV、期限、拖欠／撇销、定价方式和共同融资的银行部分 | M · HKMA |
| Mortgage | `Mortgage registrations` | `hk_all_property_*` | 全物业按揭／法定押记及解除文书宗数；`building` 指建筑融资，不能当作住宅贷款数 | M · LR |
| Mortgage | `Negative equity` | `hk_negative_equity_*` | 银行负资产按揭宗数、余额、占比、LTV、拖欠和无物业价值覆盖金额；季度存量 | Q · HKMA |
| Mortgage | `Mortgage estimates` | `*_estimate`；`hk_residential_sales_share`；`hk_bank_mortgage_refinancing_*_share` | 已有住宅／银行非转按／money-lender 差额推算及三个输入比例；不是官方 money-lender 实际观测值 | M · 仓库公式 |
| Macro | `Money supply` | `hk_m{1,2,3}_{currency}` | M1／M2／M3 × 港元／外币／合计；金额统一以 HKD million 表示 | M · HKMA |
| Macro | `HIBOR` | `hk_hibor_{tenor}_daily`；`hk_hibor_1m`、`hk_hibor_3m` | 不同期限的每日 HIBOR；没有 `_daily` 的这两条是官方月均，单位 % p.a. | D／M · HKMA、HKAB |
| Macro | `Prime rate` | `hk_prime_rate_hsbc`、`hk_prime_rate_hsbc_effective` | 前者为官方月均，后者只记录 HSBC 利率变更的生效日；单位 % p.a. | M／E · HKMA／HSBC |

### 尾缀怎么选

| 维度 | ID 中的写法 | 含义与使用范围 |
| --- | --- | --- |
| 面积 | `class_a` … `class_e` | 实用面积：A <40、B 40–<70、C 70–<100、D 100–<160、E ≥160 平方米 |
| 合并面积 | `all_classes`、`classes_a_b_c`、`classes_d_e` | 全部面积类别、ABC 合并、DE 合并；`all_classes` 不表示所有物业种类 |
| 地区 | `hong_kong`、`kowloon`、`new_territories` | 港岛、九龙、新界；如 `rvd_1_2_class_a_kowloon` |
| 选定屋苑 | `overall`／`classes_a_b_c`／`classes_d_e` + `all`／`urban`／`new_territories` | `rvd_1_5_` 专用面积／地区组合；`urban` 为港岛及九龙。完整例子：`rvd_1_5_overall_all` |
| 成交／贷款用途 | `primary`、`secondary`、`refinancing` | 一手、二手、转按；转按拆分在 HKMA 批核数据中，不能套用到提款总数 |
| 计量方式 | `count`、`value`、`amount` | 宗数、成交金额、贷款金额；金额通常为 HKD million，具体单位查 `catalog` |
| 货币 | `hkd`、`fc`、`total` | 港元、外币、合计；外币也换算为 HKD million |
| 利率期限 | `overnight`、`1w`、`1m`、`3m`、`6m`、`9m`、`12m` | 隔夜、一周、一月至十二月；`1m` 是一个月期限，不代表月度频率 |
| 利率频率 | `_daily`、`_effective` | 每日观察、利率变更生效事件；没有这两个尾缀的已列利率序列是月均 |
| 年度供应 | `class_a` … `class_e`／`total`；`sa_less_than_100_m2`／`sa_100_m2_or_above` | 存量、落成、空置按 A–E／合计；净吸纳按 <100／≥100 平方米／合计。空置 `_vacancy` 为比例，`_vacancy_unit` 为单位数 |
| 推算／比例 | `_estimate`、`_share` | `_estimate` 为公式推算；`_share` 的单位可能是 `fraction` 或 `%`，必须查目录，不能一律乘 100 |

只有实际出现在 `catalog.index` 的组合才可调用，不要把不同表的尾缀任意拼接。完整例子：`rvd_1_3_all_classes` 是租金指数，`rvd_1_4_class_a` 是 A 类售价指数，`hk_m3_hkd` 是港元 M3。

频率：`D` 每日、`M` 每月、`Q` 每季、`A` 每年、`E` 生效事件。`fraction` 的 0.25 表示 25%，而 `%` 的 2.5 已表示 2.5%。面积与地区口径见 [RVD 技术附注](https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf)。

需要精确来源或特殊口径时，再查[自动更新的完整字典](https://github.com/Hogan-cyber/Real-Estate-Data/blob/residential-data/INDICATORS.md)、`catalog()` 或 `observations()`；README 按组介绍，不逐个重复展开。

## 数据范围

| 分类 | 主要内容 | 官方来源 |
| --- | --- | --- |
| **Sales & Rent** | 住宅成交宗数与金额、一手／二手成交；平均售价和租金、价格和租金指数；住宅存量、落成量和空置量 | 土地注册处、差饷物业估价署（RVD） |
| **Mortgage** | 官方住宅按揭、全物业按揭登记及季度负资产；另有明确标注的住宅／银行／money-lender 月度推算 | HKMA、土地注册处；推算由仓库代码计算 |
| **Macro** | M1 / M2 / M3；每日 HIBOR；HSBC Prime 生效日期及利率；官方月平均利率 | HKMA、HSBC |

优先读取官方 CSV、Excel 或 API；较新的官方网页、PDF 公告用于补充。月度、季度、年度、每日及利率生效日保留各自频率，不插值、不用零填补缺失。

住宅成交、住宅按揭批核和全物业按揭登记的统计范围不同。新增的月度分配试算使用显式假设，不能视为官方或已识别的纯 money-lender 贷款。RVD 平均售价不含一手成交。完整口径见[采集与数据说明](RESIDENTIAL_DATA.md#tables-and-definitions)。

**Source audit — 5 November 2026:** all 72,142 published observations matched the official values checked. Some older HKMA mortgage details and negative-equity releases remain uncollected; source coverage notes and workbook-cell references have been corrected. See the [audit findings and historical coverage limits](docs/SOURCE_AUDIT_2026-11-05.md).

## 月度按揭推算：在原数据集内

原有 `Mortgage_Monthly` 工作表中，日期后先排列官方原始数据，再排列三列宗数及三列金额：**住宅总量推算 → 银行扣除转按推算 → money-lender 差额推算**，最后是计算所用的比例和平均贷款额。每个月单独计算，不使用全年统一比例。表顶显示公式并链接到 Python 计算函数；Excel 移除逐格 note，来源集中在 `Data_Dictionary`。负数保留，表示该月估算口径无法对齐，不代表实际负贷款。

每日 HIBOR 历史使用 HKMA 表 6.3.3，最新营业日直接读取原始发布者 [HKAB](https://www.hkab.org.hk/en/rates/hibor/) 的上午 11:15 fixing，覆盖现有 overnight、1w、1m、3m、6m、12m 序列。周末和公会确认为公众假期的日期跳过，不延用前一天数值。9m 已停止发布，只保留历史。18:00 香港时间的 GitHub 更新任务会重新检查各数据源；营业日抓取失败、日期不符或缺少期限数值时，任务失败并保留上次成功发布的数据。

- 住宅宗数推算 = LR 全物业按揭文书宗数 ×（当月住宅买卖合约宗数 ÷ 当月全部楼宇买卖合约宗数）。
- 银行购房宗数推算 = HKMA 当月提款宗数 ×（1 − 当月转按批核宗数 ÷ 当月总批核宗数）。金额用独立的金额比例计算。
- money-lender 宗数试算 = 住宅宗数推算 − 银行购房宗数推算。金额假设其平均每笔贷款等于当月银行购房贷款推算均额。

这是**只在银行侧剔除转按**的试算；差额仍可能含 LR 中的银行转按、其他贷款人和时间／范围差异，不能识别并剔除地产商关联贷款。缺失输入留空，负差额保留并标记。公式、输入指标 ID、官方来源及状态见 Excel 单元格批注、`Data_Dictionary` 和[推算说明](docs/MORTGAGE_ESTIMATES.md)。新增指标也可从原来的 Python 接口读取，无须重新安装：

```python
import hk_property_data as hk

ids = [
    "hk_residential_mortgage_count_estimate",
    "hk_bank_mortgage_purchase_drawn_count_estimate",
    "hk_money_lender_mortgage_count_estimate",
]
market = hk.Residential(ids)
df = market.history(start="2025-01", labels="name", refresh=True)
df  # 三个独立数值列，日期为索引

details = market.observations(start="2025-01")
details[["date", "metric_name", "value", "status", "flags", "source_url", "note"]]
```

`Negative_Equity_Quarterly` 保留为独立的**季度银行按揭风险**工作表：它记录负资产贷款的存量宗数、余额、无抵押覆盖部分和拖欠情况，不参与月度新增贷款推算。负资产不等于违约；该调查也不等于全市场或 money-lender 的风险统计。[HKMA 口径](https://www.hkma.gov.hk/eng/news-and-media/press-releases/2026/10/20261030-6/)

## 下载源代码，在本地采集或改公式

可以直接点击 GitHub 的 **Code → Download ZIP**，或者[下载 main 分支源代码 ZIP](https://github.com/Hogan-cyber/Real-Estate-Data/archive/refs/heads/main.zip)，解压后打开项目文件夹。在该文件夹的终端运行（Python 3.10+）：

```bash
python -m pip install -r requirements-residential.txt
python scripts/collect_residential.py
```

macOS 若 `python` 不可用，改用 `python3`。生成文件在 `outputs/residential_2002/`，包含 Excel、CSV、Parquet 和 SQLite。完整运行不需要 AI、API key 或 GitHub 登录，只需访问公开数据源的网络连接。

修改[月度公式文件](python/hk_property_data/simple/mortgage_estimates.py)后，可用已采集的本地输入重算，避免再次下载：

```bash
python scripts/collect_residential.py --from-saved
```

首次运行需先正常采集；`--from-saved` 不会更新官方输入。数据源采集代码位于 `python/hk_property_data/simple/`，Excel 分类和列顺序位于 `simple/export.py`。本地运行只更新本地文件；GitHub Actions 执行同一个程序，负责更新 GitHub 发布的数据。

## 自动更新

[Residential Excel collection](https://github.com/Hogan-cyber/Real-Estate-Data/actions/workflows/residential-data.yml) 设置为每天 **香港时间 18:00** 启动，配置为 [`0 10 * * *`（UTC）](.github/workflows/residential-data.yml)。成功采集后更新同一个 Release；也可以在 Actions 中手动运行。

这是计划启动时间，GitHub 排队可能延迟。每天检查不代表每个指标每天都有新值：月度指标仍按官方发布月份更新。检查时间、数据所属期间和利率生效日分别保存。[GitHub 定时任务说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## Python 快速开始

需要 **Python 3.10 或以上**，当前 package 为 **0.6.0**。安装的是代码包，不包含整套数据；无需克隆仓库。pandas 与 PyArrow 首次安装时自动安装，普通 `import hk_property_data` 不加载这两个库或访问网络。

### Spyder

在 Spyder 对应环境的 **IPython Console** 首次安装或升级：

```python
import sys
import subprocess

assert sys.version_info >= (3, 10), "请使用 Python 3.10 或以上。"
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "--upgrade",
    "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.6.0-py3-none-any.whl",
])
```

安装后重启 kernel。日常使用不用重复安装；在编辑器运行下方分析代码，在 **Variable Explorer** 打开 `df` 或 `all_data` 即可查看表格。独立版 Spyder 的环境设置见[完整指南](PYTHON_PACKAGE.md#spyder)。

### Jupyter Notebook

**0.6.0 已内置分组。** 下载 [完整 Notebook](examples/HK_Property_Data.ipynb) 或 [Spyder／Python 示例](examples/dataset_overview.py)，不再复制分组字典或辅助函数。旧版本请先升级。

首次安装或升级，在一个 cell 运行，完成后 **Restart Kernel**。日常使用跳过安装：

```python
import sys
assert sys.version_info >= (3, 10), "Please select a Python 3.10+ kernel."
%pip install --upgrade "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.6.0-py3-none-any.whl"
```

#### 1. 几行看全貌和完整 DataFrame

```python
import hk_property_data as hk
from IPython.display import display

market = hk.Residential()
overview = market.overview()
display(overview)

all_data = market.history(labels="id")
display(all_data)
print("Snapshot generated:", all_data.attrs["data_generated_at"])
```

| 接口 | 返回的 DataFrame |
| --- | --- |
| `market.overview()` | 每组／频率一行：指标数、原始记录数、非空数值数、记录日期范围 |
| `market.catalog()` | 每个 ID 一行：`group`、名称、单位、频率、来源及覆盖时间 |
| `market.history()` | 完整数值表：日期为索引、指标为列，数值为 float64 |
| `market.observations()` | 带原始来源、状态、备注的逐条记录 |

`overview` 的起止日期是各成员记录范围的并集，不保证每条指标同样完整；`records` 包括原始缺失记录，`available_values` 只统计非空数值。总览覆盖所选指标的完整历史。不同频率分别显示，`D/M/Q/A/E` 分别为每日／每月／每季／每年／生效事件。

`all_data` 包含全部数据。Jupyter 的 `...` 只是折叠展示；对齐不同频率后产生的空位保留为 `NaN`，不会补零、插值或自动重新采样。

#### 2. 按组和日期读取

从 `overview` 复制组名即可。只需修改 `group`、`start` 和 `end`：

```python
df = market.history(group="Price indices", start="2025-01", end=None)
display(df)

# 查看该组包含哪些 ID、名称和单位。
catalog = market.catalog(group="Price indices")
display(catalog[["metric_name", "unit", "frequency", "first_date", "last_date"]])
```

日期两端均包含在内，`end="2025-12"` 包含整个月；`None` 不限制该日期边界。默认列名是可读名称，`labels="id"` 改用稳定 ID。

#### 3. 多组一起读，或者指定频率

```python
prices_and_rents = market.history(
    group=["Price indices", "Rent indices"], start="2025-01",
)
display(prices_and_rents.tail(6))

monthly_hibor = market.history(group="HIBOR", frequency="M", start="2025-01")
display(monthly_hibor.tail(6))

daily_hibor = market.history(group="HIBOR", frequency="D", start="2026-01")
display(daily_hibor.tail(6))
```

组名不区分大小写，也接受 `price_indices` 这样的下划线写法。`frequency` 筛选已有频率，不计算月均。多个组取并集；`group`、`frequency` 和 `series` 同时使用时取交集。未知组名或没有匹配指标会明确报错；指标存在但日期内无记录时，返回保留数值列的空表。

也可以固定一个对象的默认组，以后只传日期：

```python
prices = hk.Residential(group="Price indices")
display(prices.history(start="2025-01"))
```

方法中显式提供的选择器覆盖对应的构造器默认值；选择器为 `None` 时沿用默认值。要重新查看所有组，用 `hk.Residential()`。

#### 4. 按尾缀或完整 ID 选择

```python
# 九龙平均售价：自动包括该地区的所有面积类别。
prices_catalog = market.catalog(group="Average prices")
ids = prices_catalog.index[prices_catalog.index.str.endswith("_kowloon")].tolist()
kowloon = market.history(series=ids, start="2025-01")
display(kowloon.tail(6))

# 现有多个指标 ID 的写法继续可用。
selected = market.history(
    series=["rvd_1_4_all_classes", "rvd_1_3_all_classes"],
    start="2025-01", end="2025-12", labels="id",
)
display(selected.loc["2025-06":"2025-12"])
```

#### 5. 查来源，主动刷新

```python
source = market.observations(
    group="Bank mortgages", series="hk_mortgage_drawn_amount",
    start="2025-01", end="2025-01",
)
display(source[["date", "metric_name", "value", "unit", "status", "source_url"]])

# 需要 GitHub 新发布的数据时，再主动刷新。
overview = market.overview(refresh=True)
all_data = market.history(labels="id")
```

已有 `df` 等变量不会自动改变，刷新后重跑其读取语句。首次读取下载 Parquet，之后不同对象／组别／日期筛选共用会话缓存；缓存没有定时过期，重启 kernel 会清空。共享 Arrow 缓存上限 8 MiB，返回的 DataFrame 另外占用内存。

分组由 package 维护，不改变原始来源记录。未来尚未分类的新 ID 会出现在 `Other / new indicators`；`Mortgage estimates` 保留已有推算及输入比例，不能当作官方 money-lender 观测值。

分析代码也适用于 Spyder，可在 **Variable Explorer** 打开 `overview`、`all_data` 或 `df`。更多查值、SQL、导出和缓存用法见 [Python 指南](PYTHON_PACKAGE.md)。

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

[Open Hong Kong Property Monitor](https://hogan-cyber.github.io/Real-Estate-Data/) — two English pages: **Overview** and **Mortgage**.

The dashboard reads this same residential dataset. Both pages put the latest HSBC Prime rate, **daily HIBOR**, and Hong Kong dollar M3 at the top. Line charts, horizontal bars, date filters, indicator lookup, source inspection and data downloads support exploration. Monthly-average HIBOR remains in the dataset but is not displayed. Existing mortgage estimates are clearly labelled; the dashboard adds no new calculations or observations.

After each successful daily collection, GitHub Actions rebuilds and deploys the website automatically. It runs without AI, a ChatGPT account or a local computer. [Dashboard guide, update flow and local installation](docs/DASHBOARD.md).
