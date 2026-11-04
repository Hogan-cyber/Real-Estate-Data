# Overview 数据口径与展示审计

核查日期：2026-11-04（香港）。审计基线：`d39aec0be4b9da9c3ac8b57e12b4b41484d218fb`，当时的 `src/data.json` 生成于 `2026-11-04T06:09:24.555071+00:00`。

本文审查该基线的 Overview 代码、保存数据与官方数据源，不将当前工作区中尚未发布的按揭共同融资、历史扩充、来源替换或界面修改视为线上功能。本文落盘不等于相关改动已发布；最终线上版本须另核验提交、部署和加载的数据。该审计未重新验证浏览器已加载的发布构建。

## 结论和实查证据

当前基线 Overview 的取数及同比、环比计算未发现数值错误；仍有统计范围、不同月份和精度说明不足的展示风险。数值正确不等于任何读法都正确。

- 实时下载差饷物业估价署 `1.3M.csv`、`1.4M.csv`、`5.1M.csv`，分别对比保存的 2,664、2,664、1,660 个观察值，共 **6,988 个值及原始 flags，差异为零**。该范围含当前未在首页绘出的类别组合，覆盖首页所用系列。
- 实时下载土地注册处最新政府新闻稿附件，第 5 页确认 2026-10 住宅登记总数 4,512，2026-09 为 4,761，2025-10 为 5,714。
- 实时读取土地注册处一手／二手 JSON：2026-09 分别为 1,502、3,259；2026-10 对应字段仍为空，不能估拆或填零。
- 当前保存的 24 个分项齐全月份，一手宗数加二手宗数全部等于总宗数；全量月度数据不存在重复 `(metric_id, period)`。
- 金管局 2026-09 半年度报告第 24 页明确披露新造按揭平均利率 3.26%，最新明确观察月为 2026-07。
- 已读取当前绑定的差估署 2026-10 补编 PDF 第 26 页原文，核对落成、预测、比例和范围脚注。
- 当前基线 `refresh.errors=[]`。PDF与CSV的148个历史差异在保存状态中列为已确认的暂定数据修订；首页价格、租金、收益率使用最新CSV，供应使用PDF，不能把不同版本机械要求相等。

上述是当日检查结果，不保证未来源文件不修订。检查时间、观察月份、报告刊期必须分别保留。

## 九个首页组件

以下显示值指该基线的默认日期期间；保存链接中的筛选及图形状态可能改变用户实际看到的视图。

