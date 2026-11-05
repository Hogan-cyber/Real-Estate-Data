# 全部指标字典 / Complete indicator guide

本次发布共 **163 个指标**；自动生成时间：`2026-11-05T07:25:27.213748+00:00`。
每个 ID 都有独立说明。日期范围只统计非空值；范围内仍可能缺期。
官方数据与推算共存在同一数据集：用 status、flags、note 区分。

## 怎样读 RVD 指标名称

`rvd_1_3_all_classes` = RVD 的 1.3 租金指数表 + 全部住宅面积类别。
`rvd_1_3_allclass` 不是有效 ID；请使用目录中的完整拼写。
`1_1` 平均租金；`1_2` 平均售价；`1_3` 租金指数；`1_4` 售价指数；`1_5` 选定屋苑售价指数。
`all_classes` 为全部面积类别；`class_a` 至 `class_e` 为具体面积类别，`classes_a_b_c` / `classes_d_e` 为合并类别。
实用面积：A <40 m²；B 40–69.9 m²；C 70–99.9 m²；D 100–159.9 m²；E ≥160 m²。
`hong_kong` 港岛；`kowloon` 九龙；`new_territories` 新界；`urban` 市区；`all` 合计。
[RVD 技术附注](https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) · [RVD 数据字典](https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf)

## 单位与频率

`HKD million` 为百万港元，乘 1,000,000 才是港元；`1999=100` 为指数，不是货币。
`fraction` 的 0.25 表示 25%；`%` 或 `% p.a.` 的 2.5 已表示 2.5%，不要再乘 100。
`deeds` / `份` 是登记文书宗数；`loans` 是贷款宗数；`estimated loans` 是模型推算宗数，保留小数以便核对。
`D` 每日；`M` 每月；`Q` 每季；`A` 每年；`E` 利率生效事件。不同频率不自动插值。

## 指标目录

## Sales & Rent / Transactions

### `hk_all_building_sales_count`

- 名称：全部楼宇买卖合约登记宗数
- 含义：住宅和非住宅楼宇买卖合约的登记宗数，排除土地买卖；使用文书宗数而非涉及单位数。
- 单位：`deeds`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://www.landreg.gov.hk/json/monthly_stat/stat1026/t1.json)
- 源表／计算表：Consolidated Monthly Statistics, Table 1, item 1；字段／公式：Number of Urban deeds received for registration (ASP Building Units) + Number of New Territories deeds received for registration (ASP Building Units)。
- 口径备注：全部楼宇买卖合约登记文书份数；包含住宅及非住宅，不含土地买卖合约。不是涉及单位数；市区及新界文书份数相加。登记月不一定是成交月。

### `hk_residential_primary_sales_count`

- 名称：一手住宅楼宇买卖合约登记宗数
- 含义：一手住宅楼宇买卖合约登记宗数；登记时间不一定是成交时间。这里统计合约份数，不是贷款宗数。
- 单位：`份`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://www.landreg.gov.hk/json/monthly_agt-pri/agt-primary/t1.json)
- 源表／计算表：见来源文件；字段／公式：一手住宅楼宇买卖合约登记宗数。
- 口径备注：直接使用土地注册处公布的住宅分项或合计；统计月份为送交登记月份，并非签约月份；非所有楼宇口径。金额为官方按百万港元公布的数值，分项四舍五入可能不等于合计。不包括尚受转售限制的资助出售住宅；已补地价并解除限制者按官方定义纳入。官方JSON未提供最初发布日期；HTTP最后修改时间不能视为发布日期。as_of只筛选观察月份，数据采用抓取时官网最新修订值。 来源HTTP最后修改：Mon, 12 Oct 2026 04:00:03 GMT。

### `hk_residential_primary_sales_value`

- 名称：一手住宅楼宇买卖合约登记金额
- 含义：一手住宅楼宇买卖合约登记金额；登记时间不一定是成交时间。金额是物业买卖价而非贷款额。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://www.landreg.gov.hk/json/monthly_agt-pri/agt-primary/t2.json)
- 源表／计算表：见来源文件；字段／公式：一手住宅楼宇买卖合约登记金额。
- 口径备注：直接使用土地注册处公布的住宅分项或合计；统计月份为送交登记月份，并非签约月份；非所有楼宇口径。金额为官方按百万港元公布的数值，分项四舍五入可能不等于合计。不包括尚受转售限制的资助出售住宅；已补地价并解除限制者按官方定义纳入。官方JSON未提供最初发布日期；HTTP最后修改时间不能视为发布日期。as_of只筛选观察月份，数据采用抓取时官网最新修订值。 来源HTTP最后修改：Mon, 12 Oct 2026 04:00:03 GMT。

### `hk_residential_sales_count`

- 名称：住宅楼宇买卖合约登记宗数
- 含义：住宅楼宇买卖合约登记宗数；登记时间不一定是成交时间。这里统计合约份数，不是贷款宗数。
- 单位：`份`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://gia.info.gov.hk/general/202611/03/P2026110300276_557525_1_1793678584832.pdf)
- 源表／计算表：5；字段／公式：Table 5, page 5。
- 口径备注：Official Land Registry monthly annex: residential registration totals, not all-building totals. Consideration is published in HKD million, not the rounded headline billions. This annex does not publish the primary/secondary breakdown; missing components are not estimated. Registration month may follow the transaction month. Restricted subsidised units are excluded under official definitions.

### `hk_residential_sales_value`

- 名称：住宅楼宇买卖合约登记金额
- 含义：住宅楼宇买卖合约登记金额；登记时间不一定是成交时间。金额是物业买卖价而非贷款额。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://gia.info.gov.hk/general/202611/03/P2026110300276_557525_1_1793678584832.pdf)
- 源表／计算表：5；字段／公式：Table 5, page 5。
- 口径备注：Official Land Registry monthly annex: residential registration totals, not all-building totals. Consideration is published in HKD million, not the rounded headline billions. This annex does not publish the primary/secondary breakdown; missing components are not estimated. Registration month may follow the transaction month. Restricted subsidised units are excluded under official definitions.

### `hk_residential_secondary_sales_count`

- 名称：二手住宅楼宇买卖合约登记宗数
- 含义：二手住宅楼宇买卖合约登记宗数；登记时间不一定是成交时间。这里统计合约份数，不是贷款宗数。
- 单位：`份`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://www.landreg.gov.hk/json/monthly_agt-pri/agt-primary/t1.json)
- 源表／计算表：见来源文件；字段／公式：二手住宅楼宇买卖合约登记宗数。
- 口径备注：直接使用土地注册处公布的住宅分项或合计；统计月份为送交登记月份，并非签约月份；非所有楼宇口径。金额为官方按百万港元公布的数值，分项四舍五入可能不等于合计。不包括尚受转售限制的资助出售住宅；已补地价并解除限制者按官方定义纳入。官方JSON未提供最初发布日期；HTTP最后修改时间不能视为发布日期。as_of只筛选观察月份，数据采用抓取时官网最新修订值。 来源HTTP最后修改：Mon, 12 Oct 2026 04:00:03 GMT。

### `hk_residential_secondary_sales_value`

- 名称：二手住宅楼宇买卖合约登记金额
- 含义：二手住宅楼宇买卖合约登记金额；登记时间不一定是成交时间。金额是物业买卖价而非贷款额。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://www.landreg.gov.hk/json/monthly_agt-pri/agt-primary/t2.json)
- 源表／计算表：见来源文件；字段／公式：二手住宅楼宇买卖合约登记金额。
- 口径备注：直接使用土地注册处公布的住宅分项或合计；统计月份为送交登记月份，并非签约月份；非所有楼宇口径。金额为官方按百万港元公布的数值，分项四舍五入可能不等于合计。不包括尚受转售限制的资助出售住宅；已补地价并解除限制者按官方定义纳入。官方JSON未提供最初发布日期；HTTP最后修改时间不能视为发布日期。as_of只筛选观察月份，数据采用抓取时官网最新修订值。 来源HTTP最后修改：Mon, 12 Oct 2026 04:00:03 GMT。

## Sales & Rent / Price_Indices

### `rvd_1_4_all_classes`

- 名称：Price index — All Classes
- 含义：私人住宅售价指数：比较价格水平变化，不是平均成交价格。范围：All Classes。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.4M.csv)
- 源表／计算表：1.4；字段／公式：All Classes。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_4_class_a`

- 名称：Price index — Class A
- 含义：私人住宅售价指数：比较价格水平变化，不是平均成交价格。范围：Class A。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.4M.csv)
- 源表／计算表：1.4；字段／公式：Class A。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_4_class_b`

- 名称：Price index — Class B
- 含义：私人住宅售价指数：比较价格水平变化，不是平均成交价格。范围：Class B。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.4M.csv)
- 源表／计算表：1.4；字段／公式：Class B。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_4_class_c`

- 名称：Price index — Class C
- 含义：私人住宅售价指数：比较价格水平变化，不是平均成交价格。范围：Class C。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.4M.csv)
- 源表／计算表：1.4；字段／公式：Class C。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_4_class_d`

