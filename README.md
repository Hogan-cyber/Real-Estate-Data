# 香港住宅数据集 | Hong Kong Residential Data

整理香港住宅成交、楼价、租金、按揭及宏观数据，供 Excel、Python 和 SQL 分析使用。数据统一从 **2002 年 1 月**开始；官方较晚才发布的指标保留实际起点，缺失值留空。

**GitHub 负责存放和更新数据，Python package 负责读取。** 数据采集程序可以独立运行，不依赖 AI、个人电脑常开或付费 API。当前数据以 [`residential-data-latest` Release](https://github.com/Hogan-cyber/Real-Estate-Data/releases/tag/residential-data-latest) 为准。

## 获取数据

| 使用方式 | 入口 |
| --- | --- |
| Excel：直接查看和筛选各工作表 | [HK_Residential_Data.xlsx](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/HK_Residential_Data.xlsx) |
| CSV：长表，适合 Python / R | [observations.csv](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/observations.csv) · [压缩 CSV](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/observations.csv.gz) |
| SQLite：数据库文件 | [observations.sqlite](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/observations.sqlite) |
| 数据更新时间、来源检查及异常 | [collection_status.json](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/collection_status.json) |
| Python：按指标和日期读取 GitHub 数据 | [Spyder 使用指南](PYTHON_PACKAGE.md#spyder) · [Jupyter Notebook 使用指南](PYTHON_PACKAGE.md#jupyter-notebook) · [SQL 示例](PYTHON_PACKAGE.md#sql) |

Excel、CSV 和 SQLite 来自同一批记录。Excel 的 `Data_Dictionary` 列出指标 ID、单位、来源和实际覆盖范围。下载到本地的文件是当时的快照；Python 每次调用读取 GitHub 最新成功发布的数据。

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

需要 **Python 3.10 或以上**。安装的是代码包，不包含整套数据；无需克隆仓库。package 本身没有第三方运行依赖，pandas 仅在需要 DataFrame 时使用。

### Spyder

在 Spyder 已配置的、可安装 package 的 Python 环境中，先在 **IPython Console** 运行一次：

```python
import subprocess
import sys

print("当前 Python:", sys.executable)
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir",
    "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.3.0-py3-none-any.whl",
])
```

如果使用 Spyder 独立安装版，先按[完整指南](PYTHON_PACKAGE.md#spyder)连接自己的 Python 环境。升级后若已经导入过旧版 package，请重启 kernel。

新建 `.py` 文件，粘贴以下代码，点击 **Run**：

```python
import hk_property_data as hk

# 一个指标：住宅价格指数；结束日期包含整个 2026 年 9 月
rows = hk.fetch_residential(
    series="rvd_1_4_all_classes",
    start="2025-01",
    end="2026-09",
)
print("记录数:", len(rows))
for row in rows[-5:]:
    print(row["date"], row["value"], row["unit"])
```

### Jupyter Notebook

选择 Python kernel。**第一个 cell** 安装到当前 kernel 使用的环境：

```python
%pip install --upgrade --no-cache-dir "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.3.0-py3-none-any.whl"
```

安装完成后，若已导入过旧版 package，先 **Restart Kernel**。**第二个 cell** 读取两个指标并筛选月份：

```python
import hk_property_data as hk

status = hk.fetch_residential_status()
print("数据集生成时间:", status["generated_at"])
rows = hk.fetch_residential(
    series=["hk_m3_hkd", "hk_mortgage_approved_amount"],
    start="2025-01",
    end="2026-09",
)
print("记录数:", len(rows))
for row in rows[-5:]:
    print(row["metric_id"], row["date"], row["value"], row["unit"])
```

`series` 可以是一个指标 ID 或 ID 列表。`start` / `end` 包含边界；接受 `YYYY-MM` 或 `YYYY-MM-DD`，省略 `end` 即读取到最新可用记录。完整示例包含 [DataFrame、每日 HIBOR、指标表及 SQL](PYTHON_PACKAGE.md)。

读取器从 GitHub 流式读取压缩 CSV，在本地筛选，只保留选中的记录；不会自动保存数据文件或持久缓存。网络仍需传输压缩数据，返回的列表、DataFrame 或 SQL 表仍占用内存。已有变量不会自动刷新，需要重新调用读取函数。

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
