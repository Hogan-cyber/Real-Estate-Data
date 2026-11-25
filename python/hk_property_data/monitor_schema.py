"""Stable, dependency-free names for the copied Mortgage Monitor workbook."""

REPOSITORY = 'Hogan-cyber/HK-Mortgage-Monitor'
WORKBOOK = 'hk_mortgage_data.xlsx'
# key: worksheet, date heading, frequency, indicator group, fields
# Each field: stable ID suffix, original heading, English name, unit.
LAYOUTS = {
    'registrations': ('中原按揭', '月份', 'M', 'Monitor registrations', [
        ('completed_count','现楼按揭宗数','Completed-property mortgage registrations','registrations'),
        ('offplan_count','楼花按揭宗数','Off-plan mortgage registrations','registrations'),
        ('private_completed_count','私人住宅现楼宗数','Private residential completed-property registrations','registrations'),
        ('subsidized_count','资助房屋宗数','Subsidized housing mortgage registrations','registrations'),
    ]),
    'bank': ('HKMA', '月份', 'M', 'Monitor bank mortgages', [
        ('bank_applications_count','新申请宗数','Bank mortgage applications','loans'),
        ('bank_approved_count','新批出宗数','Bank mortgage approvals','loans'),
        ('bank_approved_amount','新批出金额(HK$Mn)','Bank mortgage approvals amount','HKD million'),
        ('bank_approved_primary_count','一手宗数','Bank primary-purchase approvals','loans'),
        ('bank_approved_secondary_count','二手宗数','Bank secondary-purchase approvals','loans'),
        ('bank_approved_refinancing_count','转按宗数','Bank refinancing approvals','loans'),
        ('bank_approved_primary_amount','一手金额(HK$Mn)','Bank primary-purchase approvals amount','HKD million'),
        ('bank_approved_secondary_amount','二手金额(HK$Mn)','Bank secondary-purchase approvals amount','HKD million'),
        ('bank_approved_refinancing_amount','转按金额(HK$Mn)','Bank refinancing approvals amount','HKD million'),
        ('bank_drawn_count','新取用宗数','Bank mortgage drawdowns','loans'),
        ('bank_drawn_amount','新取用金额(HK$Mn)','Bank mortgage drawdown amount','HKD million'),
        ('bank_average_approved_amount','平均贷款额(HK$Mn)','Average approved bank loan','HKD million'),
        ('bank_outstanding_amount','未偿还总额(HK$Mn)','Outstanding bank mortgages','HKD million'),
    ]),
    'registry': ('土地注册处', '月份', 'M', 'Monitor registry documents', [
        ('registry_building_count','楼宇按揭宗数','Building mortgages (LR category)','documents'),
        ('registry_other_count','其他按揭/法定押记宗数','Other mortgages and legal charges','documents'),
        ('registry_discharge_count','撤销按揭宗数','Mortgage discharges and releases','documents'),
    ]),
    'm3': ('M3', '月份', 'M', 'Monitor money supply', [
        ('m3_hkd','港元M3(HK$Mn)','Hong Kong dollar M3','HKD million'),
        ('m3_total','所有货币M3(HK$Mn)','All-currency M3','HKD million'),
    ]),
    'prime': ('HSBC Prime', '生效日期', 'E', 'Monitor prime rate', [
        ('prime_rate_hsbc_effective','HSBC Prime Rate(%)','HSBC prime rate (effective date)','% p.a.'),
    ]),
    'hibor': ('HIBOR Daily', '日期', 'D', 'Monitor HIBOR', [
        ('hibor_overnight_daily','Overnight(%)','HIBOR overnight','% p.a.'),
        ('hibor_1w_daily','1 Week(%)','HIBOR 1 week','% p.a.'),
        ('hibor_1m_daily','1 Month(%)','HIBOR 1 month','% p.a.'),
        ('hibor_3m_daily','3 Months(%)','HIBOR 3 months','% p.a.'),
        ('hibor_6m_daily','6 Months(%)','HIBOR 6 months','% p.a.'),
        ('hibor_12m_daily','12 Months(%)','HIBOR 12 months','% p.a.'),
    ]),
    'nonbank': ('非银行', 'Date', 'M', 'Monitor estimates', [
        ('nonbank_residual_count','非银行贷款宗数','Non-bank residual estimate','loans (estimate)'),
        ('bank_purchase_drawn_count_estimate','真实买卖总数','Estimated bank purchase drawdowns','loans (estimate)'),
    ]),
}
METRIC_IDS = tuple('monitor_'+field[0] for layout in LAYOUTS.values() for field in layout[4])
GROUPS = {('monitor_'+field[0]): layout[3] for layout in LAYOUTS.values() for field in layout[4]}
SHEETS = {('monitor_'+field[0]): 'Monitor_'+key.title() for key,layout in LAYOUTS.items() for field in layout[4]}

MODEL_NOTE = ('Saved workbook model, not an observed lender count. Bank purchase drawdowns = '
              '(primary + secondary approvals) / total approvals * drawdowns, at the bank month. '
              'Residual at registration month t = completed + off-plan registrations at t '
              'minus prior-month bank purchase drawdowns. The fixed one-month lag and approval '
              'mix are assumptions. Completed-property totals include more than private housing; '
              'registration and lending coverage differ. No residual amount is provided.')