- 名称：Price index — Class D
- 含义：私人住宅售价指数：比较价格水平变化，不是平均成交价格。范围：Class D。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.4M.csv)
- 源表／计算表：1.4；字段／公式：Class D。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_4_class_e`

- 名称：Price index — Class E
- 含义：私人住宅售价指数：比较价格水平变化，不是平均成交价格。范围：Class E。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.4M.csv)
- 源表／计算表：1.4；字段／公式：Class E。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_4_classes_a_b_c`

- 名称：Price index — Classes A, B & C
- 含义：私人住宅售价指数：比较价格水平变化，不是平均成交价格。范围：Classes A, B & C。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.4M.csv)
- 源表／计算表：1.4；字段／公式：Classes A, B & C。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_4_classes_d_e`

- 名称：Price index — Classes D & E
- 含义：私人住宅售价指数：比较价格水平变化，不是平均成交价格。范围：Classes D & E。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.4M.csv)
- 源表／计算表：1.4；字段／公式：Classes D & E。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

## Sales & Rent / Prices

### `rvd_1_2_class_a_hong_kong`

- 名称：Average price — Class A Hong Kong
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class A Hong Kong。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class A Hong Kong。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_a_kowloon`

- 名称：Average price — Class A Kowloon
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class A Kowloon。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class A Kowloon。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_a_new_territories`

- 名称：Average price — Class A New Territories
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class A New Territories。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class A New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_b_hong_kong`

- 名称：Average price — Class B Hong Kong
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class B Hong Kong。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class B Hong Kong。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_b_kowloon`

- 名称：Average price — Class B Kowloon
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class B Kowloon。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class B Kowloon。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_b_new_territories`

- 名称：Average price — Class B New Territories
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class B New Territories。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class B New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_c_hong_kong`

- 名称：Average price — Class C Hong Kong
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class C Hong Kong。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class C Hong Kong。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_c_kowloon`

- 名称：Average price — Class C Kowloon
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class C Kowloon。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class C Kowloon。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_c_new_territories`

- 名称：Average price — Class C New Territories
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class C New Territories。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class C New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_d_hong_kong`

- 名称：Average price — Class D Hong Kong
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class D Hong Kong。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class D Hong Kong。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_d_kowloon`

- 名称：Average price — Class D Kowloon
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class D Kowloon。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class D Kowloon。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_d_new_territories`

- 名称：Average price — Class D New Territories
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class D New Territories。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class D New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_e_hong_kong`

- 名称：Average price — Class E Hong Kong
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class E Hong Kong。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`PZ`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class E Hong Kong。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_e_kowloon`

- 名称：Average price — Class E Kowloon
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class E Kowloon。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`PZ`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class E Kowloon。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_2_class_e_new_territories`

- 名称：Average price — Class E New Territories
- 含义：私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响。范围：Class E New Territories。
- 单位：`HKD / sq m`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.2M.csv)
- 源表／计算表：1.2；字段／公式：Class E New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

## Sales & Rent / Rent_Indices

### `rvd_1_3_all_classes`

- 名称：Rental index — All Classes
- 含义：私人住宅租金指数：比较租金水平变化，不是租金金额。范围：All Classes。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.3M.csv)
- 源表／计算表：1.3；字段／公式：All Classes。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_3_class_a`

- 名称：Rental index — Class A
- 含义：私人住宅租金指数：比较租金水平变化，不是租金金额。范围：Class A。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.3M.csv)
- 源表／计算表：1.3；字段／公式：Class A。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_3_class_b`

- 名称：Rental index — Class B
- 含义：私人住宅租金指数：比较租金水平变化，不是租金金额。范围：Class B。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.3M.csv)
- 源表／计算表：1.3；字段／公式：Class B。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_3_class_c`

- 名称：Rental index — Class C
- 含义：私人住宅租金指数：比较租金水平变化，不是租金金额。范围：Class C。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.3M.csv)
- 源表／计算表：1.3；字段／公式：Class C。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_3_class_d`

- 名称：Rental index — Class D
- 含义：私人住宅租金指数：比较租金水平变化，不是租金金额。范围：Class D。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.3M.csv)
- 源表／计算表：1.3；字段／公式：Class D。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_3_class_e`

- 名称：Rental index — Class E
- 含义：私人住宅租金指数：比较租金水平变化，不是租金金额。范围：Class E。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.3M.csv)
- 源表／计算表：1.3；字段／公式：Class E。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_3_classes_a_b_c`

- 名称：Rental index — Classes A, B & C
- 含义：私人住宅租金指数：比较租金水平变化，不是租金金额。范围：Classes A, B & C。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.3M.csv)
- 源表／计算表：1.3；字段／公式：Classes A, B & C。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_3_classes_d_e`

- 名称：Rental index — Classes D & E
- 含义：私人住宅租金指数：比较租金水平变化，不是租金金额。范围：Classes D & E。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.3M.csv)
- 源表／计算表：1.3；字段／公式：Classes D & E。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

## Sales & Rent / Rents

### `rvd_1_1_class_a_hong_kong`

- 名称：Average rent — Class A Hong Kong
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class A Hong Kong。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class A Hong Kong。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_a_kowloon`

- 名称：Average rent — Class A Kowloon
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class A Kowloon。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class A Kowloon。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_a_new_territories`

- 名称：Average rent — Class A New Territories
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class A New Territories。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class A New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_b_hong_kong`

- 名称：Average rent — Class B Hong Kong
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class B Hong Kong。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class B Hong Kong。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_b_kowloon`

- 名称：Average rent — Class B Kowloon
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class B Kowloon。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class B Kowloon。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_b_new_territories`

- 名称：Average rent — Class B New Territories
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class B New Territories。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class B New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_c_hong_kong`

- 名称：Average rent — Class C Hong Kong
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class C Hong Kong。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class C Hong Kong。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_c_kowloon`

- 名称：Average rent — Class C Kowloon
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class C Kowloon。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class C Kowloon。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_c_new_territories`

- 名称：Average rent — Class C New Territories
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class C New Territories。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class C New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_d_hong_kong`

- 名称：Average rent — Class D Hong Kong
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class D Hong Kong。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class D Hong Kong。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_d_kowloon`

- 名称：Average rent — Class D Kowloon
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class D Kowloon。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class D Kowloon。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_d_new_territories`

- 名称：Average rent — Class D New Territories
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class D New Territories。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class D New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_e_hong_kong`

- 名称：Average rent — Class E Hong Kong
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class E Hong Kong。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class E Hong Kong。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_e_kowloon`

- 名称：Average rent — Class E Kowloon
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class E Kowloon。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`PZ`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class E Kowloon。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_1_class_e_new_territories`

- 名称：Average rent — Class E New Territories
- 含义：私人住宅平均租金：每平方米每月租金，会受当月成交组合影响。范围：Class E New Territories。
- 单位：`HKD / sq m / month`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`PZ`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.1M.csv)
- 源表／计算表：1.1；字段／公式：Class E New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

## Sales & Rent / Popular_Developments

### `rvd_1_5_classes_a_b_c_all`

- 名称：Selected popular development price index — Classes A, B & C All
- 含义：选定受欢迎屋苑的私人住宅售价指数；样本范围不同于全市场指数。范围：Classes A, B & C All。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.5M.csv)
- 源表／计算表：1.5；字段／公式：Classes A, B & C All。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_5_classes_a_b_c_new_territories`

- 名称：Selected popular development price index — Classes A, B & C New Territories
- 含义：选定受欢迎屋苑的私人住宅售价指数；样本范围不同于全市场指数。范围：Classes A, B & C New Territories。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.5M.csv)
- 源表／计算表：1.5；字段／公式：Classes A, B & C New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_5_classes_a_b_c_urban`

- 名称：Selected popular development price index — Classes A, B & C Urban
- 含义：选定受欢迎屋苑的私人住宅售价指数；样本范围不同于全市场指数。范围：Classes A, B & C Urban。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.5M.csv)
- 源表／计算表：1.5；字段／公式：Classes A, B & C Urban。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_5_classes_d_e_all`

- 名称：Selected popular development price index — Classes D & E All
- 含义：选定受欢迎屋苑的私人住宅售价指数；样本范围不同于全市场指数。范围：Classes D & E All。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.5M.csv)
- 源表／计算表：1.5；字段／公式：Classes D & E All。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_5_classes_d_e_new_territories`

