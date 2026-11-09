"""Small, dependency-free navigation groups for published indicator IDs.

These labels describe families of observations; they never change source values
or turn the existing mortgage allocation estimates into official observations.
"""

_GROUP_PREFIXES = {
    'Transactions': ('hk_residential_sales_', 'hk_residential_primary_sales_',
                     'hk_residential_secondary_sales_', 'hk_all_building_sales_'),
    'Average rents': ('rvd_1_1_',),
    'Average prices': ('rvd_1_2_',),
    'Rent indices': ('rvd_1_3_',),
    'Price indices': ('rvd_1_4_',),
    'Popular developments': ('rvd_1_5_',),
    'Annual supply': ('rvd_stock_', 'rvd_completions_', 'rvd_vacancy_', 'rvd_takeup_'),
    'Bank mortgages': ('hk_mortgage_',),
    'Mortgage registrations': ('hk_all_property_',),
    'Negative equity': ('hk_negative_equity_',),
    'Money supply': ('hk_m1_', 'hk_m2_', 'hk_m3_'),
    'HIBOR': ('hk_hibor_',),
    'Prime rate': ('hk_prime_rate_hsbc',),
}
_MODEL_INPUT_SHARES = frozenset({
    'hk_residential_sales_share',
    'hk_bank_mortgage_refinancing_count_share',
    'hk_bank_mortgage_refinancing_amount_share',
})
_MODEL_PREFIXES = ('hk_residential_mortgage_', 'hk_bank_mortgage_purchase_',
                   'hk_money_lender_mortgage_')
_OTHER = 'Other / new indicators'
_GROUP_NAMES = (*_GROUP_PREFIXES, 'Mortgage estimates', _OTHER)


def group_for(metric_id):
    """Classify a stable ID; keep future unknown families visible."""
    if metric_id in _MODEL_INPUT_SHARES or (
            metric_id.startswith(_MODEL_PREFIXES) and metric_id.endswith('_estimate')):
        return 'Mortgage estimates'
    for name, prefixes in _GROUP_PREFIXES.items():
        if metric_id.startswith(prefixes):
            return name
    return _OTHER


def _key(value):
    return ' '.join(value.replace('_', ' ').split()).casefold()


def normalise_groups(group):
    if group is None:
        return None
    if isinstance(group, str):
        group = [group]
    try:
        values = tuple(group)
    except TypeError as exc:
        raise ValueError('group must be a group name or iterable of group names') from exc
    if not values or any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError('group must contain at least one nonempty group name')
    names = {_key(name): name for name in _GROUP_NAMES}
    unknown = [value for value in values if _key(value) not in names]
    if unknown:
        raise ValueError('Unknown groups: ' + ', '.join(unknown) +
                         '. Available groups: ' + ', '.join(_GROUP_NAMES))
    return tuple(dict.fromkeys(names[_key(value)] for value in values))


def normalise_frequency(frequency):
    if frequency is None:
        return None
    if not isinstance(frequency, str) or frequency.strip().upper() not in ('D', 'M', 'Q', 'A', 'E'):
        raise ValueError('frequency must be D, M, Q, A, E, or None')
    return frequency.strip().upper()
