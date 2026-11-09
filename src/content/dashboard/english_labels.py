"""English presentation labels; original observation fields stay unchanged."""

LAND_REGISTRY_NAMES = {
    'hk_all_building_sales_count': 'All building sale agreements registered',
    'hk_all_property_building_mortgage_deeds_count': 'Building-finance mortgage / charge documents registered',
    'hk_all_property_other_mortgage_deeds_count': 'Other mortgage / charge documents registered',
    'hk_all_property_mortgage_deeds_count': 'All-property mortgage / charge documents registered',
    'hk_all_property_discharge_deeds_count': 'Receipt / discharge / release documents registered',
    'hk_residential_sales_count': 'Residential sale agreements registered',
    'hk_residential_sales_value': 'Residential sale agreements: value',
    'hk_residential_primary_sales_count': 'Primary residential sale agreements registered',
    'hk_residential_primary_sales_value': 'Primary residential sale agreements: value',
    'hk_residential_secondary_sales_count': 'Secondary residential sale agreements registered',
    'hk_residential_secondary_sales_value': 'Secondary residential sale agreements: value',
}
MORTGAGE = {
    'applications': 'New residential mortgage applications received during the month; applications need not be approved or drawn.',
    'approved_amount': 'New residential mortgages approved during the month, including primary purchases, secondary purchases and refinancing; not actual drawdowns.',
    'approved_count': 'Number of new residential mortgages approved during the month, including purchases and refinancing.',
    'approved_average_size': 'Average amount per newly approved mortgage; not an average property price.',
    'approved_ltv': 'Loan amount as a percentage of property value for new approvals, weighted by loan amount.',
    'approved_tenor': 'Contractual loan term for new approvals, in months and weighted by loan amount.',
    'approved_primary_amount': 'Amount approved for primary-market residential purchases.',
    'approved_primary_count': 'Number of loans approved for primary-market residential purchases.',
    'approved_secondary_amount': 'Amount approved for secondary-market residential purchases.',
    'approved_secondary_count': 'Number of loans approved for secondary-market residential purchases.',
    'approved_refinancing_amount': 'Amount of residential refinancing loans approved during the month.',
    'approved_refinancing_count': 'Number of residential refinancing loans approved during the month.',
    'approved_undrawn_amount': 'Amount approved during the month but not yet drawn.',
    'approved_undrawn_count': 'Number of mortgages approved during the month but not yet drawn.',
    'drawn_amount': 'Amount actually drawn during the month, including refinancing. The published total has no purchase / refinancing split.',
    'drawn_count': 'Number of mortgages actually drawn during the month; these need not be the same loans approved or registered that month.',
    'outstanding': 'Residential mortgage loans outstanding at month-end. A stock, not monthly new lending; do not sum balances across months.',
    'delinquency': 'Share of residential mortgage loans overdue for more than three months.',
    'delinquency_6m': 'Share of residential mortgage loans overdue for more than six months.',
    'rescheduled_ratio': 'Share of residential mortgage loans with rescheduled repayment terms.',
    'written_off_amount': 'Residential mortgage amount written off during the month.',
    'written_off_12m_amount': 'Cumulative residential mortgage amount written off over the preceding twelve months.',
    'written_off_12m_ratio': 'Twelve-month write-offs relative to average outstanding residential mortgage loans.',
    'pricing_blr_share': 'Share of newly approved mortgages priced against the best lending / Prime rate; not the interest-rate level.',
    'pricing_hibor_share': 'Share of newly approved mortgages priced against HIBOR; not the HIBOR interest-rate level.',
    'pricing_fixed_share': 'Share of newly approved mortgages with fixed-rate pricing.',
    'pricing_other_share': 'Share of newly approved mortgages with other pricing arrangements.',
    'cofinancing_approved_amount': 'Reporting banks\' portion of newly approved co-financed residential mortgages.',
    'cofinancing_approved_count': 'Number of newly approved co-financed residential mortgages.',
    'cofinancing_government_outstanding_amount': 'Banks\' outstanding portion of mortgages co-financed with government housing loan schemes.',
    'cofinancing_government_outstanding_count': 'Number of outstanding mortgages co-financed with government housing loan schemes.',
    'cofinancing_private_outstanding_amount': 'Banks\' outstanding portion of privately co-financed mortgages; not independent money-lender lending.',
    'cofinancing_private_outstanding_count': 'Number of privately co-financed mortgages; not an independent count of money-lender loans.',
}
NEGATIVE = {
    'count': 'Known negative-equity bank first mortgages at quarter-end; a stock, not monthly originations.',
    'amount': 'Outstanding balance of negative-equity mortgages at quarter-end; not the loss amount.',
    'amount_share': 'Negative-equity mortgage balances as a share of surveyed mortgage balances.',
    'borrower_share': 'Negative-equity mortgage borrowers as a share of surveyed mortgage borrowers.',
    'delinquency': 'Share of negative-equity mortgages overdue for more than three months. Negative equity alone does not mean default.',
    'ltv': 'Outstanding loan balances relative to the collateral property value for negative-equity mortgages.',
    'unsecured_amount': 'The part of negative-equity mortgage balances above the value of collateral properties.',
}


def english_name(row):
    return LAND_REGISTRY_NAMES.get(row['metric_id'], row['metric_name'])


def english_definition(row):
    metric = row['metric_id']
    if metric == 'hk_all_building_sales_count':
        return 'Registered sale agreements for residential and non-residential buildings, excluding land. Counts documents, not individual units; the registration month may differ from the agreement month.'
    if metric.startswith('hk_all_property_'):
        detail = {
            'hk_all_property_building_mortgage_deeds_count': 'Building-finance mortgages / building legal charges (LR item 5).',
            'hk_all_property_other_mortgage_deeds_count': 'Other mortgages / legal charges (LR item 6).',
            'hk_all_property_mortgage_deeds_count': 'All-property mortgage / charge documents (LR items 5 + 6).',
            'hk_all_property_discharge_deeds_count': 'Receipts / discharges / releases; not the opposite flow of newly registered purchase mortgages.',
        }[metric]
        return detail + ' Counts registration documents across residential, non-residential and land; not unique properties or loans. Bank / non-bank and purchase / refinancing are not separately identified. LR does not publish the corresponding loan amounts. Registration can lag execution.'
    if metric in LAND_REGISTRY_NAMES:
        return english_name(row) + '. Land Registry registration month, not the contract signing month. Residential scope excludes subsidized-sale homes still subject to resale restrictions. Amounts are property sale values in HKD million, not mortgage amounts; rounded components may differ from totals.'
    if metric.startswith('hk_mortgage_'):
        return MORTGAGE.get(metric.removeprefix('hk_mortgage_'), row['note'])
    if metric.startswith('hk_negative_equity_'):
        return NEGATIVE.get(metric.removeprefix('hk_negative_equity_'), row['note'])
    # Published notes already document RVD classes, rates, monetary stocks,
    # LR document definitions and every existing model formula in English.
    return english_name(row) + '. ' + row.get('note', '')
