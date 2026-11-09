"""User-selected monthly allocation trial; never overwrites official inputs.

Change the formulas here, then run collect_residential.py --from-saved to
recalculate all exports. See docs/MORTGAGE_ESTIMATES.md for assumptions.
"""
from __future__ import annotations

import datetime as dt
import math
import calendar

METHOD_URL = 'https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/docs/MORTGAGE_ESTIMATES.md'
REGISTRATION_LAG_MONTHS = 1
INPUTS = {
    'hk_all_building_sales_count', 'hk_residential_sales_count',
    'hk_all_property_mortgage_deeds_count', 'hk_mortgage_drawn_count',
    'hk_mortgage_approved_count', 'hk_mortgage_approved_refinancing_count',
    'hk_mortgage_drawn_amount', 'hk_mortgage_approved_amount',
    'hk_mortgage_approved_refinancing_amount',
}
COUNT_COLUMNS = (
    'hk_residential_mortgage_count_estimate',
    'hk_bank_mortgage_purchase_drawn_count_estimate',
    'hk_money_lender_mortgage_count_estimate',
)
AMOUNT_COLUMNS = (
    'hk_residential_mortgage_amount_estimate',
    'hk_bank_mortgage_purchase_drawn_amount_estimate',
    'hk_money_lender_mortgage_amount_estimate',
)
SCOPE = ('Monthly allocation trial, not observed money-lender lending. '
         'Residential sales mix proxies mortgage mix; registrations and drawdowns differ. '
         'Refinancing removed only from banks; residual may include bank refinancing, '
         'other lenders, developer-related lending and timing/scope differences. ')


def _share(part, total):
    if total <= 0 or not 0 <= part <= total:
        raise ValueError('Invalid proportion')
    return part / total


def bank_period(registration_period, lag_months=REGISTRATION_LAG_MONTHS):
    """Month of bank inputs matched to an LR registration month; an assumption."""
    if type(lag_months) is not int or lag_months < 0:
        raise ValueError('registration lag must be a nonnegative integer')
    date = dt.date.fromisoformat(registration_period + '-01')
    year, month = divmod(date.year * 12 + date.month - 1 - lag_months, 12)
    return dt.date(year, month + 1, 1).strftime('%Y-%m')


