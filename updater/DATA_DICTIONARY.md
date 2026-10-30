# 香港住宅数据集说明

香港为本版唯一市场。月度数据主键为 `(metric_id, period)`，值为官方原始单位；CSV、JSON、SQLite 使用相同月度观察值。PDF 另存独立长表，避免把年度、季度、累计和月度重复计数。

| 字段 | 含义 |
|---|---|
| metric_id | 稳定系列标识；不同类别、地区、统计口径使用不同 ID |
| period / date | 观察月份 / 月末日期，不是发布日期 |
| value | 原值；缺失为 null，CSV 空白，不填零 |
| unit | 指数1999=100、港元/平方米、港元/平方米/月、百万港元、宗/份、百分比 |
| class_name | A<40㎡；B40–69.9㎡；C70–99.9㎡；D100–159.9㎡；E≥160㎡；实用面积 |
| region | 港岛、九龙、新界、市区或全港 |
| flags | 差估署 P=暂定；Z=少于20宗 |
| source_id / source_url | 数据入口及可复查官方URL |
| source_period | HKMA利率报告刊期；与利率观察月不同 |

- 差估署六张月表从1999年起保存；价格统计不包含一手住宅销售。平均租金、平均价格受成交组合影响。
- 土地注册处初始回溯24个月，一手、二手与总数保留官方值。宗数严格加总；金额独立取整，允许最多1百万港元差异。按登记月份统计。
- HKMA调查从官方API可得范围保存。按揭平均利率仅取半年度报告明确披露月份，不将定价方式占比当作利率，不补全中间月份。
- PDF十表长表额外保留 table_id、pdf_page、frequency、observation_kind、raw_cell、provisional。供应全年预测与年累计落成明确分开。
- 同比=本期/精确上年同月−1；环比=本期/精确上月−1。缺同期不计算；百分比变化乘100。均未季调。
- refresh_status.json 保存逐源核查时间、最近成功时间、历史修订和失败记录。更新时间不是数据所属月份。

SQLite v2：`observations` 表使用数值型 value，地区、类别、商业类型、单位和来源等均为可直接查询的列；完整原记录也保留在 payload JSON，唯一键为 (metric_id,period)。数据库另含 PDF 提取、来源状态、修订、PDF/CSV 差异和元数据，并提供指标目录、最新值及住宅尺价视图。见仓库根目录 DATABASE.md。本地原始文件和报告按内容哈希归档，原PDF不会被覆盖。


## Commercial property

`property_type`: Office, Retail or Industrial. `measure`: price_index, rental_index, average_price, average_rent or yield. `grade` is A/B/C/All; office grades describe building quality and are not residential size classes. `region` retains the official district. Industrial is private flatted factories.

Source tables: 2.1 office rents; 2.2 office prices; 2.3 office rental indices; 2.4 office price indices; 3.1 retail average rents/prices; 3.2 retail indices; 4.1 flatted-factory averages; 4.2 flatted-factory indices; 5.2 non-domestic yields (office A/B only, retail and flatted factories). Indices use 1999=100. Averages use internal floor area and original HKD/sq m (rent per month); displayed HKD/sq ft = original value × 0.09290304.

P is provisional. X/Y/Z indicate fewer than 5/10/20 cases. Null values retain no-published-value status; no forward fill, interpolation or unweighted district average is produced.

Source status includes `change_summary`, distinguishing a fresh check with unchanged observations from new/revised values or changed PDF content. The RVD PDF has its own status row.