| 组件 | 来源和系列 | 当前显示、公式及单位 | 期间筛选 | 含义和限制 |
|---|---|---|---|---|
| **Home prices · year on year** | 差估署[表1.4月度CSV](https://www.rvd.gov.hk/datagovhk/1.4M.csv)，`rvd_1_4_all_classes` | 2026-09 指数 **320.8**，1999=100，P。YoY **+9.34%**=`(320.8/293.4−1)×100`，基期2025-09；MoM **+0.19%**=`(320.8/320.2−1)×100`，基期2026-08。 | 取期间内最新有效值；精确比较月份从完整历史查找，可在显示期间外。 | 官方全类别指数，不是五类简单平均或平均尺价。售价统计排除一手住宅销售；基线首页图面未突出，来源定义已有说明。 |
| **Rents · year on year** | 差估署[表1.3月度CSV](https://www.rvd.gov.hk/datagovhk/1.3M.csv)，`rvd_1_3_all_classes` | 2026-09 指数 **212.2**，1999=100，P。YoY **+6.15%**=`(212.2/199.9−1)×100`，基期2025-09；MoM **+0.47%**=`(212.2/211.2−1)×100`，基期2026-08。 | 同房价卡。 | 私人住宅租金指数变化，不是港元月租或全部现有租约平均加租幅度。 |
| **Residential sales registrations** | 土地注册处，`hk_residential_sales_count`。最新月为[政府新闻稿附件表5](https://gia.info.gov.hk/general/202611/03/P2026110300276_557525_1_1793678584832.pdf)，早期月为官方JSON。 | 2026-10 **4,512份**；YoY **−21.04%**=`(4512/5714−1)×100`；MoM **−5.23%**=`(4512/4761−1)×100`。整数宗数，无季调。 | 期间内最新有效月份；比较月份可在范围外。 | 一手及二手住宅买卖合约送交登记总数，不是全部楼宇交易；登记月份可能滞后签约日期。 |
| **New mortgage lending rate** | 金管局[2026-09半年度报告第24页](https://www.hkma.gov.hk/media/eng/publication-and-research/bulletin/202609/E_Half-yearly_202609.pdf)，`hk_new_mortgage_rate` | 2026-07 **3.26% p.a.**。直接引用明确观察值，不自行平均，不计算同比环比。保存数据仅有2026-01、2026-07两个明确月份。 | 期间内存在观察才显示；只选2026-08至10月时为空，不把7月向后填充。 | 新造按揭平均贷款利率，不是今天报价、Prime、HIBOR或存量按揭平均利率。报告刊期2026-09不等于观察月2026-07。 |
| **Hong Kong Residential Property Price Index** | 差估署表1.4，`rvd_1_4_class_a`至`rvd_1_4_class_e` | 2026-09：A **340.4**、B **312.6**、C **307.1**、D **293.0**、E **286.8**，均P；单位1999=100。直接画官方指数，不重新定基或平均。 | 默认绘2020-01至2026-09；单击图例隐藏／显示，双击独看一条；筛选不重算指数。 | 五条线按实用面积分类。A指数高于E不代表A单位更贵，只是相对各自基期的指数水平不同；不是港元售价或尺价，也不代表一手价格。 |
| **Hong Kong Residential Rental Index · All classes** | 差估署表1.3，`rvd_1_3_all_classes` | 单条全类别指数，最新2026-09 **212.2**，P；1999=100。 | 默认2020-01至2026-09；期间和图内缩放影响显示。 | 与租金KPI同源，图是水平、卡是增长率；不以平均租金重新推算指数。 |
| **Residential sales registrations · primary & secondary** | 土地注册处[宗数JSON](https://www.landreg.gov.hk/json/monthly_agt-pri/agt-primary/t1.json)，`hk_residential_primary_sales_count`／`hk_residential_secondary_sales_count` | 最新2026-09 **一手1,502份、二手3,259份**，合计4,761；基线历史2024-10至2026-09，共24个月。 | 只画期间内已公布分项，不用总数估拆10月；Y轴从零。 | 一手通常指发展商出售，二手指其他卖方。总数卡4,512属于10月，分项合计4,761属于9月，不能误当同月对账失败。 |
| **Residential yields by size class** | 差估署[表5.1月度CSV](https://www.rvd.gov.hk/datagovhk/5.1M.csv)，`rvd_5_1_domestic_class_a`至`class_e` | 2026-08：A **3.5%**、B **3.1%**、C **2.8%**、D **2.6%**、E **2.3%**，均P。直接读官方值。 | 取期间内表5.1最新月的五类；标题带月，Y轴从零；期间无值则为空。 | 统计市场回报率，不是某套物业净收益率，不用租金指数除价格指数。图面尚未突出暂定标记。 |
| **Housing supply · latest report** | 差估署[2026-10每月补编表6.1，PDF第26页](https://www.rvd.gov.hk/doc/en/statistics/full.pdf)，`row_label='Overall'` | 累计落成 **8,987套**，2026-01至08；2026全年预测 **16,975套**；官方整数比例 **53%**，基线格式化为53.00%。原比例来自PDF，无网站重算。 | **不受日期筛选影响**，始终使用保存的最新报告；现有脚注已经说明。 | 是私人住宅落成及全年预测，不是全港所有住房供应或可售库存。PDF规定不含村屋、包括Starter Homes资助出售单位；预测为年初估计。累计修订不能当作某月新增。 |

面积分类为实用面积：A<40平方米；B40–69.9；C70–99.9；D100–159.9；E≥160。

## 官方统计方法和范围

[差估署技术附注](https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf)第8、9、11节支持以下区别：平均价格／租金受成交组合影响；指数借助应课差饷租值调整质量差异。住宅综合指数按本月和前11个月交易宗数加权。住宅售价分析排除一手、带租约等不合口径成交。住宅租赁分析主要按新租约生效月，租金剔除差饷、管理费等；无法观察的优惠仍可能影响可比性。租售统计范围可含村屋及符合条件的已解除限制资助住宅，不能套用供应表的排除范围。市场回报率比较租金／应课差饷租值与售价／应课差饷租值因子，两组物业可能不同。

[土地注册处一手二手定义页](https://www.landreg.gov.hk/en/monthly/agt-primary.htm)及[2026-10统计政府新闻稿](https://www.info.gov.hk/gia/general/202611/03/P2026110300276.htm)说明：仍受限制的资助出售单位不纳入相关销售统计，满足解除限制及补地价条件者依官方定义处理；文件可在交易后30天内送交登记，因此月度登记不等于当月签约。2026-10新闻稿于2026-11-03公布，最新总数不能据此推断分项已齐。

金管局半年度报告明确披露3.26%从2026年1月至7月保持不变；此产品保守保留明确端点观察月，没有将文字区间扩展为新造月度序列。该限制必须与报告观察期一同解释。

供应表原文特别规定所有数均不含村屋、均包括Starter Homes资助出售单位；其口径不能简写成“排除所有资助住房”。2026年全年预测为年初估计，不是截至8月的重新预测。8,987/16,975×100=52.942562592%，官方四舍五入为53%。

## 代码计算与筛选规则

相关实现：`src/content/dashboard/DashboardContent.jsx` 的 `Overview`、`MomentumCard`、`Kpi`；`clear-trend.js` 的 `exactChange`／`monthlySegments`；`reference-period.js`；`percentage-format.js`；`ClearTrend.jsx`。

```text
selected_rows = rows where start_date <= row.date <= end_date
latest_metric = latest non-null observation of that metric in selected_rows
prior_period = exact calendar month, offset by 1 or 12 months
YoY_or_MoM_percent = (current / exact_prior - 1) * 100
missing_or_zero_comparator -> no calculated percentage
```

- `MomentumCard`调用`exactChange(row, all,12/1)`；销售卡`growth`使用相同精确日历月份公式。基期查完整`all`，不受显示窗口截断。无比较月留空，不拿“上一条可用记录”冒充上月。
- 百分数保存为百分点数值：3.26即3.26%，`formatPercent`只格式化，不再次乘100。收益率图字段`Yield (%)`明确按百分点值格式化。
- 默认日期范围为`2020-01-01..2026-11-04`；终点来自全站每日利率等可用日期，不意味着首页月度指标已有11月数据。RVD月度数据在此产品从1999-01保存，各图仍保留自己的最新月。
- 观察日期按月末存储，只用于筛选及排序，不意味着所有经济活动发生在月末。选月后需点Apply period；日期范围跨页面共享。
- **选择历史期间不是历史可知数据回放**。仍使用本次获取的最新修订值，而非当时发布版本，不能据此声称消除回测前视偏差。
- 默认月度折线按真实日期定位，只连接连续月份；空值或缺月断线，不插值填数据。价格和租金图Y轴不从零开始；销量图及收益率柱图从零开始。隐藏线后会重新调整Y轴。
- 图内缩放只改变该图显示，不改变顶部KPI。当前Reset filters只重置全局日期，不清除单图缩放或隐藏线状态。
- 供应从PDF独立查询读取，非月度查询；年度、累计及预测没有相加。`Completions Overall`、`Forecast completions Overall`、`Completions / forecast %`分别选取。
- P为暂定；首页价格租金KPI和默认折线端点显示P；来源数据保留Z少于20宗等标记。收益率五项P没有同样突出。最新值为空不填零。

## 已确认展示风险与建议文案

这些是审计基线上的问题和建议，写入本文不代表已完成修改。

1. **价格范围提示**：房价卡／图补上 `Private residential resale prices; primary sales excluded. Index: 1999 = 100.` 来源面板已有定义，默认首页也应可见。
2. **五线图理解**：补上 `Each class is indexed to 1999 = 100. Index levels compare change from the base year, not dollar prices between classes.`
3. **销量发布缺口**：动态文案宜为 `Total registrations: Oct 2026. Primary / secondary breakdown: Sep 2026; October components are not yet published.` 应根据各系列最新月生成，不能长期写死。
4. **按揭利率**：标题可用 `Average new mortgage lending rate`；注释 `Latest explicitly reported observation; Jul 2026, published in the Sep 2026 HKMA report.` 刊期、观察月从源字段取。
5. **收益率**：补上 `Provisional official market yields. Rental and sale samples may differ; these are not property-specific net returns.`
6. **供应标题和口径**：用 `Private residential completions & annual forecast`；注释 `Excludes village houses; includes Starter Homes subsidised sale flats. Forecast made at the beginning of the year.` 保留独立于日期筛选及累计修订说明。
7. **供应比例精度**：官方只公布53%，不应格式化53.00%。若另算52.94%，必须标记为按原数计算，与官方舍入值区分。
8. **预测状态**：PDF脚注只将落成数标为暂定，解析器将整行全部单元格`provisional=true`，所以预测也显示Provisional。预测值无误，但界面优先标`Annual forecast · beginning-of-year estimate`更准确。
9. **缩放图形一致性**：`ClearTrend`月图缩放时转交通用`ChartRenderer`，默认逐月直线变成`type="monotone"`，端点标签也消失。未来所有系列同时缺某月且没有空行时，通用绘图可能跨月连接。当前首页历史连续，未发现因此产生当前数值错误；后续应统一渲染规则。
10. **来源失败就地提示**：当前没有来源失败。完整错误列表位于Data & Updates，首页无自动错误横幅；以后若保留旧值，应在相关卡图直接标`Source refresh failed; showing last valid observation`及最近成功时间。不要把检查成功但观察月较早误称失败。

## 政府来源边界

本文九个Overview组件实际来源均为差估署、土地注册处／政府新闻稿及金管局，符合政府来源限制。**该结论不适用于基线全站**：Money & Rates日度／生效利率仍使用HSBC、HKAB；这些非政府直接来源须另行替换或停用，不能凭借本页审计宣布全站政府来源合规。未发布的共同融资或其他扩展不纳入本审计的已上线结论。

## 同日补充：政府利率入口替换核查（工作区改动，非发布证明）

2026-11-04另行核实可保留现有观察口径的金管局发布入口。这里的“政府来源”指从金管局直接取得其发布数据；基准仍分别是HSBC报价及HKAB定盘，不能声称基准由政府设定。

| 用途 | 官方API／文档及字段 | 同表官方Excel与核实结构 | 当日真实采集结果 |
|---|---|---|---|
| Prime生效日历史 | [hkd-ir-effdates文档](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hkd-ir-effdates/)；[API](https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hkd-ir-effdates)；`effect_date`、`best_lending_rate`，年率百分数 | [T060401.xls](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060401.xls)，sheet `T6.4.1`；日期为第1列Excel日期，利率为第11列；标题为Rates as at effective dates，脚注明确HSBC | 205条有效利率记录，最新生效日2025-10-31，5.00%；频率E。日期不能改成抓取日，也不生成每日观察。 |
| HIBOR 1M／3M日度定盘 | [hk-interbank-ir-daily文档](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily/)；[API fixing段](https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily?segment=hibor.fixing)；`end_of_day`、`ir_1m`、`ir_3m`，11:15定盘、年率百分数 | [T060303.xls](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060303.xls)，sheet `T6.3.3 (HIBOR Fixing)`；第1列Excel日期，第6／7列为1M／3M。拒绝同书已停用的`HIBOR`收市系列及`HONIA` | 两期限共14,946条记录，最新2026-10-30：1M 2.70923%、3M 3.21256%；频率D。较新1M另由金管局每日货币统计补充，3M不由1M推算。 |

表号必须区分：6.3.1是期末数，6.3.2是期平均数，6.3.3才是日度；6.4.1是利率生效日，6.4.2是期平均数。本次真实采集因API请求受阻使用同表官方Excel后备，成功核验日期、数值、表头及口径。月均历史仍只使用原有官方6.3.2／6.4.2，不由日度数据合成。

工作区的`hk_latest_rates.py`已替换采集入口，并在成功合并和失败保留两条路径中排除旧非政府来源记录；政府来源失败只保留先前已验证的政府观察，不保留私人入口缓存冒充政府值。专项测试覆盖不同期限日期、旧来源迁移、API后备、缺失／冲突、错误表头及导出频率分离。是否已上线和是否已完成全部整合测试，须查最终交付记录。