- 名称：Selected popular development price index — Classes D & E New Territories
- 含义：选定受欢迎屋苑的私人住宅售价指数；样本范围不同于全市场指数。范围：Classes D & E New Territories。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.5M.csv)
- 源表／计算表：1.5；字段／公式：Classes D & E New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_5_classes_d_e_urban`

- 名称：Selected popular development price index — Classes D & E Urban
- 含义：选定受欢迎屋苑的私人住宅售价指数；样本范围不同于全市场指数。范围：Classes D & E Urban。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.5M.csv)
- 源表／计算表：1.5；字段／公式：Classes D & E Urban。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_5_overall_all`

- 名称：Selected popular development price index — Overall All
- 含义：选定受欢迎屋苑的私人住宅售价指数；样本范围不同于全市场指数。范围：Overall All。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.5M.csv)
- 源表／计算表：1.5；字段／公式：Overall All。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_5_overall_new_territories`

- 名称：Selected popular development price index — Overall New Territories
- 含义：选定受欢迎屋苑的私人住宅售价指数；样本范围不同于全市场指数。范围：Overall New Territories。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.5M.csv)
- 源表／计算表：1.5；字段／公式：Overall New Territories。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

### `rvd_1_5_overall_urban`

- 名称：Selected popular development price index — Overall Urban
- 含义：选定受欢迎屋苑的私人住宅售价指数；样本范围不同于全市场指数。范围：Overall Urban。
- 单位：`1999=100`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Provisional；标记：`P`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/1.5M.csv)
- 源表／计算表：1.5；字段／公式：Overall Urban。
- 口径备注：Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.

## Sales & Rent / Supply_Annual

### `rvd_completions_class_a_completions`

- 名称：Completions — Class A (Completions)
- 含义：私人住宅落成量：当年落成的单位数；当年部分数据的截止期见备注。范围：Class A (Completions)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Partial; Provisional；标记：`# Provisional figures (up to 30.09.2026).`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Completions.csv)
- 源表／计算表：completions；字段／公式：Class A (Completions)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Completion figures from 2025 onwards include subsidised sale flats under the Starter Homes for Hong Kong Residents (SH) projects. Year-to-date through 2026-09-30; not a full-year total.

### `rvd_completions_class_b_completions`

- 名称：Completions — Class B (Completions)
- 含义：私人住宅落成量：当年落成的单位数；当年部分数据的截止期见备注。范围：Class B (Completions)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Partial; Provisional；标记：`# Provisional figures (up to 30.09.2026).`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Completions.csv)
- 源表／计算表：completions；字段／公式：Class B (Completions)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Completion figures from 2025 onwards include subsidised sale flats under the Starter Homes for Hong Kong Residents (SH) projects. Year-to-date through 2026-09-30; not a full-year total.

### `rvd_completions_class_c_completions`

- 名称：Completions — Class C (Completions)
- 含义：私人住宅落成量：当年落成的单位数；当年部分数据的截止期见备注。范围：Class C (Completions)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Partial; Provisional；标记：`# Provisional figures (up to 30.09.2026).`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Completions.csv)
- 源表／计算表：completions；字段／公式：Class C (Completions)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Completion figures from 2025 onwards include subsidised sale flats under the Starter Homes for Hong Kong Residents (SH) projects. Year-to-date through 2026-09-30; not a full-year total.

### `rvd_completions_class_d_completions`

- 名称：Completions — Class D (Completions)
- 含义：私人住宅落成量：当年落成的单位数；当年部分数据的截止期见备注。范围：Class D (Completions)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Partial; Provisional；标记：`# Provisional figures (up to 30.09.2026).`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Completions.csv)
- 源表／计算表：completions；字段／公式：Class D (Completions)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Completion figures from 2025 onwards include subsidised sale flats under the Starter Homes for Hong Kong Residents (SH) projects. Year-to-date through 2026-09-30; not a full-year total.

### `rvd_completions_class_e_completions`

- 名称：Completions — Class E (Completions)
- 含义：私人住宅落成量：当年落成的单位数；当年部分数据的截止期见备注。范围：Class E (Completions)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Partial; Provisional；标记：`# Provisional figures (up to 30.09.2026).`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Completions.csv)
- 源表／计算表：completions；字段／公式：Class E (Completions)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Completion figures from 2025 onwards include subsidised sale flats under the Starter Homes for Hong Kong Residents (SH) projects. Year-to-date through 2026-09-30; not a full-year total.

### `rvd_completions_total_completions`

- 名称：Completions — Total (Completions)
- 含义：私人住宅落成量：当年落成的单位数；当年部分数据的截止期见备注。范围：Total (Completions)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Partial; Provisional；标记：`# Provisional figures (up to 30.09.2026).`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Completions.csv)
- 源表／计算表：completions；字段／公式：Total (Completions)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Completion figures from 2025 onwards include subsidised sale flats under the Starter Homes for Hong Kong Residents (SH) projects. Year-to-date through 2026-09-30; not a full-year total.

### `rvd_stock_class_a_stock`

- 名称：Year-end stock — Class A (Stock)
- 含义：年末私人住宅存量：已存在的住宅单位数。范围：Class A (Stock)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Stock.csv)
- 源表／计算表：stock；字段／公式：Class A (Stock)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_stock_class_b_stock`

- 名称：Year-end stock — Class B (Stock)
- 含义：年末私人住宅存量：已存在的住宅单位数。范围：Class B (Stock)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Stock.csv)
- 源表／计算表：stock；字段／公式：Class B (Stock)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_stock_class_c_stock`

- 名称：Year-end stock — Class C (Stock)
- 含义：年末私人住宅存量：已存在的住宅单位数。范围：Class C (Stock)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Stock.csv)
- 源表／计算表：stock；字段／公式：Class C (Stock)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_stock_class_d_stock`

- 名称：Year-end stock — Class D (Stock)
- 含义：年末私人住宅存量：已存在的住宅单位数。范围：Class D (Stock)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Stock.csv)
- 源表／计算表：stock；字段／公式：Class D (Stock)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_stock_class_e_stock`

- 名称：Year-end stock — Class E (Stock)
- 含义：年末私人住宅存量：已存在的住宅单位数。范围：Class E (Stock)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Stock.csv)
- 源表／计算表：stock；字段／公式：Class E (Stock)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_stock_total_stock`

- 名称：Year-end stock — Total (Stock)
- 含义：年末私人住宅存量：已存在的住宅单位数。范围：Total (Stock)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Stock.csv)
- 源表／计算表：stock；字段／公式：Total (Stock)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_takeup_take_up_sa_100_m2_or_above`

- 名称：Net take-up — Take up (SA 100 m2 or above)
- 含义：私人住宅净吸纳量：净吸纳单位数，不是成交宗数或落成量。范围：Take up (SA 100 m2 or above)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Take-up.csv)
- 源表／计算表：takeup；字段／公式：Take up (SA 100 m2 or above)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_takeup_take_up_sa_less_than_100_m2`

- 名称：Net take-up — Take Up (SA Less than 100 m2)
- 含义：私人住宅净吸纳量：净吸纳单位数，不是成交宗数或落成量。范围：Take Up (SA Less than 100 m2)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Take-up.csv)
- 源表／计算表：takeup；字段／公式：Take Up (SA Less than 100 m2)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_takeup_take_up_total`

- 名称：Net take-up — Take up (Total)
- 含义：私人住宅净吸纳量：净吸纳单位数，不是成交宗数或落成量。范围：Take up (Total)。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Take-up.csv)
- 源表／计算表：takeup；字段／公式：Take up (Total)。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_vacancy_class_a_vacancy`

- 名称：Year-end vacancy — Class A (Vacancy) - %
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Class A (Vacancy) - %。
- 单位：`fraction`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Class A (Vacancy) - %。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Source percentage column is a fraction: 0.043 = 4.3%; retained without rescaling.

### `rvd_vacancy_class_a_vacancy_unit`

- 名称：Year-end vacancy — Class A (Vacancy) - Unit
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Class A (Vacancy) - Unit。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Class A (Vacancy) - Unit。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_vacancy_class_b_vacancy`

- 名称：Year-end vacancy — Class B (Vacancy) - %
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Class B (Vacancy) - %。
- 单位：`fraction`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Class B (Vacancy) - %。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Source percentage column is a fraction: 0.043 = 4.3%; retained without rescaling.

### `rvd_vacancy_class_b_vacancy_unit`

- 名称：Year-end vacancy — Class B (Vacancy) - Unit
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Class B (Vacancy) - Unit。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Class B (Vacancy) - Unit。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_vacancy_class_c_vacancy`

- 名称：Year-end vacancy — Class C (Vacancy) - %
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Class C (Vacancy) - %。
- 单位：`fraction`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Class C (Vacancy) - %。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Source percentage column is a fraction: 0.043 = 4.3%; retained without rescaling.

### `rvd_vacancy_class_c_vacancy_unit`

- 名称：Year-end vacancy — Class C (Vacancy) - Unit
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Class C (Vacancy) - Unit。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Class C (Vacancy) - Unit。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_vacancy_class_d_vacancy`