def build(rows, registration_lag_months=REGISTRATION_LAG_MONTHS):
    """Return comparisons dated by LR month t, with bank inputs at t minus lag."""
    bank_period('2002-01', registration_lag_months)  # Validate even an empty input.
    by_month = {}
    for row in rows:
        if row['metric_id'] not in INPUTS or row.get('frequency') != 'M':
            continue
        part = by_month.setdefault(row['period'], {})
        if row['metric_id'] in part:
            raise ValueError(f"Duplicate mortgage input: {row['metric_id']} {row['period']}")
        part[row['metric_id']] = row
    result = []
    calculated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    bank_ids = {metric for metric in INPUTS if metric.startswith('hk_mortgage_')}
    for period, current in sorted(by_month.items()):
        bank_month = bank_period(period, registration_lag_months)
        bank_inputs = by_month.get(bank_month, {})
        original = {key: row for key, row in current.items() if key not in bank_ids}
        original.update({key: row for key, row in bank_inputs.items() if key in bank_ids})
        # Unrelated small exports need not acquire an empty model table.
        if not ({'hk_all_property_mortgage_deeds_count','hk_mortgage_drawn_count'} & original.keys()):
            continue
        data = dict(original)
        roots = {key: {key} for key in INPUTS}

        def add(metric, name, unit, deps, formula, calculate, *, estimated=True, flags=(), note=''):
            root_ids = set().union(*(roots[d] for d in deps))
            roots[metric] = root_ids
            inputs = [data.get(key) for key in deps]
            evidence = [original[key] for key in sorted(root_ids) if key in original]
            out_flags = {'MODEL_ESTIMATE' if estimated else 'CALCULATED', *flags}
            if root_ids & bank_ids:
                out_flags.add(f'REGISTRATION_LAG_ASSUMED_{registration_lag_months}M')
            for row in inputs:
                if row:
                    out_flags.update(filter(None, row.get('flags','').split(';')))
            value = None
            if any(row is None or row.get('value') is None for row in inputs):
                out_flags.add('MISSING_INPUT')
            elif any(isinstance(row['value'],bool) or not isinstance(row['value'],(int,float))
                     or not math.isfinite(row['value'])
                     or (row['metric_id'] in INPUTS and
                         (row['value'] < 0 or row.get('unit') not in
                          ({'HKD million'} if row['metric_id'].endswith('_amount') else {'loans','deeds','份'})))
                     for row in inputs):
                out_flags.add('INVALID_INPUT')
            else:
                try:
                    value = calculate(*(row['value'] for row in inputs))
                    if not math.isfinite(value):
                        raise ValueError('Non-finite result')
                except (ValueError, ZeroDivisionError, OverflowError):
                    value = None
                    out_flags.add('INVALID_INPUT')
            if value is not None and value < 0:
                out_flags.add('NEGATIVE_RESIDUAL')
            urls = sorted({r['source_url'] for r in evidence if r.get('source_url')})
            checks = [r.get('source_checked_at') for r in evidence]
            record = dict(metric_id=metric, metric_name=name, period=period,
                          date=f'{period}-{calendar.monthrange(*map(int, period.split("-")))[1]}', frequency='M', value=value,
                          unit=unit, status=('Estimated' if estimated else 'Calculated') if value is not None else 'Unavailable',
                          flags=';'.join(sorted(out_flags)), source_id='mortgage_estimates',
                          source_name='Repository calculation from '+ ' / '.join(sorted({r.get('source_name','') for r in evidence})),
                          source_url='; '.join(urls) if urls else METHOD_URL,
                          source_table='Monthly mortgage allocation trial v2; LR registration-month basis',
                          source_field=f'{formula}; LR={period}; HKMA={bank_month}',
                          note=(f'Formula: {formula}. LR registration month: t; HKMA input month: t-{registration_lag_months}; '
                                f'assumed registration lag: {registration_lag_months} month(s). Raw inputs: '
                                +', '.join(key+'@'+(f't-{registration_lag_months}' if key in bank_ids else 't') for key in sorted(root_ids))+'. '
                                +note+(SCOPE if estimated else 'Calculated ratio of official inputs from the indicated source month. ')
                                +'Method: '+METHOD_URL),
                          checked_at=calculated_at,
                          source_checked_at=min(checks) if checks and all(checks) else '')
            data[metric] = record
            result.append(record)

        share='hk_residential_sales_share'
        refi_n='hk_bank_mortgage_refinancing_count_share'
        refi_a='hk_bank_mortgage_refinancing_amount_share'
        total_n, bank_n, lender_n=COUNT_COLUMNS
        total_a, bank_a, lender_a=AMOUNT_COLUMNS
        avg='hk_bank_mortgage_purchase_average_amount_estimate'
        add(share,'Residential share of building sale agreements','fraction',
            ('hk_residential_sales_count','hk_all_building_sales_count'),
            'residential sales count / all building sales count',_share,estimated=False)
        add(refi_n,'Bank refinancing share of approvals: count','fraction',
            ('hk_mortgage_approved_refinancing_count','hk_mortgage_approved_count'),
            'refinancing approved count / total approved count',_share,estimated=False)
        add(refi_a,'Bank refinancing share of approvals: amount','fraction',
            ('hk_mortgage_approved_refinancing_amount','hk_mortgage_approved_amount'),
            'refinancing approved amount / total approved amount',_share,estimated=False)
        add(total_n,'Residential total: count estimate','estimated loans',
            ('hk_all_property_mortgage_deeds_count',share),
            'LR mortgage deeds * residential sales share',lambda m,s:m*s,
            flags=('SALES_MIX_PROXY','LR_REFINANCING_NOT_REMOVED'))
        add(bank_n,'Bank excluding refinancing: count estimate','estimated loans',
            ('hk_mortgage_drawn_count',refi_n),
            f'bank drawn count[t-{registration_lag_months}] * (1 - refinancing count share[t-{registration_lag_months}])',lambda d,r:d*(1-r),
            flags=('APPROVAL_MIX_PROXY',))
        add(bank_a,'Bank excluding refinancing: amount estimate','HKD million',
            ('hk_mortgage_drawn_amount',refi_a),
            f'bank drawn amount[t-{registration_lag_months}] * (1 - refinancing amount share[t-{registration_lag_months}])',lambda d,r:d*(1-r),
            flags=('APPROVAL_MIX_PROXY',))
        add(avg,'Bank purchase average loan: amount estimate','HKD million per loan',
            (bank_a,bank_n),'bank purchase amount estimate / bank purchase count estimate',
            lambda a,n:a/n)
        add(lender_n,'Money-lender residual: count estimate','estimated loans',
            (total_n,bank_n),'residential total count estimate - bank purchase count estimate',
            lambda a,b:a-b,flags=('UNIDENTIFIED_LENDER_RESIDUAL',))
        add(total_a,'Residential total: amount scenario','HKD million',
            (total_n,avg),'residential total count estimate * bank purchase average loan estimate',
            lambda n,a:n*a,flags=('BANK_AVERAGE_LOAN_SIZE_ASSUMED',))
        add(lender_a,'Money-lender residual: amount scenario','HKD million',
            (total_a,bank_a),'residential total amount scenario - bank purchase amount estimate',
            lambda a,b:a-b,flags=('UNIDENTIFIED_LENDER_RESIDUAL',))
    return result
