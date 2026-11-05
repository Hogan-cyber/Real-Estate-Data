"""Generate a complete, source-linked indicator guide with every publication."""
from collections import defaultdict
from pathlib import Path

from .export import ORDER, group_for, sheet_for

MORTGAGE = {
    'applications':'银行在当月接获的新住宅按揭申请宗数；申请未必获批或提款。',
    'approved_amount':'银行当月新批出的住宅按揭金额，包含一手、二手和转按；不是实际提款。',
    'approved_count':'银行当月新批出的住宅按揭宗数，包含一手、二手和转按。',
    'approved_average_size':'银行当月新批住宅按揭的平均每笔金额；不是平均楼价。',
    'approved_ltv':'银行当月新批住宅按揭的贷款额与物业价值比率（按揭成数）。',
    'approved_tenor':'银行当月新批住宅按揭的合约还款年期，原始单位为月。',
    'approved_primary_amount':'银行当月批出的一手住宅购房按揭金额。',
    'approved_primary_count':'银行当月批出的一手住宅购房按揭宗数。',
    'approved_secondary_amount':'银行当月批出的二手住宅购房按揭金额。',
    'approved_secondary_count':'银行当月批出的二手住宅购房按揭宗数。',
    'approved_refinancing_amount':'银行当月批出的转按／再融资贷款金额。',
    'approved_refinancing_count':'银行当月批出的转按／再融资贷款宗数。',
    'approved_undrawn_amount':'当月新批出但尚未提款的住宅按揭金额。',
    'approved_undrawn_count':'当月新批出但尚未提款的住宅按揭宗数。',
    'drawn_amount':'银行当月实际提取的住宅按揭金额；公开总量未按购房和转按分拆。',
    'drawn_count':'银行当月实际提取的住宅按揭宗数；与同月批核或登记并非同一批贷款。',
    'outstanding':'月末未偿还住宅按揭贷款余额；这是存量，不能把各月余额相加作新增贷款。',
    'delinquency':'逾期超过三个月的住宅按揭贷款比率。',
    'delinquency_6m':'逾期超过六个月的住宅按揭贷款比率。',
    'rescheduled_ratio':'经重新安排还款条件的住宅按揭贷款比率。',
    'written_off_amount':'银行在当月撇销的住宅按揭贷款金额。',
    'written_off_12m_amount':'过去十二个月累计撇销的住宅按揭贷款金额。',
    'written_off_12m_ratio':'过去十二个月撇销金额相对平均未偿还贷款余额的比率。',
    'pricing_blr_share':'当月新批按揭中以最优惠贷款利率（BLR／P）定价的占比；不是利率水平。',
    'pricing_hibor_share':'当月新批按揭中以 HIBOR 定价的占比；不是 HIBOR 利率。',
    'pricing_fixed_share':'当月新批按揭中采用固定利率定价的占比。',
    'pricing_other_share':'当月新批按揭中采用其他定价方式的占比。',
    'cofinancing_approved_amount':'当月新批共同融资住宅按揭的银行部分金额。',
    'cofinancing_approved_count':'当月新批共同融资住宅按揭的宗数。',
    'cofinancing_government_outstanding_amount':'与政府房屋贷款计划共同融资的未偿还住宅贷款中，银行部分的余额。',
    'cofinancing_government_outstanding_count':'与政府房屋贷款计划共同融资的未偿还住宅贷款宗数。',
    'cofinancing_private_outstanding_amount':'与私人部门共同融资的未偿还住宅贷款中，银行部分的余额；不能当作财务公司放款金额。',
    'cofinancing_private_outstanding_count':'与私人部门共同融资的未偿还住宅贷款宗数；不能当作财务公司独立贷款宗数。',
}
NEGATIVE = {
    'amount':'季度末负资产住宅按揭的未偿还贷款总余额；不是全部损失金额。',
    'amount_share':'负资产住宅按揭余额占调查口径按揭余额的比率。',
    'borrower_share':'负资产住宅按揭借款人占调查口径借款人的比率。',
    'count':'季度末已知处于负资产状态的银行第一按揭贷款宗数。',
    'delinquency':'负资产住宅按揭中逾期超过三个月的贷款比率；不等于所有负资产借款人已违约。',
    'ltv':'负资产住宅按揭的贷款余额相对抵押物业价值比率。',
    'unsecured_amount':'负资产住宅按揭余额中超出抵押物业价值、缺少物业价值覆盖的部分。',
}
MODEL = {
    'hk_residential_sales_share':'当月住宅买卖合约宗数除以全部楼宇买卖合约宗数；是成交结构，不是借贷人数占比。',
    'hk_bank_mortgage_refinancing_count_share':'当月银行转按批核宗数占总批核宗数的比重，用于宗数试算。',
    'hk_bank_mortgage_refinancing_amount_share':'当月银行转按批核金额占总批核金额的比重，用于金额试算。',
    'hk_residential_mortgage_count_estimate':'按当月住宅成交宗数占比，把 LR 全物业按揭文书总数分配为住宅按揭宗数的推算。',
    'hk_bank_mortgage_purchase_drawn_count_estimate':'用当月转按批核宗数占比，从银行提款总宗数中扣除推算转按宗数。',
    'hk_bank_mortgage_purchase_drawn_amount_estimate':'用当月转按批核金额占比，从银行提款总额中扣除推算转按金额。',
    'hk_bank_mortgage_purchase_average_amount_estimate':'银行扣除转按后的推算金额除以推算宗数，作为每笔贷款均额。',
    'hk_residential_mortgage_amount_estimate':'住宅按揭推算宗数乘以银行购房贷款推算均额；金额情景，并非 LR 公布的贷款金额。',
    'hk_money_lender_mortgage_count_estimate':'住宅按揭推算宗数减银行扣除转按后的推算宗数；差额仍可含银行转按及口径差异。',
    'hk_money_lender_mortgage_amount_estimate':'住宅按揭金额情景减银行扣除转按后的推算金额；假设非银行每笔贷款均额与银行相同。',
}