- 名称：Year-end vacancy — Class D (Vacancy) - %
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Class D (Vacancy) - %。
- 单位：`fraction`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Class D (Vacancy) - %。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Source percentage column is a fraction: 0.043 = 4.3%; retained without rescaling.

### `rvd_vacancy_class_d_vacancy_unit`

- 名称：Year-end vacancy — Class D (Vacancy) - Unit
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Class D (Vacancy) - Unit。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Class D (Vacancy) - Unit。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_vacancy_class_e_vacancy`

- 名称：Year-end vacancy — Class E (Vacancy) - %
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Class E (Vacancy) - %。
- 单位：`fraction`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Class E (Vacancy) - %。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Source percentage column is a fraction: 0.043 = 4.3%; retained without rescaling.

### `rvd_vacancy_class_e_vacancy_unit`

- 名称：Year-end vacancy — Class E (Vacancy) - Unit
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Class E (Vacancy) - Unit。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Class E (Vacancy) - Unit。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

### `rvd_vacancy_total_vacancy`

- 名称：Year-end vacancy — Total (Vacancy) - %
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Total (Vacancy) - %。
- 单位：`fraction`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Total (Vacancy) - %。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage. Source percentage column is a fraction: 0.043 = 4.3%; retained without rescaling.

### `rvd_vacancy_total_vacancy_unit`

- 名称：Year-end vacancy — Total (Vacancy) - Unit
- 含义：年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例。范围：Total (Vacancy) - Unit。
- 单位：`dwellings`；频率：`A`；非空值范围：2002-12-31 — 2025-12-31。
- 最新记录（2025-12-31）状态：Published；标记：`无`。
- 最新记录来源：Rating and Valuation Department。[来源 1](https://www.rvd.gov.hk/datagovhk/Private_Domestic-Vacancy.csv)
- 源表／计算表：vacancy；字段／公式：Total (Vacancy) - Unit。
- 口径备注：Official RVD CSV. Supply definitions follow the table-specific data dictionary (https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes (https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 onwards exclude village houses. The generic Technical Notes (https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; do not treat 2002 and 2003 as safely like-for-like coverage.

## Mortgage / Mortgage_Monthly

### `hk_bank_mortgage_purchase_average_amount_estimate`

- 名称：Bank purchase average loan: amount estimate
- 含义：银行扣除转按后的推算金额除以推算宗数，作为每笔贷款均额。
- 单位：`HKD million per loan`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-10-31）状态：Unavailable；标记：`APPROVAL_MIX_PROXY;CALCULATED;MISSING_INPUT;MODEL_ESTIMATE`。
- 最新记录来源：Repository calculation from 。[来源 1](https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md)
- 源表／计算表：Monthly mortgage allocation trial v1；字段／公式：bank purchase amount estimate / bank purchase count estimate。
- 口径备注：Formula: bank purchase amount estimate / bank purchase count estimate. Same-month raw input IDs: hk_mortgage_approved_amount, hk_mortgage_approved_count, hk_mortgage_approved_refinancing_amount, hk_mortgage_approved_refinancing_count, hk_mortgage_drawn_amount, hk_mortgage_drawn_count. Monthly allocation trial, not observed money-lender lending. Residential sales mix proxies mortgage mix; registrations and drawdowns differ. Refinancing removed only from banks; residual may include bank refinancing, other lenders, developer-related lending and timing/scope differences. Method: https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md

### `hk_bank_mortgage_purchase_drawn_amount_estimate`

- 名称：Bank excluding refinancing: amount estimate
- 含义：用当月转按批核金额占比，从银行提款总额中扣除推算转按金额。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-10-31）状态：Unavailable；标记：`APPROVAL_MIX_PROXY;CALCULATED;MISSING_INPUT;MODEL_ESTIMATE`。
- 最新记录来源：Repository calculation from 。[来源 1](https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md)
- 源表／计算表：Monthly mortgage allocation trial v1；字段／公式：bank drawn amount * (1 - refinancing amount share)。
- 口径备注：Formula: bank drawn amount * (1 - refinancing amount share). Same-month raw input IDs: hk_mortgage_approved_amount, hk_mortgage_approved_refinancing_amount, hk_mortgage_drawn_amount. Monthly allocation trial, not observed money-lender lending. Residential sales mix proxies mortgage mix; registrations and drawdowns differ. Refinancing removed only from banks; residual may include bank refinancing, other lenders, developer-related lending and timing/scope differences. Method: https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md

### `hk_bank_mortgage_purchase_drawn_count_estimate`

- 名称：Bank excluding refinancing: count estimate
- 含义：用当月转按批核宗数占比，从银行提款总宗数中扣除推算转按宗数。
- 单位：`estimated loans`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-10-31）状态：Unavailable；标记：`APPROVAL_MIX_PROXY;CALCULATED;MISSING_INPUT;MODEL_ESTIMATE`。
- 最新记录来源：Repository calculation from 。[来源 1](https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md)
- 源表／计算表：Monthly mortgage allocation trial v1；字段／公式：bank drawn count * (1 - refinancing count share)。
- 口径备注：Formula: bank drawn count * (1 - refinancing count share). Same-month raw input IDs: hk_mortgage_approved_count, hk_mortgage_approved_refinancing_count, hk_mortgage_drawn_count. Monthly allocation trial, not observed money-lender lending. Residential sales mix proxies mortgage mix; registrations and drawdowns differ. Refinancing removed only from banks; residual may include bank refinancing, other lenders, developer-related lending and timing/scope differences. Method: https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md

### `hk_bank_mortgage_refinancing_amount_share`

- 名称：Bank refinancing share of approvals: amount
- 含义：当月银行转按批核金额占总批核金额的比重，用于金额试算。
- 单位：`fraction`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-10-31）状态：Unavailable；标记：`CALCULATED;MISSING_INPUT`。
- 最新记录来源：Repository calculation from 。[来源 1](https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md)
- 源表／计算表：Monthly mortgage allocation trial v1；字段／公式：refinancing approved amount / total approved amount。
- 口径备注：Formula: refinancing approved amount / total approved amount. Same-month raw input IDs: hk_mortgage_approved_amount, hk_mortgage_approved_refinancing_amount. Calculated ratio of official same-month inputs. Method: https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md

### `hk_bank_mortgage_refinancing_count_share`

- 名称：Bank refinancing share of approvals: count
- 含义：当月银行转按批核宗数占总批核宗数的比重，用于宗数试算。
- 单位：`fraction`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-10-31）状态：Unavailable；标记：`CALCULATED;MISSING_INPUT`。
- 最新记录来源：Repository calculation from 。[来源 1](https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md)
- 源表／计算表：Monthly mortgage allocation trial v1；字段／公式：refinancing approved count / total approved count。
- 口径备注：Formula: refinancing approved count / total approved count. Same-month raw input IDs: hk_mortgage_approved_count, hk_mortgage_approved_refinancing_count. Calculated ratio of official same-month inputs. Method: https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md

### `hk_money_lender_mortgage_amount_estimate`

- 名称：Money-lender residual: amount scenario
- 含义：住宅按揭金额情景减银行扣除转按后的推算金额；假设非银行每笔贷款均额与银行相同。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-10-31）状态：Unavailable；标记：`APPROVAL_MIX_PROXY;BANK_AVERAGE_LOAN_SIZE_ASSUMED;CALCULATED;LR_REFINANCING_NOT_REMOVED;MISSING_INPUT;MODEL_ESTIMATE;SALES_MIX_PROXY;UNIDENTIFIED_LENDER_RESIDUAL`。
- 最新记录来源：Repository calculation from 香港土地注册处。[来源 1](https://gia.info.gov.hk/general/202611/03/P2026110300276_557525_1_1793678584832.pdf) · [来源 2](https://www.landreg.gov.hk/json/monthly_stat/stat1026/t1.json)
- 源表／计算表：Monthly mortgage allocation trial v1；字段／公式：residential total amount scenario - bank purchase amount estimate。
- 口径备注：Formula: residential total amount scenario - bank purchase amount estimate. Same-month raw input IDs: hk_all_building_sales_count, hk_all_property_mortgage_deeds_count, hk_mortgage_approved_amount, hk_mortgage_approved_count, hk_mortgage_approved_refinancing_amount, hk_mortgage_approved_refinancing_count, hk_mortgage_drawn_amount, hk_mortgage_drawn_count, hk_residential_sales_count. Monthly allocation trial, not observed money-lender lending. Residential sales mix proxies mortgage mix; registrations and drawdowns differ. Refinancing removed only from banks; residual may include bank refinancing, other lenders, developer-related lending and timing/scope differences. Method: https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md

### `hk_money_lender_mortgage_count_estimate`

- 名称：Money-lender residual: count estimate
- 含义：住宅按揭推算宗数减银行扣除转按后的推算宗数；差额仍可含银行转按及口径差异。
- 单位：`estimated loans`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-10-31）状态：Unavailable；标记：`APPROVAL_MIX_PROXY;CALCULATED;LR_REFINANCING_NOT_REMOVED;MISSING_INPUT;MODEL_ESTIMATE;SALES_MIX_PROXY;UNIDENTIFIED_LENDER_RESIDUAL`。
- 最新记录来源：Repository calculation from 香港土地注册处。[来源 1](https://gia.info.gov.hk/general/202611/03/P2026110300276_557525_1_1793678584832.pdf) · [来源 2](https://www.landreg.gov.hk/json/monthly_stat/stat1026/t1.json)
- 源表／计算表：Monthly mortgage allocation trial v1；字段／公式：residential total count estimate - bank purchase count estimate。
- 口径备注：Formula: residential total count estimate - bank purchase count estimate. Same-month raw input IDs: hk_all_building_sales_count, hk_all_property_mortgage_deeds_count, hk_mortgage_approved_count, hk_mortgage_approved_refinancing_count, hk_mortgage_drawn_count, hk_residential_sales_count. Monthly allocation trial, not observed money-lender lending. Residential sales mix proxies mortgage mix; registrations and drawdowns differ. Refinancing removed only from banks; residual may include bank refinancing, other lenders, developer-related lending and timing/scope differences. Method: https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md

### `hk_mortgage_applications`

- 名称：New mortgage applications
- 含义：银行在当月接获的新住宅按揭申请宗数；申请未必获批或提款。
- 单位：`applications`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_app_received。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_amount`

