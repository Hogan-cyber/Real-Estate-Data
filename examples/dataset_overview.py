"""Run in Spyder or Python 3.10+ with hk-property-data 0.6.0+.

Group definitions are built into the reader. Reads share a bounded session cache.
"""

# %% 1. See the whole dataset.
import hk_property_data as hk

try:
    from IPython.display import display
except ImportError:
    display = print

market = hk.Residential()
overview = market.overview()
catalog = market.catalog()
all_data = market.history(labels="id")

print("Package:", hk.__version__)
print("Snapshot generated:", all_data.attrs["data_generated_at"])
print(f"{len(catalog)} indicators; {len(all_data):,} date rows")
display(overview)
display(all_data)

# %% 2. Select a group and dates. Copy a group name from overview.
group_name = "Price indices"
df = market.history(group=group_name, start="2025-01", end=None)
display(market.catalog(group=group_name)[["metric_name", "unit", "frequency", "first_date", "last_date"]])
display(df)

# %% 3. Select multiple groups, or a frequency within a mixed-frequency group.
prices_and_rents = market.history(group=["Price indices", "Rent indices"], start="2025-01")
display(prices_and_rents.tail(3))
monthly_hibor = market.history(group="HIBOR", frequency="M", start="2025-01")
display(monthly_hibor.tail(3))

# %% 4. Existing metric IDs and suffix selection still work.
prices = market.catalog(group="Average prices")
kowloon_ids = prices.index[prices.index.str.endswith("_kowloon")].tolist()
kowloon = market.history(series=kowloon_ids, start="2025-01")
display(kowloon.tail(3))
selected = market.history(series=["rvd_1_4_all_classes", "rvd_1_3_all_classes"],
                          start="2025-01", end="2025-12", labels="id")
display(selected.tail(3))

# %% 5. Check an original source record.
source = market.observations(group="Bank mortgages", series="hk_mortgage_drawn_amount",
                             start="2025-01", end="2025-01")
display(source[["date", "metric_name", "value", "unit", "status", "source_url"]])

# Explicit refresh: rerun the other reads to replace their older DataFrames.
# overview = market.overview(refresh=True)