def describe(row):
    metric=row['metric_id']
    if metric in MODEL:return MODEL[metric]
    if metric.startswith('hk_mortgage_'):
        return MORTGAGE.get(metric.removeprefix('hk_mortgage_'),row['metric_name'])
    if metric.startswith('hk_negative_equity_'):
        return NEGATIVE.get(metric.removeprefix('hk_negative_equity_'),row['metric_name'])
    if metric.startswith('rvd_'):
        scope=row.get('source_field','')
        for prefix,meaning in (
            ('rvd_1_1_','私人住宅平均租金：每平方米每月租金，会受当月成交组合影响'),
            ('rvd_1_2_','私人住宅平均售价：每平方米价格，不含一手成交，会受成交组合影响'),
            ('rvd_1_3_','私人住宅租金指数：比较租金水平变化，不是租金金额'),
            ('rvd_1_4_','私人住宅售价指数：比较价格水平变化，不是平均成交价格'),
            ('rvd_1_5_','选定受欢迎屋苑的私人住宅售价指数；样本范围不同于全市场指数'),
            ('rvd_stock_','年末私人住宅存量：已存在的住宅单位数'),
            ('rvd_completions_','私人住宅落成量：当年落成的单位数；当年部分数据的截止期见备注'),
            ('rvd_vacancy_','年末私人住宅空置量或空置率；dwellings 为单位数，fraction 为比例'),
            ('rvd_takeup_','私人住宅净吸纳量：净吸纳单位数，不是成交宗数或落成量'),
        ):
            if metric.startswith(prefix):return meaning+'。范围：'+scope+'。'
    if metric.startswith(('hk_m1_','hk_m2_','hk_m3_')):
        _,level,currency=metric.split('_')
        scope={'hkd':'港元部分','fc':'外币部分，已折算为港元','total':'所有货币合计'}[currency]
        components={
            'm1':'M1 包括公众持有的法定纸币及硬币，以及客户在银行的活期存款。',
            'm2':'M2 在 M1 上加入客户的银行储蓄和定期存款，以及银行体系以外持有的银行可转让存款证。',
            'm3':'M3 在 M2 上加入客户在有限制牌照银行和接受存款公司的存款，以及银行体系以外持有的这些机构的可转让存款证。',
        }
        return (f'货币供应 {level.upper()} 的{scope}；月末存量，不是当月新增货币。'+components[level]
                +'[HKMA 定义](https://www.hkma.gov.hk/eng/data-publications-and-research/guide-to-monetary-banking-and-financial-terms/)。')
    if metric.startswith('hk_hibor_'):
        tenor={'overnight':'隔夜','1w':'一周','1m':'一个月','3m':'三个月','6m':'六个月','9m':'九个月','12m':'十二个月'}[metric.split('_')[2]]
        return f'{tenor}期香港银行同业拆息；'+('逐日公布的定盘利率。' if metric.endswith('_daily') else '官方公布的月平均利率。')+'数值按年利率百分数表示。'
    if metric.startswith('hk_prime_rate_hsbc'):
        return 'HSBC 最优惠贷款利率；'+('仅记录利率变更的生效日期，不是完整每日时间序列。' if metric.endswith('_effective') else '官方公布的月平均值。')
    if metric.startswith('hk_all_property_'):
        meanings={
            'hk_all_property_building_mortgage_deeds_count':'建筑融资按揭／建筑法定押记文书宗数；不是普通住宅按揭总数。',
            'hk_all_property_other_mortgage_deeds_count':'其他按揭／法定押记文书宗数，跨住宅、非住宅及土地。',
            'hk_all_property_mortgage_deeds_count':'LR 第 5、6 项合计的全物业按揭／法定押记文书宗数；并非独立贷款或住宅套数。',
            'hk_all_property_discharge_deeds_count':'收据／解除按揭／解除押记文书宗数；不能直接从新按揭宗数相减为购房贷款。',
        }
        return meanings[metric]
    if metric=='hk_all_building_sales_count':
        return '住宅和非住宅楼宇买卖合约的登记宗数，排除土地买卖；使用文书宗数而非涉及单位数。'
    if metric.startswith('hk_residential_'):
        return row['metric_name']+'；登记时间不一定是成交时间。'+('金额是物业买卖价而非贷款额。' if metric.endswith('_value') else '这里统计合约份数，不是贷款宗数。')
    return row['metric_name']+'；定义以以下来源及备注为准。'