- 名称：New mortgage loans approved: amount
- 含义：银行当月新批出的住宅按揭金额，包含一手、二手和转按；不是实际提款。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_approved_amt。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_average_size`

- 名称：Average size of new approved mortgages
- 含义：银行当月新批住宅按揭的平均每笔金额；不是平均楼价。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：2.c. Average size。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_count`

- 名称：New mortgage loans approved: count
- 含义：银行当月新批出的住宅按揭宗数，包含一手、二手和转按。
- 单位：`loans`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_approved。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_ltv`

- 名称：Loan-to-value ratio of new approved mortgages
- 含义：银行当月新批住宅按揭的贷款额与物业价值比率（按揭成数）。
- 单位：`%`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：2.d. Loan-to-value ratio (%)。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_primary_amount`

- 名称：Primary-market mortgage approvals: amount
- 含义：银行当月批出的一手住宅购房按揭金额。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_approved_pt_amt_pri。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_primary_count`

- 名称：Primary-market mortgage approvals: count
- 含义：银行当月批出的一手住宅购房按揭宗数。
- 单位：`loans`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_approved_pt_primkt。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_refinancing_amount`

- 名称：Refinancing mortgage approvals: amount
- 含义：银行当月批出的转按／再融资贷款金额。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_approved_pt_amt_refin。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_refinancing_count`

- 名称：Refinancing mortgage approvals: count
- 含义：银行当月批出的转按／再融资贷款宗数。
- 单位：`loans`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_approved_pt_refin。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_secondary_amount`

- 名称：Secondary-market mortgage approvals: amount
- 含义：银行当月批出的二手住宅购房按揭金额。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_approved_pt_amt_sec。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_secondary_count`

- 名称：Secondary-market mortgage approvals: count
- 含义：银行当月批出的二手住宅购房按揭宗数。
- 单位：`loans`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_approved_pt_secmkt。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_tenor`

- 名称：Contractual life of new approved mortgages
- 含义：银行当月新批住宅按揭的合约还款年期，原始单位为月。
- 单位：`months`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：2.e. Contractual life (months)。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_undrawn_amount`

- 名称：Mortgages approved during month but not drawn: amount
- 含义：当月新批出但尚未提款的住宅按揭金额。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：2.h. New loans approved during the month but not yet drawn: Value。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_approved_undrawn_count`

- 名称：Mortgages approved during month but not drawn: count
- 含义：当月新批出但尚未提款的住宅按揭宗数。
- 单位：`loans`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：2.h. New loans approved during the month but not yet drawn: Number。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_cofinancing_approved_amount`

- 名称：Approved co-financed mortgages: amount
- 含义：当月新批共同融资住宅按揭的银行部分金额。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_approved_cofin_amt。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_cofinancing_approved_count`

- 名称：Approved co-financed mortgages: count
- 含义：当月新批共同融资住宅按揭的宗数。
- 单位：`loans`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_approved_cofin。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_cofinancing_government_outstanding_amount`

- 名称：Government co-financing: outstanding amount
- 含义：与政府房屋贷款计划共同融资的未偿还住宅贷款中，银行部分的余额。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：outstanding_loans_cofin_gf_amt。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_cofinancing_government_outstanding_count`

- 名称：Government co-financing: outstanding loans
- 含义：与政府房屋贷款计划共同融资的未偿还住宅贷款宗数。
- 单位：`loans`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：outstanding_loans_cofin_gf。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_cofinancing_private_outstanding_amount`

- 名称：Private co-financing: outstanding amount
- 含义：与私人部门共同融资的未偿还住宅贷款中，银行部分的余额；不能当作财务公司放款金额。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：outstanding_loans_cofin_ps_amt。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_cofinancing_private_outstanding_count`

- 名称：Private co-financing: outstanding loans
- 含义：与私人部门共同融资的未偿还住宅贷款宗数；不能当作财务公司独立贷款宗数。
- 单位：`loans`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：outstanding_loans_cofin_ps。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_delinquency`

- 名称：Mortgage delinquency ratio: more than 3 months
- 含义：逾期超过三个月的住宅按揭贷款比率。
- 单位：`%`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：delinquency_ratio。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_delinquency_6m`

- 名称：Mortgage delinquency ratio: more than 6 months
- 含义：逾期超过六个月的住宅按揭贷款比率。
- 单位：`%`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：4.c. Delinquency ratio (%): More than 6 months。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_drawn_amount`

- 名称：New mortgage loans drawn down: amount
- 含义：银行当月实际提取的住宅按揭金额；公开总量未按购房和转按分拆。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_drawn_amt。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_drawn_count`

- 名称：New mortgage loans drawn down: count
- 含义：银行当月实际提取的住宅按揭宗数；与同月批核或登记并非同一批贷款。
- 单位：`loans`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：new_loans_drawn。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_outstanding`

- 名称：Outstanding residential mortgage loans
- 含义：月末未偿还住宅按揭贷款余额；这是存量，不能把各月余额相加作新增贷款。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7；字段／公式：outstanding_loans_amt。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_pricing_blr_share`

- 名称：New approved mortgages priced with reference to BLR
- 含义：当月新批按揭中以最优惠贷款利率（BLR／P）定价的占比；不是利率水平。
- 单位：`%`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：6.b. With reference to Best Lending Rate (BLR)。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_pricing_fixed_share`

- 名称：New approved mortgages with fixed rates
- 含义：当月新批按揭中采用固定利率定价的占比。
- 单位：`%`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：6.c. Fixed rate。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_pricing_hibor_share`

- 名称：New approved mortgages priced with reference to HIBOR
- 含义：当月新批按揭中以 HIBOR 定价的占比；不是 HIBOR 利率。
- 单位：`%`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：6.a. With reference to Hong Kong Interbank Offered Rate (HIBOR)。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_pricing_other_share`

- 名称：New approved mortgages with other pricing
- 含义：当月新批按揭中采用其他定价方式的占比。
- 单位：`%`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：6.d. Others。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_rescheduled_ratio`

- 名称：Rescheduled mortgage loan ratio
- 含义：经重新安排还款条件的住宅按揭贷款比率。
- 单位：`%`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：4.d. Rescheduled loan ratio (%)。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_written_off_12m_amount`

- 名称：Mortgage loans written off over past 12 months
- 含义：过去十二个月累计撇销的住宅按揭贷款金额。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：5.b. Loans written off over the past 12 months: Value。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_mortgage_written_off_12m_ratio`

- 名称：Past-12-month write-offs as share of average outstanding
- 含义：过去十二个月撇销金额相对平均未偿还贷款余额的比率。
- 单位：`%`；频率：`M`；非空值范围：暂无可计算／已发布数值。
- 最新记录（2026-09-30）状态：Missing；标记：`below_reporting_threshold`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：5.b. Loans written off over the past 12 months: As % of the average outstanding loans。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. Source * means less than 0.05%; exact value unavailable. 

### `hk_mortgage_written_off_amount`

- 名称：Mortgage loans written off during month
- 含义：银行在当月撇销的住宅按揭贷款金额。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf)
- 源表／计算表：Residential Mortgage Survey annex；字段／公式：5.a. Value of loans written off during the month。
- 口径备注：HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. Co-financing includes only reporting institutions' portions, not developer/non-bank top-up loans. LTV and contractual life are weighted by loan amount. Missing values are not filled. 

### `hk_residential_mortgage_amount_estimate`

