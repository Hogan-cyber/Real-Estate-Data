# Python 使用指南：从 GitHub 读取香港住宅数据

`hk_property_data` 读取本仓库已经发布的住宅数据集。GitHub Actions 负责采集和更新，package 负责按指标、日期读取数据；使用者无需运行爬虫、克隆仓库或预先下载 Excel。

需要 **Python 3.10 或以上**和互联网连接。当前 package 为 **0.3.0**，通过 GitHub Release 安装，没有第三方运行依赖。安装包只含代码；读取时不会自动生成本地数据文件。数据更新无需重新安装，重新调用读取函数即可。

选择你的环境：[Spyder](#spyder) · [Jupyter Notebook](#jupyter-notebook)。两套示例可以独立使用，不需要依次执行。

## Spyder

### 1. 确认使用的 Python 环境

在 Spyder 的 **IPython Console** 运行：

```python
import sys
print("Python 路径:", sys.executable)
print("Python 版本:", sys.version)
```

下面的安装命令使用同一个解释器，避免安装成功后 Spyder 却无法导入。

如果使用 Spyder 独立安装版，请先连接自己的 Python / Conda 环境：在 **Preferences → Python interpreter** 选择解释器，或通过 **Consoles → New console in environment** 打开对应环境。缺少 `spyder-kernels` 时按 Spyder 提示安装所需版本，再重启 kernel。详细操作见 [Spyder 官方环境说明](https://docs.spyder-ide.org/current/faq.html#using-spyder)。

### 2. 首次安装，已有读取接口时自动跳过

在该环境的 **IPython Console** 粘贴以下 Python 代码。环境需允许安装 package 并已包含 pip：

```python
import sys

assert sys.version_info >= (3, 10), "请使用 Python 3.10 或以上。"
try:
    from hk_property_data import fetch_residential
except ImportError:
    import subprocess
    PACKAGE_URL = (
        "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/"
        "residential-data-latest/hk_property_data-0.3.0-py3-none-any.whl"
    )
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE_URL,
    ])
else:
    print("读取接口已可用，跳过安装。")
```

首次使用时，这一步会从 GitHub 下载并安装小型代码包。已有读取接口时，仅检查本地安装，跳过 pip 和网络下载。不要把 `pip install ...` 或 `python -m pip ...` 当作 Python 代码写进 `.py` 文件。若已经导入过旧版，安装后执行 **Consoles → Restart kernel**。

### 3. 新建 Python 文件并读取数据

在 Spyder 编辑器新建文件，例如 `read_hk_residential.py`，粘贴并点击 **Run**：

```python
import hk_property_data as hk

print("package 版本:", hk.__version__)
status = hk.fetch_residential_status()
print("数据集生成时间:", status["generated_at"])
print("采集异常:", status["errors"])

# 同时读取 M3 与住宅按揭批核金额，筛选 2025 年 1 月至 2026 年 9 月
rows = hk.fetch_residential(
    series=["hk_m3_hkd", "hk_mortgage_approved_amount"],
    start="2025-01",
    end="2026-09",
)
print("记录数:", len(rows))
for row in rows[-5:]:
    print(row["metric_id"], row["date"], row["value"], row["unit"])
```

如果环境已有 pandas，可在同一文件末尾添加以下代码；运行后在 **Variable Explorer** 打开 `df` 查看表格：

```python
import pandas as pd

df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values(["metric_id", "date"]).reset_index(drop=True)
print(df[["metric_id", "date", "value", "unit"]].tail())

# 在已读入的 DataFrame 内继续筛选，不产生新的网络请求
m3 = df.loc[
    (df["metric_id"] == "hk_m3_hkd")
    & df["date"].between("2026-01-01", "2026-09-30")
].copy()
print(m3[["date", "value", "unit"]])
```

## Jupyter Notebook

选择 **Python 3.10+ kernel**，下面每个代码块放入一个独立 cell，按顺序执行。JupyterLab 同样适用。

### Cell 1：首次安装，后续运行自动跳过

```python
import sys

print("当前 Python:", sys.version.split()[0])
assert sys.version_info >= (3, 10), "请切换到 Python 3.10 或以上的 kernel。"
try:
    from hk_property_data import fetch_residential
except ImportError:
    %pip install --upgrade "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.3.0-py3-none-any.whl"
else:
    print("读取接口已可用，跳过安装。")
```

`%pip` 使用当前 kernel 的环境，见 [IPython 官方说明](https://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-pip)。如果本次会话已经导入过旧版 package，升级后先 **Restart Kernel**，再从 Cell 2 运行。不要把 `%pip` 放进普通 `.py` 文件。上面的检查不会自动升级已有的读取接口；只有明确要更新 package 版本时，才单独执行对应版本的 `%pip install --upgrade ...`，数据更新无需重装。

### Cell 2：导入并检查数据集状态

```python
import hk_property_data as hk

print("package 版本:", hk.__version__)
status = hk.fetch_residential_status()
print("数据集生成时间:", status["generated_at"])
print("采集异常:", status["errors"])
print("利率发布说明:", status.get("rate_release_notes", []))
```

`generated_at` 是数据集生成时间，不是所有指标的最新月份。每条记录的 `date` / `period` 才是其观察日期／统计期间；官方月度数据会晚于当前日期。

### Cell 3：按指标和月份读取

```python
rows = hk.fetch_residential(
    series=["rvd_1_4_all_classes", "rvd_1_3_all_classes"],
    start="2025-01",
    end="2026-09",
)
print("记录数:", len(rows))
for row in rows[-5:]:
    print(row["metric_id"], row["date"], row["value"], row["unit"])
```

这两个指标分别是住宅价格指数和租金指数。将 `series` 改为下方指标表中的 ID，即可读取其他序列；将 `end` 删除或设为 `None`，即可读到最新可用记录。

### Cell 4：按具体日期读取每日 HIBOR

```python
hibor_rows = hk.fetch_residential(
    series="hk_hibor_1m_daily",
    start="2026-10-01",
    end="2026-10-31",
)
for row in hibor_rows[-5:]:
    print(row["date"], row["value"], row["unit"])
```

这是官方发布的每日记录，非发布日不会补值；不能把“未发布”解释为利率为零。

### Cell 5：可选，转换成 pandas 表格并继续筛选

以下使用已有的 pandas；若环境尚未安装，可先在单独 cell 执行 `%pip install pandas`。

```python
import pandas as pd

df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values(["metric_id", "date"]).reset_index(drop=True)
display(df[["metric_id", "date", "value", "unit"]].tail(10))

price_2026 = df.loc[
    (df["metric_id"] == "rvd_1_4_all_classes")
    & df["date"].between("2026-01-01", "2026-09-30")
].copy()
display(price_2026[["date", "value", "unit"]])
```

## 常用指标与筛选规则

| 指标 ID（`series`） | 内容 |
| --- | --- |
| `rvd_1_4_all_classes` | RVD 住宅价格指数：所有类别 |
| `rvd_1_3_all_classes` | RVD 住宅租金指数：所有类别 |
| `hk_residential_sales_count` | 住宅买卖合约登记宗数 |
| `hk_mortgage_approved_amount` | 新批住宅按揭金额，HKD million |
| `hk_m3_hkd` | 港元 M3，HKD million |
| `hk_hibor_1m_daily` | 每日 1 个月 HIBOR，% p.a. |
| `hk_prime_rate_hsbc_effective` | HSBC Prime，按利率生效日记录，% p.a. |

完整指标表见 [Excel](https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/HK_Residential_Data.xlsx) 的 `Data_Dictionary`，其中包含来源、单位和实际覆盖范围。

- `series="一个ID"` 读取一个指标，`series=["ID1", "ID2"]` 读取多个；省略则选取全部指标。拼错或不存在的 ID 返回空列表。
- `start` 和 `end` 按观察日期筛选，**包含边界**。`end="2026-09"` 包含整个 9 月，`end="2026-09-15"` 只到 9 月 15 日。
- 不填 `start` / `end` 表示该侧不限制；各指标从自身最早可用记录开始。统一采集起点为 2002 年，并不代表每个指标都覆盖完整历史。
- `value` 为数字或 `None`，零与缺失分开；来源、单位、频率和标记仍保留。季度和年度序列保留原频率，不自动展开成月份。

## SQL

在 Spyder 或 Jupyter 中运行相同的 Python 代码，将选中的记录放入**本地内存中的 SQLite**，再用 SQL 查询：

```python
from hk_property_data import connect_residential

conn = connect_residential(
    series="hk_mortgage_approved_amount",
    start="2025-01",
    end="2026-09",
)
try:
    result = conn.execute("""
        SELECT date, value, unit
        FROM observations
        WHERE value IS NOT NULL
        ORDER BY date DESC
        LIMIT 5
    """).fetchall()
    print(result)
finally:
    conn.close()
```

GitHub 提供数据文件，SQL 在本地内存中执行。这里不会保存 `.sqlite` 文件；连接只读，使用后 `close()` 释放内存。需要 DataFrame 时，在关闭连接前调用 `pd.read_sql_query(sql, conn)`。

## 接口速查

| 接口 | 返回内容 |
| --- | --- |
| `fetch_residential(series=..., start=..., end=...)` | 符合筛选条件的记录列表 |
| `iter_residential(series=..., start=..., end=...)` | 逐行迭代器，适合不需要保留全部记录的处理 |
| `connect_residential(series=..., start=..., end=...)` | 内存 SQLite 连接，数据表名 `observations` |
| `fetch_residential_status()` | 当前发布的状态字典；不读取整套观察值 |
| `residential_url("csv")` | 对应 Release 文件的 URL |

前三个接口支持 `timeout=90`（秒），状态接口默认 `timeout=30`。格式 URL 支持 `csv`、`csv.gz`、`excel`、`sqlite`、`status`：

```python
from hk_property_data import residential_url

print(residential_url("csv"))
print(residential_url("excel"))
print(residential_url("sqlite"))
```

需要使用 Excel、外部 SQLite 工具或离线分析时，可以主动下载文件。普通 SQLite 客户端通常需要本地文件；不想保存文件时使用上面的 `connect_residential()`。

## 内存与更新方式

读取器流式读取 GitHub 的 `observations.csv.gz` 并逐步解压。筛选在客户端完成，因此仍会传输压缩数据，但 `fetch_residential()` 只保留选中的记录。列表、DataFrame 和 SQL 表仍占内存；无筛选地读取全库会保留全库记录。

需要逐行处理时，用以下方式确保迭代结束或提前退出时关闭网络连接：

```python
from contextlib import closing
from hk_property_data import iter_residential

with closing(iter_residential(series="hk_hibor_1m_daily", start="2026-01")) as stream:
    for count, row in enumerate(stream, start=1):
        # 在这里执行逐行处理；示例只输出前三条
        print(row["date"], row["value"])
        # 如需处理全部记录，删除下面两行
        if count == 3:
            break
```

已有的 `rows`、`df` 或 SQL 连接不会自动刷新。重新调用读取函数才会获取最新成功发布的数据；状态与观察值是独立请求，发布切换期间两者可能来自相邻批次。package 不保存持久数据缓存，安装代码本身会占用少量磁盘空间。

## Faster access

安装、导入和读取数据是三个不同步骤。`import hk_property_data` 只加载本地代码，不访问 GitHub。反复执行 `%pip install --upgrade ...` 则仍可能检查或下载安装包；上述安装检查可避免日常重复运行 pip。pip 自身的安装缓存可减少重复下载，因此示例保留默认缓存行为，见 [pip 官方缓存说明](https://pip.pypa.io/en/stable/topics/caching/)。这是小型安装包的缓存，与住宅数据缓存分开。

`fetch_residential()` 当前每次都会读取整份压缩 CSV，再在本地筛选。即使只选一个指标，也需要 GitHub 的连接、跳转和传输时间。日期和指标筛选减少保留的结果，不是服务端查询条件；`fetch_residential_status()` 也会产生一次独立请求。日常分析时，建议一次读入需要的指标，然后直接筛选已有结果：

```python
import time
import hk_property_data as hk

t0 = time.perf_counter()
analysis_rows = hk.fetch_residential(
    series=["rvd_1_4_all_classes", "rvd_1_3_all_classes", "hk_m3_hkd"],
    start="2025-01",
)
print(f"从 GitHub 读取: {time.perf_counter() - t0:.2f} 秒，{len(analysis_rows)} 条记录")

# 以下仅筛选已读入的记录；更改日期或指标后重跑这部分，无需再次联网
t0 = time.perf_counter()
selected_rows = [
    row for row in analysis_rows
    if row["metric_id"] == "hk_m3_hkd"
    and "2026-01-01" <= row["date"] <= "2026-09-30"
]
print(f"内存筛选: {time.perf_counter() - t0:.6f} 秒，{len(selected_rows)} 条记录")
```

在 Notebook 中，可以把读取和内存筛选放在不同 cell；只有需要更新数据，或读取之前未选入的指标／日期时，才重跑网络读取部分。内存记录随 kernel 关闭而释放，不会保存到磁盘。

2026-11-05 在一台 Mac 的 Python 3.12 环境中，对 `rvd_1_4_all_classes` 的 `2025-01` 至 `2026-09` 查询连续实测为 **14.10、6.79、2.58 秒**；最慢的一次仅建立初次 GitHub HTTPS 连接就花了约 **11.98 秒**。将相同响应放在内存中解析，耗时约 **0.27 秒**，返回完全相同的 21 行。每次远程查询仍扫描 72,142 行：压缩 CSV 为 661 KB，解压后约 30.85 MB。

当前访问路径为 `github.com` → HTTP 302 跳转 → `release-assets.githubusercontent.com`。读取器每次重新联网，无会话缓存；连接等待波动会直接影响每次查询。上述连接计时包含 TCP／代理／TLS 建连，尚未区分其具体原因，不能据此断言是某个网络服务故障。这些测量也不是速度保证。另一次测量中，单指标与两个指标合并查询均约 2.84 秒，说明合并请求可以减少重复连接。

旧式 `archive/refs/heads/main.zip` 安装会下载整个源码仓库，`refresh()` 会在本地抓取官方数据。日常读取已发布数据使用本指南的 wheel 和 `fetch_residential()`。

## 常见问题

| 情况 | 处理方法 |
| --- | --- |
| `requires a different Python` | 当前解释器低于 Python 3.10；在 Spyder / Jupyter 切换到 Python 3.10+ 环境，再安装 package。 |
| `ModuleNotFoundError: No module named 'hk_property_data'` | 在出错的 console / kernel 打印 `sys.executable`，按对应环境的安装步骤重装；不要只在另一个终端环境安装。 |
| 安装后仍是旧版，或缺少 `fetch_residential` | 重启 kernel，再检查 `hk_property_data.__version__` 和 `hk_property_data.__file__`；自己的脚本不要命名为 `hk_property_data.py`。 |
| Spyder 环境没有 pip 或无法安装 | 先连接一个可自行安装 package 的 Python 环境，见前面的 Spyder 官方环境说明。 |
| `SyntaxError` 出现在安装命令 | Spyder `.py` 文件使用普通 Python；Jupyter cell 使用 `%pip`；终端才使用 `python -m pip`。 |
| 返回空列表 | 检查指标 ID、日期范围和该序列的实际覆盖期；空结果不代表零。 |
| `CloudDataError` | 网络、GitHub 文件或数据格式读取失败；恢复连接后重试，不会静默退回本地旧文件。 |

流式迭代遇到中途网络错误时，前面已收到的行只是部分结果，不能视为完整数据。失败的 SQL 加载会关闭部分数据库并报错。非法筛选参数抛出 `ValueError`。

旧版 `fetch_dataset()` / `fetch_status()` 仍是旧 dashboard 的兼容接口，其更新流程已暂停。当前住宅数据使用本文的 `*_residential` 接口。独立抓取官方源数据的方法见 [RESIDENTIAL_DATA.md](RESIDENTIAL_DATA.md)，维护结构见 [RESIDENTIAL_ARCHITECTURE.md](docs/RESIDENTIAL_ARCHITECTURE.md)。