def write(rows, path, generated_at):
    """Write every present ID once, grouped like the original workbook."""
    series=defaultdict(list)
    for row in rows:series[row['metric_id']].append(row)
    lines=['# 全部指标字典 / Complete indicator guide','',
           f'本次发布共 **{len(series)} 个指标**；自动生成时间：`{generated_at}`。',
           '每个 ID 都有独立说明。日期范围只统计非空值；范围内仍可能缺期。',
           '官方数据与推算共存在同一数据集：用 status、flags、note 区分。', '',
           '## 怎样读 RVD 指标名称','',
           '`rvd_1_3_all_classes` = RVD 的 1.3 租金指数表 + 全部住宅面积类别。',
           '`rvd_1_3_allclass` 不是有效 ID；请使用目录中的完整拼写。',
           '`1_1` 平均租金；`1_2` 平均售价；`1_3` 租金指数；`1_4` 售价指数；`1_5` 选定屋苑售价指数。',
           '`all_classes` 为全部面积类别；`class_a` 至 `class_e` 为具体面积类别，`classes_a_b_c` / `classes_d_e` 为合并类别。',
           '实用面积：A <40 m²；B 40–69.9 m²；C 70–99.9 m²；D 100–159.9 m²；E ≥160 m²。',
           '`hong_kong` 港岛；`kowloon` 九龙；`new_territories` 新界；`urban` 市区；`all` 合计。',
           '[RVD 技术附注](https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) · [RVD 数据字典](https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf)', '',
           '## 单位与频率','',
           '`HKD million` 为百万港元，乘 1,000,000 才是港元；`1999=100` 为指数，不是货币。',
           '`fraction` 的 0.25 表示 25%；`%` 或 `% p.a.` 的 2.5 已表示 2.5%，不要再乘 100。',
           '`deeds` / `份` 是登记文书宗数；`loans` 是贷款宗数；`estimated loans` 是模型推算宗数，保留小数以便核对。',
           '`D` 每日；`M` 每月；`Q` 每季；`A` 每年；`E` 利率生效事件。不同频率不自动插值。', '',
           '## 指标目录','']
    for sheet in ORDER:
        selected={m:part for m,part in series.items() if sheet_for(part[-1])==sheet}
        if not selected:continue
        lines.extend([f'## {group_for(sheet)} / {sheet}', ''])
        for metric,part in sorted(selected.items()):
            last=max(part,key=lambda r:r['date']);valid=[r['date'] for r in part if r['value'] is not None]
            coverage=f'{min(valid)} — {max(valid)}' if valid else '暂无可计算／已发布数值'
            urls=last.get('source_url','').split('; ')
            links=' · '.join(f'[来源 {i}]({url})' for i,url in enumerate(urls,1))
            note=last.get('note','').replace('\n',' ')
            lines.extend([f'### `{metric}`','',
                          f"- 名称：{last['metric_name']}",
                          '- 含义：'+describe(last),
                          f"- 单位：`{last['unit']}`；频率：`{last['frequency']}`；非空值范围：{coverage}。",
                          f"- 最新记录（{last['date']}）状态：{last.get('status','')}；标记：`{last.get('flags','') or '无'}`。",
                          f"- 最新记录来源：{last.get('source_name','')}。{links}",
                          f"- 源表／计算表：{last.get('source_table') or '见来源文件'}；字段／公式：{last.get('source_field') or last['metric_name']}。",
                          '- 口径备注：'+(note or '见来源原表。'),''])
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('\n'.join(lines),encoding='utf-8')
