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
| Python：按指标和日期读取 GitHub 数据 | [Spyder 使用指南](PYTHON_PACKAGE.md#spyder) · [Jupyter Notebook 使用指南](PYTHON_PACKAGE.md#jupyter-notebook) · [SQL 示例](PYTHON_PACKAGE.md#sql) |

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

安装后重启 kernel。日常使用不用重复安装；在编辑器运行下方分析代码，在 **Variable Explorer** 打开 `prices` 即可查看表格。独立版 Spyder 的环境设置见[完整指南](PYTHON_PACKAGE.md#spyder)。

### Jupyter Notebook

首次安装或升级时在单独 cell 执行，然后 **Restart Kernel**：

```python
%pip install --upgrade "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.5.0-py3-none-any.whl"
```

以下分析代码适用于 Spyder 和 Jupyter。返回值直接是 pandas DataFrame：日期为索引，数据列均为 `float64`，列名可直接阅读。

```python
import hk_property_data as hk

market = hk.Residential()
prices = market.history(
    series=["rvd_1_4_all_classes", "rvd_1_3_all_classes"],
    start="2025-01",
    end="2026-09",
)
print(prices.tail())
print(prices.dtypes)

# 一次查看所有指标名称、单位、原始频率和日期覆盖
catalog = market.catalog()
print(catalog[["metric_name", "unit", "frequency", "first_date", "last_date"]])
```

结果示例：

```text
            Price index — All Classes  Rental index — All Classes
Date
2026-07-31                      320.1                       207.4
2026-08-31                      320.2                       211.2
2026-09-30                      320.8                       212.2
```

也可像 Ticker 一样先选择指标：`hk.Residential("rvd_1_4_all_classes").history(start="2025-01")`。用 `labels="id"` 保留稳定指标 ID 作为列名。`start` / `end` 包含边界；接受 `YYYY-MM` 或 `YYYY-MM-DD`。缺失值为 `NaN`，不自动填值或混合统计频率。单位、来源和频率见 `catalog` 或 `prices.attrs["series"]`；逐条标记和备注见 `market.observations(...)`。

首次取数读取一次 Parquet，后续对象、指标与日期查询复用同一 Arrow 快照。缓存上限 8 MiB，不写数据文件；返回的 DataFrame 另占内存。使用 `refresh=True` 获取最新发布，已有变量不会自行改变。旧 `fetch_residential()` 继续返回原始记录列表，适用于需要完整导出字段的代码。

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
