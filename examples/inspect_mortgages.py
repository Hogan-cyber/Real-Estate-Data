"""Read the published GitHub dataset with the lightweight package; no crawler runs."""
from hk_property_data import fetch_dataset


METRICS = [
    'hk_residential_sales_count', 'hk_residential_sales_value',
    'hk_residential_primary_sales_count', 'hk_residential_primary_sales_value',
    'hk_residential_secondary_sales_count', 'hk_residential_secondary_sales_value',
    'hk_mortgage_approved_count', 'hk_mortgage_drawn_count',
    'hk_mortgage_approved_primary_count', 'hk_mortgage_approved_secondary_count',
    'hk_mortgage_approved_refinancing_count', 'hk_mortgage_approved_purchase_count',
    'hk_all_property_mortgage_deeds_count', 'hk_all_property_discharge_deeds_count',
]


def select_series(dataset, metric_id, start=None, end=None):
    """Return complete source records in calendar order; missing values stay None."""
    return sorted((row for row in dataset['observations'] if row['metric_id']==metric_id
                   and (start is None or row['period']>=start)
                   and (end is None or row['period']<=end)),key=lambda row:row['period'])


def main():
    dataset = fetch_dataset()
    print('Source checks:', dataset['checked_at'])
    print('Errors:', dataset['errors'])
    print('Notes:', dataset.get('warnings',[]))
    for metric in METRICS:
        history = select_series(dataset,metric)
        available = [row for row in history if row['value'] is not None]
        if not available:
            print(metric, 'Unavailable in this published snapshot')
            continue
        latest = available[-1]
        print(metric, available[0]['period'], 'to', latest['period'],
              latest['value'], latest['unit'], latest.get('observation_type','official'))
    print('\nPurchase approvals are not purchase drawdowns or non-bank originations.')
    print('Land Registry instrument counts cover all properties, not only mortgaged residential sales.')


if __name__ == '__main__':
    main()
