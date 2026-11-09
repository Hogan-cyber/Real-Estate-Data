"""Run in Spyder or Python 3.10+ after installing hk-property-data 0.5.0+.

Reads GitHub's published snapshot once; later selections reuse the session cache.
The group labels below are an example navigation aid, not new data or package APIs.
"""

# %% 1. Load the complete numeric dataset and its indicator catalogue.
import pandas as pd
import hk_property_data as hk

try:
    from IPython.display import display
except ImportError:
    display = print

market = hk.Residential()
catalog = market.catalog()
all_data = market.history(labels="id")

print("Package:", hk.__version__)
print("Snapshot generated:", all_data.attrs["data_generated_at"])
print(f"{len(catalog)} indicators; {len(all_data):,} date rows")

# %% 2. Group related indicators; retain every ID and its original definition.
GROUP_PREFIXES = {
    "Transactions": ("hk_residential_sales_", "hk_residential_primary_sales_", "hk_residential_secondary_sales_", "hk_all_building_sales_"),
    "Average rents": ("rvd_1_1_",),
    "Average prices": ("rvd_1_2_",),
    "Rent indices": ("rvd_1_3_",),
    "Price indices": ("rvd_1_4_",),
    "Popular developments": ("rvd_1_5_",),
    "Annual supply": ("rvd_stock_", "rvd_completions_", "rvd_vacancy_", "rvd_takeup_"),
    "Bank mortgages": ("hk_mortgage_",),
    "Mortgage registrations": ("hk_all_property_",),
    "Negative equity": ("hk_negative_equity_",),
    "Money supply": ("hk_m1_", "hk_m2_", "hk_m3_"),
    "HIBOR": ("hk_hibor_",),
    "Prime rate": ("hk_prime_rate_hsbc",),
}
MODEL_INPUT_SHARES = {
    "hk_residential_sales_share",
    "hk_bank_mortgage_refinancing_count_share",
    "hk_bank_mortgage_refinancing_amount_share",
}


def indicator_group(metric_id):
    if metric_id.endswith("_estimate") or metric_id in MODEL_INPUT_SHARES:
        return "Mortgage estimates"
    for group, prefixes in GROUP_PREFIXES.items():
        if metric_id.startswith(prefixes):
            return group
    return "Other / new indicators"  # Future indicators remain visible.


catalog["group"] = catalog.index.map(indicator_group)
overview = catalog.groupby(["group", "frequency"], sort=True).agg(
    indicators=("metric_name", "size"),
    records=("observations", "sum"),
    available_values=("non_missing", "sum"),
    first_date=("first_date", "min"),
    last_date=("last_date", "max"),
)
display(overview)

# %% 3. A small monthly view: six existing indicators, no calculated values.
core_ids = [
    "rvd_1_4_all_classes",
    "rvd_1_3_all_classes",
    "hk_residential_sales_count",
    "hk_mortgage_drawn_amount",
    "hk_hibor_1m",
    "hk_m3_hkd",
]
catalog_columns = ["metric_name", "unit", "frequency", "first_date", "last_date"]
display(catalog.loc[core_ids, catalog_columns])
core = market.history(series=core_ids, labels="name")
display(core.tail(6))

# %% 4. Choose a group and dates. Copy any group name from overview.
group_name = "Price indices"
start, end = "2025-01", None  # None includes all subsequently available dates.
members = catalog.loc[catalog["group"].eq(group_name)]
if members.empty:
    raise ValueError(f"Unknown or empty group: {group_name!r}; inspect overview")
display(members[catalog_columns])
df = market.history(series=members.index.tolist(), start=start, end=end, labels="id")
display(df.tail(6))

# %% 5. Select suffixes, multiple IDs, and a date range from the same snapshot.
# Example: classes A-E in Kowloon, average prices only.
area_ids = catalog.index[
    catalog.index.str.startswith("rvd_1_2_")
    & catalog.index.str.endswith("_kowloon")
].tolist()
area_prices = market.history(series=area_ids, start="2025-01", labels="id")
display(area_prices.tail(3))

selected_ids = ["rvd_1_4_all_classes", "rvd_1_3_all_classes"]
selected = market.history(series=selected_ids, start="2025-01", end="2025-12", labels="id")
display(selected.tail(3))

# %% 6. Search by ID or name and look up the source of a specific observation.
keyword = "refinancing"
matches = catalog.loc[
    catalog.index.str.contains(keyword, case=False, regex=False)
    | catalog["metric_name"].str.contains(keyword, case=False, na=False, regex=False)
]
display(matches[["group"] + catalog_columns])
source = market.observations(series="hk_mortgage_drawn_amount", start="2025-01", end="2025-01")
display(source[["date", "metric_name", "value", "unit", "status", "source_url"]])

# Optional explicit refresh: rerun the analysis cells after replacing the snapshot.
# all_data = market.history(labels="id", refresh=True)
# catalog = market.catalog()
# No automatic filling, interpolation, resampling, or source-data edits occur.