- 名称：Residential total: amount scenario
- 含义：住宅按揭推算宗数乘以银行购房贷款推算均额；金额情景，并非 LR 公布的贷款金额。
- 单位：`HKD million`；频率：`M`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-10-31）状态：Unavailable；标记：`APPROVAL_MIX_PROXY;BANK_AVERAGE_LOAN_SIZE_ASSUMED;CALCULATED;LR_REFINANCING_NOT_REMOVED;MISSING_INPUT;MODEL_ESTIMATE;SALES_MIX_PROXY`。
- 最新记录来源：Repository calculation from 香港土地注册处。[来源 1](https://gia.info.gov.hk/general/202611/03/P2026110300276_557525_1_1793678584832.pdf) · [来源 2](https://www.landreg.gov.hk/json/monthly_stat/stat1026/t1.json)
- 源表／计算表：Monthly mortgage allocation trial v1；字段／公式：residential total count estimate * bank purchase average loan estimate。
- 口径备注：Formula: residential total count estimate * bank purchase average loan estimate. Same-month raw input IDs: hk_all_building_sales_count, hk_all_property_mortgage_deeds_count, hk_mortgage_approved_amount, hk_mortgage_approved_count, hk_mortgage_approved_refinancing_amount, hk_mortgage_approved_refinancing_count, hk_mortgage_drawn_amount, hk_mortgage_drawn_count, hk_residential_sales_count. Monthly allocation trial, not observed money-lender lending. Residential sales mix proxies mortgage mix; registrations and drawdowns differ. Refinancing removed only from banks; residual may include bank refinancing, other lenders, developer-related lending and timing/scope differences. Method: https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md

### `hk_residential_mortgage_count_estimate`

- 名称：Residential total: count estimate
- 含义：按当月住宅成交宗数占比，把 LR 全物业按揭文书总数分配为住宅按揭宗数的推算。
- 单位：`estimated loans`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Estimated；标记：`CALCULATED;LR_REFINANCING_NOT_REMOVED;MODEL_ESTIMATE;SALES_MIX_PROXY`。
- 最新记录来源：Repository calculation from 香港土地注册处。[来源 1](https://gia.info.gov.hk/general/202611/03/P2026110300276_557525_1_1793678584832.pdf) · [来源 2](https://www.landreg.gov.hk/json/monthly_stat/stat1026/t1.json)
- 源表／计算表：Monthly mortgage allocation trial v1；字段／公式：LR mortgage deeds * residential sales share。
- 口径备注：Formula: LR mortgage deeds * residential sales share. Same-month raw input IDs: hk_all_building_sales_count, hk_all_property_mortgage_deeds_count, hk_residential_sales_count. Monthly allocation trial, not observed money-lender lending. Residential sales mix proxies mortgage mix; registrations and drawdowns differ. Refinancing removed only from banks; residual may include bank refinancing, other lenders, developer-related lending and timing/scope differences. Method: https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md

### `hk_residential_sales_share`

- 名称：Residential share of building sale agreements
- 含义：当月住宅买卖合约宗数除以全部楼宇买卖合约宗数；是成交结构，不是借贷人数占比。
- 单位：`fraction`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Calculated；标记：`CALCULATED`。
- 最新记录来源：Repository calculation from 香港土地注册处。[来源 1](https://gia.info.gov.hk/general/202611/03/P2026110300276_557525_1_1793678584832.pdf) · [来源 2](https://www.landreg.gov.hk/json/monthly_stat/stat1026/t1.json)
- 源表／计算表：Monthly mortgage allocation trial v1；字段／公式：residential sales count / all building sales count。
- 口径备注：Formula: residential sales count / all building sales count. Same-month raw input IDs: hk_all_building_sales_count, hk_residential_sales_count. Calculated ratio of official same-month inputs. Method: https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md

## Mortgage / Mortgage_Registrations

### `hk_all_property_building_mortgage_deeds_count`

- 名称：建筑按揭／建筑法定押记文书登记宗数
- 含义：建筑融资按揭／建筑法定押记文书宗数；不是普通住宅按揭总数。
- 单位：`deeds`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://www.landreg.gov.hk/json/monthly_stat/stat1026/t1.json)
- 源表／计算表：Consolidated Monthly Statistics, Table 1；字段／公式：Total Number of Urban & New Territories deeds received for registration for Building Mortgages/Building Legal Charges。
- 口径备注：统计送交登记的文书份数，不是有按揭住宅成交宗数或独立物业数。覆盖住宅、非住宅及土地，未区分银行与非银行、购房与再融资，不能减去银行购房按揭以推算非银行按揭。解除按揭等文书不是新按揭的相反流量，不能相减推算购房按揭。登记月通常滞后文书签立时间；市区及新界分项加总，已核对来源提供的合计。官方未公布此表按揭金额；未将不适用值当作零。历史档案最多30天重新核查；source_checked_at记录实际来源核查时间，非发布日期。

### `hk_all_property_discharge_deeds_count`

- 名称：收据／解除按揭／解除押记文书登记宗数
- 含义：收据／解除按揭／解除押记文书宗数；不能直接从新按揭宗数相减为购房贷款。
- 单位：`deeds`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://www.landreg.gov.hk/json/monthly_stat/stat1026/t1.json)
- 源表／计算表：Consolidated Monthly Statistics, Table 1；字段／公式：Total Number of Urban & New Territories deeds received for registration for Receipts/Discharges/Releases。
- 口径备注：统计送交登记的文书份数，不是有按揭住宅成交宗数或独立物业数。覆盖住宅、非住宅及土地，未区分银行与非银行、购房与再融资，不能减去银行购房按揭以推算非银行按揭。解除按揭等文书不是新按揭的相反流量，不能相减推算购房按揭。登记月通常滞后文书签立时间；市区及新界分项加总，已核对来源提供的合计。官方未公布此表按揭金额；未将不适用值当作零。历史档案最多30天重新核查；source_checked_at记录实际来源核查时间，非发布日期。

### `hk_all_property_mortgage_deeds_count`

- 名称：全物业按揭／法定押记文书登记宗数
- 含义：LR 第 5、6 项合计的全物业按揭／法定押记文书宗数；并非独立贷款或住宅套数。
- 单位：`deeds`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://www.landreg.gov.hk/json/monthly_stat/stat1026/t1.json)
- 源表／计算表：Consolidated Monthly Statistics, Table 1；字段／公式：Building Mortgages/Building Legal Charges + Other Mortgages/Legal Charges; Urban + New Territories。
- 口径备注：统计送交登记的文书份数，不是有按揭住宅成交宗数或独立物业数。覆盖住宅、非住宅及土地，未区分银行与非银行、购房与再融资，不能减去银行购房按揭以推算非银行按揭。解除按揭等文书不是新按揭的相反流量，不能相减推算购房按揭。登记月通常滞后文书签立时间；市区及新界分项加总，已核对来源提供的合计。官方未公布此表按揭金额；未将不适用值当作零。历史档案最多30天重新核查；source_checked_at记录实际来源核查时间，非发布日期。

### `hk_all_property_other_mortgage_deeds_count`

- 名称：其他按揭／法定押记文书登记宗数
- 含义：其他按揭／法定押记文书宗数，跨住宅、非住宅及土地。
- 单位：`deeds`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Published；标记：`无`。
- 最新记录来源：香港土地注册处。[来源 1](https://www.landreg.gov.hk/json/monthly_stat/stat1026/t1.json)
- 源表／计算表：Consolidated Monthly Statistics, Table 1；字段／公式：Total Number of Urban & New Territories deeds received for registration for Other Mortgages/Legal Charges。
- 口径备注：统计送交登记的文书份数，不是有按揭住宅成交宗数或独立物业数。覆盖住宅、非住宅及土地，未区分银行与非银行、购房与再融资，不能减去银行购房按揭以推算非银行按揭。解除按揭等文书不是新按揭的相反流量，不能相减推算购房按揭。登记月通常滞后文书签立时间；市区及新界分项加总，已核对来源提供的合计。官方未公布此表按揭金额；未将不适用值当作零。历史档案最多30天重新核查；source_checked_at记录实际来源核查时间，非发布日期。

## Mortgage / Negative_Equity_Quarterly

### `hk_negative_equity_amount`

- 名称：Negative-equity mortgages: outstanding value
- 含义：季度末负资产住宅按揭的未偿还贷款总余额；不是全部损失金额。
- 单位：`HKD million`；频率：`Q`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e6a1.pdf)
- 源表／计算表：Key Extrapolated Results of the Survey on Residential Mortgage Loans in Negative Equity；字段／公式：Total outstanding value (HK$ million)。
- 口径备注：Quarterly extrapolated negative-equity survey of first mortgages from authorized institutions; no monthly interpolation.

### `hk_negative_equity_amount_share`

- 名称：Negative-equity mortgages: share of outstanding value
- 含义：负资产住宅按揭余额占调查口径按揭余额的比率。
- 单位：`%`；频率：`Q`；非空值范围：2017-03-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e6a1.pdf)
- 源表／计算表：Key Extrapolated Results of the Survey on Residential Mortgage Loans in Negative Equity；字段／公式：As % of total outstanding value。
- 口径备注：Quarterly extrapolated negative-equity survey of first mortgages from authorized institutions; no monthly interpolation.

### `hk_negative_equity_borrower_share`

- 名称：Negative-equity mortgages: share of total borrowers
- 含义：负资产住宅按揭借款人占调查口径借款人的比率。
- 单位：`%`；频率：`Q`；非空值范围：2017-03-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e6a1.pdf)
- 源表／计算表：Key Extrapolated Results of the Survey on Residential Mortgage Loans in Negative Equity；字段／公式：As % of total mortgage borrowers。
- 口径备注：Quarterly extrapolated negative-equity survey of first mortgages from authorized institutions; no monthly interpolation.

### `hk_negative_equity_count`

- 名称：Negative-equity mortgages: outstanding count
- 含义：季度末已知处于负资产状态的银行第一按揭贷款宗数。
- 单位：`loans`；频率：`Q`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e6a1.pdf)
- 源表／计算表：Key Extrapolated Results of the Survey on Residential Mortgage Loans in Negative Equity；字段／公式：Total outstanding number。
- 口径备注：Quarterly extrapolated negative-equity survey of first mortgages from authorized institutions; no monthly interpolation.

