"""Collect official Hong Kong residential sale and purchase registrations.

The Land Registry's own page loads the JSON endpoints discovered in its JS.
No API key or third party packages are required. collect() returns six series
for the latest 24 available months as of the supplied date. Publication dates
are not provided in these JSON files and are deliberately left null.

Usage: python3 hk_landreg_collector.py --as-of 2026-10-27 --cache-dir work/lr_cache
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import hashlib
import json
import pathlib
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor


ORIGIN = "https://www.landreg.gov.hk"
SCRIPT_URL = ORIGIN + "/js/load-agt-primary.js"
PAGE_URL = ORIGIN + "/en/monthly/agt-primary.htm"
COUNT_KEY = "Number of ASP for Residential Building Units"
AMOUNT_KEY = "Consideration of ASP for Residential Building Units"
USER_AGENT = "HongKongResidentialDataCollector/1.0 (official public statistics)"
SERIES = (
    ("hk_residential_sales_count", COUNT_KEY, "住宅楼宇买卖合约登记宗数", "份", "一手及二手合计", "t1"),
    ("hk_residential_primary_sales_count", "Number of Primary Sales for ASP Residential Building Units", "一手住宅楼宇买卖合约登记宗数", "份", "一手住宅", "t1"),
    ("hk_residential_secondary_sales_count", "Number of Secondary Sales for ASP Residential Building Units", "二手住宅楼宇买卖合约登记宗数", "份", "二手住宅", "t1"),
    ("hk_residential_sales_value", AMOUNT_KEY, "住宅楼宇买卖合约登记金额", "HKD million", "一手及二手合计", "t2"),
    ("hk_residential_primary_sales_value", "Consideration of Primary Sales for ASP Residential Building Units", "一手住宅楼宇买卖合约登记金额", "HKD million", "一手住宅", "t2"),
    ("hk_residential_secondary_sales_value", "Consideration of Secondary Sales for ASP Residential Building Units", "二手住宅楼宇买卖合约登记金额", "HKD million", "二手住宅", "t2"),
)


def _get(url, cache_dir):
    """Revalidate a cached response on every call; never hide network failure."""
    cache_file = None
    cached = None
    headers = {"User-Agent": USER_AGENT}
    if cache_dir is not None:
        folder = pathlib.Path(cache_dir)
        folder.mkdir(parents=True, exist_ok=True)
        cache_file = folder / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                if cached.get("url") != url or not isinstance(cached.get("body"), str):
                    cached = None
            except (ValueError, OSError):
                cached = None
        if cached:
            if cached.get("etag"):
                headers["If-None-Match"] = cached["etag"]
            if cached.get("last_modified"):
                headers["If-Modified-Since"] = cached["last_modified"]
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = {
                "url": url,
                "body": response.read().decode("utf-8-sig"),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            }
    except urllib.error.HTTPError as error:
        if error.code == 304 and cached:
            return cached
        raise RuntimeError(f"Land Registry request failed: {url}: {error}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"Land Registry request failed: {url}: {error}") from error
    if cache_file:
        temporary = cache_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(cache_file)
    return payload


def _parse_table(payload, key):
    rows = json.loads(payload["body"])
    if not isinstance(rows, list):
        raise ValueError(f"Unexpected Land Registry JSON shape: {payload['url']}")
    parsed = {}
    for row in rows:
        if key not in row or "Year" not in row or "Month" not in row:
            raise ValueError(f"Land Registry schema changed: {payload['url']}")
        month = row["Month"]
        if str(month).strip().lower() == "total":
            continue
        year, month = int(row["Year"]), int(month)
        if not 1 <= month <= 12:
            raise ValueError(f"Unexpected month: {month}")
        value = row[key]
        if value is None or str(value).strip() in ("", "-", "--"):
            continue
        if isinstance(value, bool):
            raise ValueError("Boolean value in Land Registry statistics")
        number = float(str(value).replace(",", ""))
        if not 0 <= number < float("inf") or not number.is_integer():
            raise ValueError(f"Invalid count or HKD-million amount: {value}")
        month_end = dt.date(year, month, calendar.monthrange(year, month)[1])
        if month_end in parsed:
            raise ValueError(f"Duplicate month in source: {month_end}")
        parsed[month_end] = (int(number), payload["url"], payload.get("last_modified"))
    return parsed


def _as_date(as_of):
    if as_of is None:
        # Hong Kong has no daylight-saving clock changes.
        return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()
    if isinstance(as_of, dt.datetime):
        return as_of.date()
    if isinstance(as_of, dt.date):
        return as_of
    return dt.date.fromisoformat(str(as_of)[:10])


def _months_ending(latest, length=24):
    index = latest.year * 12 + latest.month - 1
    result = []
    for offset in range(length - 1, -1, -1):
        year, zero_month = divmod(index - offset, 12)
        month = zero_month + 1
        result.append(dt.date(year, month, calendar.monthrange(year, month)[1]))
    return result


def collect(cache_dir=None, as_of=None):
    """Return 144 records: total/primary/secondary count and value for 24 months.

    as_of limits observation months, not the historical vintage of revisions.
    cache_dir can be None to disable disk caching. Network errors and incomplete
    monthly coverage raise exceptions instead of silently returning stale data.
    """
    cutoff = _as_date(as_of)
    script = _get(SCRIPT_URL, cache_dir)["body"]
    path_match = re.search(r'jsonInterPath\s*=\s*[\"\']([^\"\']+)[\"\']', script)
    if not path_match or not path_match.group(1).startswith("/json/"):
        raise ValueError("Cannot discover Land Registry monthly JSON path")
    base = ORIGIN + path_match.group(1).rstrip("/")
    variable_ranges = dict(re.findall(r'var\s+(agtP\d+)\s*=\s*[\"\'](\d{4}(?:-\d{4})?)[\"\']', script))
    discovered = re.findall(r'[\"\'](agt-primary|agt-pri-\d+)[\"\']\s*:\s*(agtP\d+)', script)
    blocks = []
    for block, variable in discovered:
        years = variable_ranges.get(variable)
        if years:
            parts = [int(year) for year in years.split("-")]
            blocks.append((block, min(parts), max(parts)))
    if not any(block == "agt-primary" for block, _, _ in blocks):
        raise ValueError("Cannot discover current Land Registry data block")
    # The current block can carry more history than its page title advertises.
    # Read it first, then discover archives only when older months are needed.
    ordered = [entry for entry in blocks if entry[0] == "agt-primary"]
    ordered += sorted((entry for entry in blocks if entry[0] != "agt-primary" and entry[1] <= cutoff.year), key=lambda entry: entry[2], reverse=True)
    monthly = {metric_id: {} for metric_id, *_ in SERIES}
    selected = None
    for block, _, _ in ordered:
        urls = [f"{base}/{block}/t1.json", f"{base}/{block}/t2.json"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            count_payload, amount_payload = list(pool.map(lambda url: _get(url, cache_dir), urls))
        # Prefer the current/recent block in the event of overlapping revisions.
        block_series = {}
        for metric_id, key, _, _, _, table in SERIES:
            block_series[metric_id] = _parse_table(count_payload if table == "t1" else amount_payload, key)
        block_common = set.intersection(*(set(series) for series in block_series.values()))
        for date in block_common:
            count_total = block_series["hk_residential_sales_count"][date][0]
            count_parts = sum(block_series[key][date][0] for key in ("hk_residential_primary_sales_count", "hk_residential_secondary_sales_count"))
            amount_total = block_series["hk_residential_sales_value"][date][0]
            amount_parts = sum(block_series[key][date][0] for key in ("hk_residential_primary_sales_value", "hk_residential_secondary_sales_value"))
            if count_total != count_parts:
                raise ValueError(f"Residential count components disagree with total: {date}")
            # Each published amount is independently rounded to HKD million.
            if abs(amount_total - amount_parts) > 1:
                raise ValueError(f"Residential consideration components disagree with total beyond rounding: {date}")
        for metric_id, series in block_series.items():
            for date, record in series.items():
                monthly[metric_id].setdefault(date, record)
        common = sorted(date for date in set.intersection(*(set(series) for series in monthly.values())) if date <= cutoff)
        if common:
            desired = _months_ending(common[-1])
            if all(all(date in series for series in monthly.values()) for date in desired):
                selected = desired
                break
    if selected is None:
        raise ValueError(f"Could not obtain 24 complete residential months as of {cutoff}")
    records = []
    for date in selected:
        for metric_id, _, name, unit, scope, _ in SERIES:
            value, source_url, last_modified = monthly[metric_id][date]
            note = (
                "直接使用土地注册处公布的住宅分项或合计；"
                "统计月份为送交登记月份，并非签约月份；非所有楼宇口径。"
                "金额为官方按百万港元公布的数值，分项四舍五入可能不等于合计。"
                "不包括尚受转售限制的资助出售住宅；已补地价并解除限制者按官方定义纳入。"
                "官方JSON未提供最初发布日期；HTTP最后修改时间不能视为发布日期。"
                "as_of只筛选观察月份，数据采用抓取时官网最新修订值。"
            )
            if last_modified:
                note += f" 来源HTTP最后修改：{last_modified}。"
            records.append({
                "market": "HK", "category": "sales", "metric_id": metric_id,
                "metric_name": name, "period": date.strftime("%Y-%m"),
                "date": date.isoformat(), "value": value, "unit": unit,
                "frequency": "monthly", "scope": "香港全境住宅楼宇，" + scope,
                "seasonal_adjustment": "NSA", "source_name": "香港土地注册处",
                "source_url": source_url, "published_date": None, "note": note,
                "fetch_mode": "automatic_json",
            })
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default=None, help="Observation cutoff YYYY-MM-DD")
    parser.add_argument("--cache-dir", default=None, help="Optional raw response cache folder")
    arguments = parser.parse_args()
    print(json.dumps(collect(arguments.cache_dir, arguments.as_of), ensure_ascii=False, indent=2))