### `hk_negative_equity_delinquency`

- 名称：Negative-equity mortgages: delinquency over 3 months
- 含义：负资产住宅按揭中逾期超过三个月的贷款比率；不等于所有负资产借款人已违约。
- 单位：`%`；频率：`Q`；非空值范围：2026-03-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e6a1.pdf)
- 源表／计算表：Key Extrapolated Results of the Survey on Residential Mortgage Loans in Negative Equity；字段／公式：Delinquency ratio (more than 3 months)。
- 口径备注：Quarterly extrapolated negative-equity survey of first mortgages from authorized institutions; no monthly interpolation.

### `hk_negative_equity_ltv`

- 名称：Negative-equity mortgages: loan-to-value ratio
- 含义：负资产住宅按揭的贷款余额相对抵押物业价值比率。
- 单位：`%`；频率：`Q`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e6a1.pdf)
- 源表／计算表：Key Extrapolated Results of the Survey on Residential Mortgage Loans in Negative Equity；字段／公式：Loan-to-value ratio。
- 口径备注：Quarterly extrapolated negative-equity survey of first mortgages from authorized institutions; no monthly interpolation.

### `hk_negative_equity_unsecured_amount`

- 名称：Negative-equity mortgages: unsecured portion
- 含义：负资产住宅按揭余额中超出抵押物业价值、缺少物业价值覆盖的部分。
- 单位：`HKD million`；频率：`Q`；非空值范围：2016-12-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e6a1.pdf)
- 源表／计算表：Key Extrapolated Results of the Survey on Residential Mortgage Loans in Negative Equity；字段／公式：Value of unsecured portion (HK$ million)。
- 口径备注：Quarterly extrapolated negative-equity survey of first mortgages from authorized institutions; no monthly interpolation.

## Macro / Money_Supply

### `hk_m1_fc`

- 名称：Foreign currency M1
- 含义：货币供应 M1 的外币部分，已折算为港元；月末存量，不是当月新增货币。M1 包括公众持有的法定纸币及硬币，以及客户在银行的活期存款。[HKMA 定义](https://www.hkma.gov.hk/eng/data-publications-and-research/guide-to-monetary-banking-and-financial-terms/)。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e7a1.pdf)
- 源表／计算表：Table 1A: Hong Kong Monetary Statistics；字段／公式：Money Supply: M1 - Foreign currency。
- 口径备注：End-month money supply, not seasonally adjusted, new series since April 1997. M2/M3 HKD includes foreign-currency swap deposits; foreign currency excludes them. Foreign currency and all-currency totals are expressed in HKD million. Latest press-release table rounds amounts to whole HKD million; historical workbook may retain decimals.

### `hk_m1_hkd`

- 名称：Hong Kong dollar M1
- 含义：货币供应 M1 的港元部分；月末存量，不是当月新增货币。M1 包括公众持有的法定纸币及硬币，以及客户在银行的活期存款。[HKMA 定义](https://www.hkma.gov.hk/eng/data-publications-and-research/guide-to-monetary-banking-and-financial-terms/)。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e7a1.pdf)
- 源表／计算表：Table 1A: Hong Kong Monetary Statistics；字段／公式：Money Supply: M1 - HK$。
- 口径备注：End-month money supply, not seasonally adjusted, new series since April 1997. M2/M3 HKD includes foreign-currency swap deposits; foreign currency excludes them. Foreign currency and all-currency totals are expressed in HKD million. Latest press-release table rounds amounts to whole HKD million; historical workbook may retain decimals.

### `hk_m1_total`

- 名称：All-currency M1
- 含义：货币供应 M1 的所有货币合计；月末存量，不是当月新增货币。M1 包括公众持有的法定纸币及硬币，以及客户在银行的活期存款。[HKMA 定义](https://www.hkma.gov.hk/eng/data-publications-and-research/guide-to-monetary-banking-and-financial-terms/)。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e7a1.pdf)
- 源表／计算表：Table 1A: Hong Kong Monetary Statistics；字段／公式：Money Supply: M1 - Total。
- 口径备注：End-month money supply, not seasonally adjusted, new series since April 1997. M2/M3 HKD includes foreign-currency swap deposits; foreign currency excludes them. Foreign currency and all-currency totals are expressed in HKD million. Latest press-release table rounds amounts to whole HKD million; historical workbook may retain decimals.

### `hk_m2_fc`

- 名称：Foreign currency M2
- 含义：货币供应 M2 的外币部分，已折算为港元；月末存量，不是当月新增货币。M2 在 M1 上加入客户的银行储蓄和定期存款，以及银行体系以外持有的银行可转让存款证。[HKMA 定义](https://www.hkma.gov.hk/eng/data-publications-and-research/guide-to-monetary-banking-and-financial-terms/)。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e7a1.pdf)
- 源表／计算表：Table 1A: Hong Kong Monetary Statistics；字段／公式：Money Supply: M2 - Foreign currency。
- 口径备注：End-month money supply, not seasonally adjusted, new series since April 1997. M2/M3 HKD includes foreign-currency swap deposits; foreign currency excludes them. Foreign currency and all-currency totals are expressed in HKD million. Latest press-release table rounds amounts to whole HKD million; historical workbook may retain decimals.

### `hk_m2_hkd`

- 名称：Hong Kong dollar M2
- 含义：货币供应 M2 的港元部分；月末存量，不是当月新增货币。M2 在 M1 上加入客户的银行储蓄和定期存款，以及银行体系以外持有的银行可转让存款证。[HKMA 定义](https://www.hkma.gov.hk/eng/data-publications-and-research/guide-to-monetary-banking-and-financial-terms/)。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e7a1.pdf)
- 源表／计算表：Table 1A: Hong Kong Monetary Statistics；字段／公式：Money Supply: M2 - HK$。
- 口径备注：End-month money supply, not seasonally adjusted, new series since April 1997. M2/M3 HKD includes foreign-currency swap deposits; foreign currency excludes them. Foreign currency and all-currency totals are expressed in HKD million. Latest press-release table rounds amounts to whole HKD million; historical workbook may retain decimals.

### `hk_m2_total`

- 名称：All-currency M2
- 含义：货币供应 M2 的所有货币合计；月末存量，不是当月新增货币。M2 在 M1 上加入客户的银行储蓄和定期存款，以及银行体系以外持有的银行可转让存款证。[HKMA 定义](https://www.hkma.gov.hk/eng/data-publications-and-research/guide-to-monetary-banking-and-financial-terms/)。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e7a1.pdf)
- 源表／计算表：Table 1A: Hong Kong Monetary Statistics；字段／公式：Money Supply: M2 - Total。
- 口径备注：End-month money supply, not seasonally adjusted, new series since April 1997. M2/M3 HKD includes foreign-currency swap deposits; foreign currency excludes them. Foreign currency and all-currency totals are expressed in HKD million. Latest press-release table rounds amounts to whole HKD million; historical workbook may retain decimals.

### `hk_m3_fc`

- 名称：Foreign currency M3
- 含义：货币供应 M3 的外币部分，已折算为港元；月末存量，不是当月新增货币。M3 在 M2 上加入客户在有限制牌照银行和接受存款公司的存款，以及银行体系以外持有的这些机构的可转让存款证。[HKMA 定义](https://www.hkma.gov.hk/eng/data-publications-and-research/guide-to-monetary-banking-and-financial-terms/)。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e7a1.pdf)
- 源表／计算表：Table 1A: Hong Kong Monetary Statistics；字段／公式：Money Supply: M3 - Foreign currency。
- 口径备注：End-month money supply, not seasonally adjusted, new series since April 1997. M2/M3 HKD includes foreign-currency swap deposits; foreign currency excludes them. Foreign currency and all-currency totals are expressed in HKD million. Latest press-release table rounds amounts to whole HKD million; historical workbook may retain decimals.

### `hk_m3_hkd`

- 名称：Hong Kong dollar M3
- 含义：货币供应 M3 的港元部分；月末存量，不是当月新增货币。M3 在 M2 上加入客户在有限制牌照银行和接受存款公司的存款，以及银行体系以外持有的这些机构的可转让存款证。[HKMA 定义](https://www.hkma.gov.hk/eng/data-publications-and-research/guide-to-monetary-banking-and-financial-terms/)。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e7a1.pdf)
- 源表／计算表：Table 1A: Hong Kong Monetary Statistics；字段／公式：Money Supply: M3 - HK$。
- 口径备注：End-month money supply, not seasonally adjusted, new series since April 1997. M2/M3 HKD includes foreign-currency swap deposits; foreign currency excludes them. Foreign currency and all-currency totals are expressed in HKD million. Latest press-release table rounds amounts to whole HKD million; historical workbook may retain decimals.

### `hk_m3_total`

- 名称：All-currency M3
- 含义：货币供应 M3 的所有货币合计；月末存量，不是当月新增货币。M3 在 M2 上加入客户在有限制牌照银行和接受存款公司的存款，以及银行体系以外持有的这些机构的可转让存款证。[HKMA 定义](https://www.hkma.gov.hk/eng/data-publications-and-research/guide-to-monetary-banking-and-financial-terms/)。
- 单位：`HKD million`；频率：`M`；非空值范围：2002-01-31 — 2026-09-30。
- 最新记录（2026-09-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e7a1.pdf)
- 源表／计算表：Table 1A: Hong Kong Monetary Statistics；字段／公式：Money Supply: M3 - Total。
- 口径备注：End-month money supply, not seasonally adjusted, new series since April 1997. M2/M3 HKD includes foreign-currency swap deposits; foreign currency excludes them. Foreign currency and all-currency totals are expressed in HKD million. Latest press-release table rounds amounts to whole HKD million; historical workbook may retain decimals.

## Macro / HIBOR_Daily

### `hk_hibor_12m_daily`

- 名称：HIBOR 12 months
- 含义：十二个月期香港银行同业拆息；逐日公布的定盘利率。数值按年利率百分数表示。
- 单位：`% p.a.`；频率：`D`；非空值范围：2002-01-02 — 2026-10-30。
- 最新记录（2026-10-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060303.xls)
- 源表／计算表：6.3.3 (HIBOR Fixing)；字段／公式：12 months。
- 口径备注：HKAB fixing at 11:15; separate from discontinued closing quotes. 

### `hk_hibor_1m_daily`

- 名称：HIBOR 1 month
- 含义：一个月期香港银行同业拆息；逐日公布的定盘利率。数值按年利率百分数表示。
- 单位：`% p.a.`；频率：`D`；非空值范围：2002-01-02 — 2026-11-04。
- 最新记录（2026-11-04）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/eng/data-publications-and-research/data-and-statistics/daily-monetary-statistics/2026/11/ms-20261104/)
- 源表／计算表：见来源文件；字段／公式：HIBOR 1 month。
- 口径备注：HKAB 1-month fixing published in HKMA Daily Monetary Statistics.

### `hk_hibor_1w_daily`

- 名称：HIBOR 1 week
- 含义：一周期香港银行同业拆息；逐日公布的定盘利率。数值按年利率百分数表示。
- 单位：`% p.a.`；频率：`D`；非空值范围：2006-01-03 — 2026-10-30。
- 最新记录（2026-10-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060303.xls)
- 源表／计算表：6.3.3 (HIBOR Fixing)；字段／公式：1 week。
- 口径备注：HKAB fixing at 11:15; separate from discontinued closing quotes. 

### `hk_hibor_3m_daily`

- 名称：HIBOR 3 months
- 含义：三个月期香港银行同业拆息；逐日公布的定盘利率。数值按年利率百分数表示。
- 单位：`% p.a.`；频率：`D`；非空值范围：2002-01-02 — 2026-10-30。
- 最新记录（2026-10-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060303.xls)
- 源表／计算表：6.3.3 (HIBOR Fixing)；字段／公式：3 months。
- 口径备注：HKAB fixing at 11:15; separate from discontinued closing quotes. 

### `hk_hibor_6m_daily`

- 名称：HIBOR 6 months
- 含义：六个月期香港银行同业拆息；逐日公布的定盘利率。数值按年利率百分数表示。
- 单位：`% p.a.`；频率：`D`；非空值范围：2002-01-02 — 2026-10-30。
- 最新记录（2026-10-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060303.xls)
- 源表／计算表：6.3.3 (HIBOR Fixing)；字段／公式：6 months。
- 口径备注：HKAB fixing at 11:15; separate from discontinued closing quotes. 

### `hk_hibor_9m_daily`

- 名称：HIBOR 9 months
- 含义：九个月期香港银行同业拆息；逐日公布的定盘利率。数值按年利率百分数表示。
- 单位：`% p.a.`；频率：`D`；非空值范围：2002-01-02 — 2014-03-31。
- 最新记录（2026-10-30）状态：Missing；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060303.xls)
- 源表／计算表：6.3.3 (HIBOR Fixing)；字段／公式：9 months。
- 口径备注：HKAB fixing at 11:15; separate from discontinued closing quotes. 9-month fixing discontinued from 1 April 2014.

### `hk_hibor_overnight_daily`

- 名称：HIBOR Overnight
- 含义：隔夜期香港银行同业拆息；逐日公布的定盘利率。数值按年利率百分数表示。
- 单位：`% p.a.`；频率：`D`；非空值范围：2006-01-03 — 2026-10-30。
- 最新记录（2026-10-30）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060303.xls)
- 源表／计算表：6.3.3 (HIBOR Fixing)；字段／公式：Overnight。
- 口径备注：HKAB fixing at 11:15; separate from discontinued closing quotes. 

## Macro / Prime_Rate

### `hk_prime_rate_hsbc_effective`

- 名称：HSBC Prime rate
- 含义：HSBC 最优惠贷款利率；仅记录利率变更的生效日期，不是完整每日时间序列。
- 单位：`% p.a.`；频率：`E`；非空值范围：2002-11-08 — 2025-10-31。
- 最新记录（2025-10-31）状态：Published；标记：`无`。
- 最新记录来源：HSBC。[来源 1](https://www.hsbc.com.hk/investments/market-information/hk/lending-rate/)
- 源表／计算表：见来源文件；字段／公式：HSBC Prime rate。
- 口径备注：Rate effective from this date. HSBC current rate checked 2026-11-05; unchanged dates are not new rate changes.

## Macro / Rates_Monthly

### `hk_hibor_1m`

- 名称：1-month HIBOR (monthly average)
- 含义：一个月期香港银行同业拆息；官方公布的月平均利率。数值按年利率百分数表示。
- 单位：`% p.a.`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060302.xls)
- 源表／计算表：6.3.2；字段／公式：ir_1m。
- 口径备注：Official monthly average of HKAB Hong Kong dollar Interest Settlement Rates (HIBOR fixing). A market benchmark, not an HSBC-specific quote or actual mortgage rate. The discontinued Standard Chartered HIBOR segment is excluded.

### `hk_hibor_3m`

- 名称：3-month HIBOR (monthly average)
- 含义：三个月期香港银行同业拆息；官方公布的月平均利率。数值按年利率百分数表示。
- 单位：`% p.a.`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060302.xls)
- 源表／计算表：6.3.2；字段／公式：ir_3m。
- 口径备注：Official monthly average of HKAB Hong Kong dollar Interest Settlement Rates (HIBOR fixing). A market benchmark, not an HSBC-specific quote or actual mortgage rate. The discontinued Standard Chartered HIBOR segment is excluded.

### `hk_prime_rate_hsbc`

- 名称：HSBC prime rate (monthly average)
- 含义：HSBC 最优惠贷款利率；官方公布的月平均值。
- 单位：`% p.a.`；频率：`M`；非空值范围：2002-01-31 — 2026-10-31。
- 最新记录（2026-10-31）状态：Published；标记：`无`。
- 最新记录来源：Hong Kong Monetary Authority。[来源 1](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060402.xls)
- 源表／计算表：6.4.2；字段／公式：best_lending_rate。
- 口径备注：Official monthly average of the best lending rate quoted by HSBC (Hongkong and Shanghai Banking Corporation Limited). Not the current effective rate or an actual mortgage borrowing rate.
