"""Collect official Hong Kong residential sale and purchase registrations.

The Land Registry's own page loads the JSON endpoints discovered in its JS.
collect() returns all six residential series from the official archive blocks,
supplemented with newer totals from the official monthly release's PDF annex,
and separate all-property mortgage/charge/discharge document counts from 1993.
JSON publication dates are deliberately left null; annex dates come from the
official release catalog. PDF extraction uses pdfplumber, with no AI service.

Usage: python3 hk_landreg_collector.py --as-of 2026-10-27 --cache-dir work/lr_cache
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import hashlib
import io
import json
import pathlib
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor


ORIGIN = "https://www.landreg.gov.hk"
SCRIPT_URL = ORIGIN + "/js/load-agt-primary.js"
PAGE_URL = ORIGIN + "/en/monthly/agt-primary.htm"
PRESS_URL = ORIGIN + "/en/public/press.htm"
INSTRUMENT_URL = ORIGIN + "/json/monthly_stat/monthly/t1.json"
ARCHIVE_RECHECK_DAYS = 30
MAX_ARCHIVE_WORKERS = 8
INSTRUMENT_METRIC_IDS = (
    "hk_all_property_building_mortgage_deeds_count", "hk_all_property_other_mortgage_deeds_count",
    "hk_all_property_mortgage_deeds_count", "hk_all_property_discharge_deeds_count",
    "hk_all_building_sales_count",
)
MONTHS = {name: number for number, name in enumerate(calendar.month_name) if name}
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
                "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
    except urllib.error.HTTPError as error:
        if error.code == 304 and cached:
            payload = dict(cached, checked_at=dt.datetime.now(dt.timezone.utc).isoformat())
        else:
            raise RuntimeError(f"Land Registry request failed: {url}: {error}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"Land Registry request failed: {url}: {error}") from error
    if cache_file:
        temporary = cache_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(cache_file)
    return payload


def _get_archive(url, cache_dir, *, recheck=False):
    """Recheck old archives monthly; current/recent observations always revalidate.

    A failed revalidation raises: expired cached data are never silently returned.
    checked_at remains the original source check when an unexpired cache is used.
    """
    if cache_dir is not None and not recheck:
        path = pathlib.Path(cache_dir) / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            checked = dt.datetime.fromisoformat(cached["checked_at"])
            age = dt.datetime.now(dt.timezone.utc) - checked
            if (cached.get("url") == url and isinstance(cached.get("body"), str)
                    and dt.timedelta(0) <= age < dt.timedelta(days=ARCHIVE_RECHECK_DAYS)):
                return cached
        except (OSError, ValueError, KeyError, TypeError):
            pass
    return _get(url, cache_dir)


def _parse_instruments(payload, expected_period=None):
    """Validate district sums and any published totals; count deeds, not homes."""
    rows = json.loads(payload["body"])
    if not isinstance(rows, list) or not rows:
        raise ValueError("Empty or invalid Land Registry instrument table")
    periods, by_description = set(), {}
    for row in rows:
        # Historical XLS-to-JSON exports sometimes retain a fully blank last
        # spreadsheet row (for example {'Year': ''}); never discard a value.
        if isinstance(row, dict) and all(value is None or str(value).strip() == "" for value in row.values()):
            continue
        if not isinstance(row, dict) or not {"Year", "Month", "Description", "Units"} <= row.keys():
            raise ValueError("Land Registry instrument schema changed")
        year, month = int(row["Year"]), int(row["Month"])
        date = dt.date(year, month, calendar.monthrange(year, month)[1])
        periods.add(date)
        description = str(row["Description"]).strip()
        if description in by_description:
            raise ValueError(f"Duplicate Land Registry instrument category: {description}")
        by_description[description] = row["Units"]
    if len(periods) != 1:
        raise ValueError("Mixed months in Land Registry instrument table")
    date = periods.pop()
    period = date.strftime("%Y-%m")
    if expected_period is not None and period != expected_period:
        raise ValueError(f"Land Registry instrument period mismatch: {period} != {expected_period}")

    def count(key):
        if key not in by_description:
            raise ValueError(f"Missing Land Registry instrument category: {key}")
        value = by_description[key]
        raw = str(value).strip().replace(",", "")
        if isinstance(value, bool) or not re.fullmatch(r"\d+", raw):
            raise ValueError(f"Invalid Land Registry instrument count: {key}: {value}")
        return int(raw)

    categories = (
        ("hk_all_property_building_mortgage_deeds_count", "Building Mortgages/Building Legal Charges", "建筑按揭／建筑法定押记文书登记宗数"),
        ("hk_all_property_other_mortgage_deeds_count", "Other Mortgages/Legal Charges", "其他按揭／法定押记文书登记宗数"),
        ("hk_all_property_discharge_deeds_count", "Receipts/Discharges/Releases", "收据／解除按揭／解除押记文书登记宗数"),
    )
    values, parts, fields, names = {}, {}, {}, {}
    for metric, category, name in categories:
        keys = [f"Number of {district} deeds received for registration for {category}"
                for district in ("Urban", "New Territories")]
        parts[metric] = [count(key) for key in keys]
        values[metric] = sum(parts[metric])
        total_key = f"Total Number of Urban & New Territories deeds received for registration for {category}"
        if total_key in by_description and count(total_key) != values[metric]:
            raise ValueError(f"Land Registry instrument total disagrees with districts: {category}")
        fields[metric] = total_key if total_key in by_description else " + ".join(keys)
        names[metric] = name
    total_metric = "hk_all_property_mortgage_deeds_count"
    building, other = [category[0] for category in categories[:2]]
    values[total_metric] = values[building] + values[other]
    for district, total in (("Urban", parts[building][0] + parts[other][0]),
                            ("New Territories", parts[building][1] + parts[other][1]),
                            ("Urban & New Territories", values[total_metric])):
        key = f"Sub-total (5)+(6) of {district}"
        if key in by_description and count(key) != total:
            raise ValueError(f"Land Registry mortgage subtotal disagrees: {district}")
    fields[total_metric] = "Building Mortgages/Building Legal Charges + Other Mortgages/Legal Charges; Urban + New Territories"
    names[total_metric] = "全物业按揭／法定押记文书登记宗数"
    result = []
    for metric in (building, other, total_metric, categories[2][0]):
        result.append({
            "market": "HK", "category": "registration", "metric_id": metric,
            "metric_name": names[metric], "period": period, "date": date.isoformat(),
            "value": values[metric], "unit": "deeds", "frequency": "monthly",
            "property_type": "All property types",
            "scope": "香港全境所有物业（土地、住宅及非住宅）；送交登记的文书",
            "seasonal_adjustment": "NSA", "source_name": "香港土地注册处",
            "source_url": payload["url"], "source_documentation": ORIGIN + "/en/monthly/monthly.htm",
            "source_table": "Consolidated Monthly Statistics, Table 1",
            "source_field": fields[metric], "published_date": None,
            "source_checked_at": payload.get("checked_at"), "fetch_mode": "automatic_json",
            "note": "统计送交登记的文书份数，不是有按揭住宅成交宗数或独立物业数。"
                    "覆盖住宅、非住宅及土地，未区分银行与非银行、购房与再融资，不能减去银行购房按揭以推算非银行按揭。"
                    "解除按揭等文书不是新按揭的相反流量，不能相减推算购房按揭。"
                    "登记月通常滞后文书签立时间；市区及新界分项加总，已核对来源提供的合计。"
                    "官方未公布此表按揭金额；未将不适用值当作零。"
                    "历史档案最多30天重新核查；source_checked_at记录实际来源核查时间，非发布日期。",
        })
    sale_keys = [f"Number of {district} deeds received for registration (ASP Building Units)"
                 for district in ("Urban", "New Territories")]
    sale_count = sum(count(key) for key in sale_keys)
    # Count agreements, never the separate '(Unit Involved)' fields.
    sale_total = "Total Number of Urban & New Territories deeds received for registration (ASP Building Units)"
    if sale_total in by_description and count(sale_total) != sale_count:
        raise ValueError("Land Registry building sale total disagrees with districts")
    result.append(dict(
        market="HK", category="transaction", metric_id="hk_all_building_sales_count",
        metric_name="全部楼宇买卖合约登记宗数", period=period, date=date.isoformat(),
        value=sale_count, unit="deeds", frequency="monthly", property_type="All building units",
        scope="All building-unit sale agreements, residential and non-residential; excludes land agreements",
        source_name="香港土地注册处", source_url=payload["url"], source_documentation=ORIGIN+"/en/monthly/monthly.htm",
        source_table="Consolidated Monthly Statistics, Table 1, item 1",
        source_field=" + ".join(sale_keys), published_date=None,
        source_checked_at=payload.get("checked_at"), fetch_mode="automatic_json",
        note="全部楼宇买卖合约登记文书份数；包含住宅及非住宅，不含土地买卖合约。"
             "不是涉及单位数；市区及新界文书份数相加。登记月不一定是成交月。",
    ))
    return result


class InstrumentCollectionError(RuntimeError):
    """Carry failed month/metric scope even when no instrument rows survive."""
    def __init__(self, message, failed_periods):
        super().__init__(message)
        self.failed_periods = sorted(failed_periods)


def _collect_instruments(cache_dir, cutoff, start=dt.date(1993, 4, 30), latest_sales_period=None):
    """Backfill with eight concurrent requests, then reuse revalidated archives."""
    warnings, current, conflicting_latest, failed_periods = [], [], False, set()
    announced = None
    try:
        release = _latest_release(_get(PRESS_URL, cache_dir)["body"], cutoff)
        if release:
            year, month = map(int, release["period"].split("-"))
            announced = dt.date(year, month, calendar.monthrange(year, month)[1])
    except Exception as error:
        warnings.append(f"latest instrument release catalog: {error}")
    try:
        candidate = _parse_instruments(_get(INSTRUMENT_URL, cache_dir))
        if dt.date.fromisoformat(candidate[0]["date"]) > cutoff:
            raise ValueError(f"Future instrument observation {candidate[0]['period']} exceeds cutoff {cutoff}")
        current = candidate
    except Exception as error:
        warnings.append(f"latest instrument table: {error}")
    known = [announced] if announced else []
    if latest_sales_period:
        year, month = map(int, latest_sales_period.split("-"))
        sale_date = dt.date(year, month, calendar.monthrange(year, month)[1])
        if sale_date <= cutoff:
            known.append(sale_date)
    if current:
        known.append(dt.date.fromisoformat(current[0]["date"]))
    end = max(known) if known else cutoff.replace(day=1) - dt.timedelta(days=1)
    # A lagging moving endpoint must not cap historical retrieval below a newer
    # officially announced month. Compare only observations of the same month.
    if current and current[0]["date"] != end.isoformat():
        current = []
    if end < start:
        return []
    # The fixed latest archive can publish earlier than the datagov monthly file.
    latest_url = ORIGIN + f"/json/monthly_stat/stat{end:%m%y}/t1.json"
    try:
        fixed = _parse_instruments(_get(latest_url, cache_dir), end.strftime("%Y-%m"))
        if current and [r["value"] for r in fixed] != [r["value"] for r in current]:
            current = []
            conflicting_latest = True
            failed_periods.add(end.strftime("%Y-%m"))
            raise ValueError("latest and fixed instrument tables disagree; latest month omitted")
        current = fixed
    except Exception as error:
        warnings.append(f"{end:%Y-%m} fixed instrument archive: {error}")
    length = (end.year - start.year) * 12 + end.month - start.month + 1
    dates = _months_ending(end, length)
    if current or conflicting_latest:
        dates = dates[:-1]

    def fetch(date):
        url = ORIGIN + f"/datagovhk/{date:%Y%m}_data.json"
        recent = (end.year - date.year) * 12 + end.month - date.month < 3
        try:
            data = _get_archive(url, cache_dir, recheck=recent)
            return date, _parse_instruments(data, date.strftime("%Y-%m")), None
        except Exception as error:
            return date, [], str(error)

    records = []
    with ThreadPoolExecutor(max_workers=MAX_ARCHIVE_WORKERS) as pool:
        for date, rows, error in pool.map(fetch, dates):
            records.extend(rows)
            if error:
                warnings.append(f"{date:%Y-%m}: {error}")
                failed_periods.add(date.strftime("%Y-%m"))
    records.extend(current)
    if not records:
        raise InstrumentCollectionError("No valid Land Registry instrument observations: " + "; ".join(warnings[:3]), failed_periods)
    if warnings:
        warning = f"Land Registry instrument coverage incomplete ({len(warnings)} source checks failed): " + "; ".join(warnings[:8])
        if len(warnings) > 8:
            warning += f"; {len(warnings) - 8} additional failures"
        records = [dict(row, refresh_warning=warning) for row in records]
    if failed_periods:
        records = [dict(row, refresh_failed_periods=sorted(failed_periods),
                        refresh_failed_metric_ids=list(INSTRUMENT_METRIC_IDS)) for row in records]
    return records


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


def _get_pdf(url, cache_dir):
    """Revalidate binary annexes; cache only successful official responses."""
    pdf_path = metadata_path = None
    cached = None
    headers = {"User-Agent": USER_AGENT}
    if cache_dir is not None:
        folder = pathlib.Path(cache_dir)
        folder.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(url.encode()).hexdigest()
        pdf_path, metadata_path = folder / (key + ".pdf"), folder / (key + ".headers.json")
        if pdf_path.exists() and metadata_path.exists():
            try:
                candidate = json.loads(metadata_path.read_text())
                if candidate.get("url") == url and candidate.get("sha256") == hashlib.sha256(pdf_path.read_bytes()).hexdigest():
                    cached = candidate
                    for field, header in (("etag", "If-None-Match"), ("last_modified", "If-Modified-Since")):
                        if cached.get(field):
                            headers[header] = cached[field]
            except (OSError, ValueError):
                pass
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            body = response.read(20_000_001)
            payload = {"url": url, "etag": response.headers.get("ETag"),
                       "last_modified": response.headers.get("Last-Modified")}
    except urllib.error.HTTPError as error:
        if error.code == 304 and cached:
            return dict(cached, body=pdf_path.read_bytes())
        raise RuntimeError(f"Land Registry annex request failed: {url}: {error}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"Land Registry annex request failed: {url}: {error}") from error
    if not body.startswith(b"%PDF") or len(body) > 20_000_000:
        raise ValueError("Invalid Land Registry annex PDF")
    payload["sha256"] = hashlib.sha256(body).hexdigest()
    if pdf_path:
        temporary = pdf_path.with_suffix(".tmp")
        temporary.write_bytes(body)
        temporary.replace(pdf_path)
        metadata_path.write_text(json.dumps(payload), encoding="utf-8")
    return dict(payload, body=body)


def _latest_release(body, cutoff):
    marker = re.search(r"\bpressReleaseJson\s*=\s*", body)
    if not marker:
        raise ValueError("Land Registry release catalog changed")
    catalog, _ = json.JSONDecoder().raw_decode(body[marker.end():])
    candidates = []
    recognized = 0
    for year in catalog:
        for item in year["items"]:
            title = re.fullmatch(r"Land Registry releases statistics for ([A-Za-z]+)(?: (\d{4}))?", item["title"])
            if not title or title[1] not in MONTHS:
                continue
            recognized += 1
            published = dt.datetime.strptime(item["date"], "%Y/%m/%d").date()
            month = MONTHS[title[1]]
            year_number = int(title[2]) if title[2] else published.year - (month > published.month)
            end = dt.date(year_number, month, calendar.monthrange(year_number, month)[1])
            if published > cutoff or end > cutoff:
                continue
            candidates.append({"period": end.strftime("%Y-%m"), "published_date": published.isoformat(), "url": item["url"]})
    if not recognized:
        raise ValueError("No monthly Land Registry releases in catalog")
    if not candidates:
        return None
    latest = max(candidates, key=lambda row: (row["period"], row["published_date"]))
    published = dt.date.fromisoformat(latest["published_date"])
    parsed = urlparse(latest["url"])
    prefix = f"/gia/general/{published:%Y%m}/{published:%d}/"
    if parsed.scheme != "https" or parsed.netloc != "www.info.gov.hk" or not parsed.path.startswith(prefix):
        raise ValueError("Unexpected Land Registry monthly release URL")
    return latest


def _annex_table_text(body):
    import pdfplumber
    matches = []
    with pdfplumber.open(io.BytesIO(body)) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            if re.search(r"(?m)^Table 5\s*$", text) and "Total Consideration" in text:
                matches.append((text, page_number))
    if len(matches) != 1:
        raise ValueError("Cannot identify unique Land Registry residential Table 5")
    return matches[0]


def _parse_release_table(text, expected_period):
    """Parse exact residential totals; reject changed labels, units or columns."""
    normalized = re.sub(r"\s+", " ", text)
    title = "Number of Sale and Purchase Agreements of residential building units and total consideration"
    if title not in normalized or not re.search(r"(?m)^Table 5\s*$", text):
        raise ValueError("Unexpected Land Registry residential table title")
    span = re.findall(r"from ([A-Za-z]+) (\d{4}) to ([A-Za-z]+) (\d{4})", normalized)
    if len(span) != 1 or span[0][0] not in MONTHS or span[0][2] not in MONTHS:
        raise ValueError("Missing Land Registry table period")
    first_month, first_year, last_month, last_year = span[0]
    end_month = MONTHS[last_month]
    end = dt.date(int(last_year), end_month, calendar.monthrange(int(last_year), end_month)[1])
    months = _months_ending(end, 13)
    if end.strftime("%Y-%m") != expected_period or (months[0].year, months[0].month) != (int(first_year), MONTHS[first_month]):
        raise ValueError("Land Registry table does not cover the announced 13 months")
    def unique_line(label):
        lines = re.findall(r"(?m)^" + re.escape(label) + r"[ \t]+([^\n]+)$", text)
        if len(lines) != 1:
            raise ValueError(f"Missing or duplicate Land Registry row: {label}")
        return lines[0].split()
    if unique_line("Month") != [str(date.month) for date in months]:
        raise ValueError("Land Registry month columns changed")
    if unique_line("Year") != list(dict.fromkeys(str(date.year) for date in months)):
        raise ValueError("Land Registry year columns changed")
    values = []
    for label in ("Total No.", "Total Consideration ($ million)"):
        tokens = unique_line(label)
        if len(tokens) != 13 or any(not re.fullmatch(r"(?:\d{1,3}(?:,\d{3})+|\d+)", token) for token in tokens):
            raise ValueError(f"Invalid Land Registry 13-month totals: {label}")
        values.append([int(token.replace(",", "")) for token in tokens])
    return {date.strftime("%Y-%m"): (values[0][i], values[1][i]) for i, date in enumerate(months)}


def _release_supplement(records, cache_dir, cutoff):
    release = _latest_release(_get(PRESS_URL, cache_dir)["body"], cutoff)
    metrics = ("hk_residential_sales_count", "hk_residential_sales_value")
    existing = {(row["metric_id"], row["period"]): row for row in records}
    latest = {metric: max(row["period"] for row in records if row["metric_id"] == metric) for metric in metrics}
    if release is None or all(release["period"] <= period for period in latest.values()):
        return records
    html = _get(release["url"], cache_dir)["body"]
    # Follow only an actual PDF link in the official release, never a guessed filename.
    links = set(re.findall(r'href=["\'](https://gia\.info\.gov\.hk/[^"\']+\.pdf)["\']', html, re.I))
    publication = dt.date.fromisoformat(release["published_date"])
    release_id = pathlib.PurePosixPath(urlparse(release["url"]).path).stem
    prefix = f"/general/{publication:%Y%m}/{publication:%d}/{release_id}_"
    links = [url for url in links if urlparse(url).path.startswith(prefix)]
    if len(links) != 1:
        raise ValueError(f"Latest announced Land Registry {release['period']} annex link is missing or ambiguous")
    annex_url = links[0]
    text, page_number = _annex_table_text(_get_pdf(annex_url, cache_dir)["body"])
    totals = _parse_release_table(text, release["period"])
    overlap = sorted(period for period in totals if all((metric, period) in existing for metric in metrics))[-6:]
    if len(overlap) < 6 or any(existing[(metric, period)]["value"] != totals[period][i]
                                for period in overlap for i, metric in enumerate(metrics)):
        raise ValueError("Land Registry annex overlap does not match six known monthly totals")
    result = list(records)
    for period, amounts in totals.items():
        for i, metric in enumerate(metrics):
            if period <= latest[metric]:
                continue
            year, month = map(int, period.split("-"))
            end = dt.date(year, month, calendar.monthrange(year, month)[1])
            if end > cutoff:
                continue
            template = existing[(metric, latest[metric])]
            result.append(dict(template, period=period, date=end.isoformat(), value=amounts[i],
                source_url=annex_url, source_documentation=release["url"],
                source_table="5", source_field=f"Table 5, page {page_number}",
                published_date=release["published_date"], fetch_mode="automatic_pdf",
                freshness_basis="Official monthly press-release annex; exact residential totals",
                note="Official Land Registry monthly annex: residential registration totals, not all-building totals. "
                     "Consideration is published in HKD million, not the rounded headline billions. "
                     "This annex does not publish the primary/secondary breakdown; missing components are not estimated. "
                     "Registration month may follow the transaction month. Restricted subsidised units are excluded under official definitions."))
    return result


def _validate_sales_month(series, date):
    """Reconcile each published measure independently, including partial tables."""
    for suffix, tolerance in (("count", 0), ("value", 1)):
        total = series["hk_residential_sales_" + suffix].get(date, (None,))[0]
        parts = [series["hk_residential_" + market + "_sales_" + suffix].get(date, (None,))[0]
                 for market in ("primary", "secondary")]
        present = [value for value in parts if value is not None]
        if total is not None and (sum(present) > total + tolerance or
                                  (len(present) == 2 and abs(total - sum(present)) > tolerance)):
            raise ValueError(f"Residential {suffix} components disagree with total: {date}")


def _collect_sales(cache_dir=None, as_of=None):
    """Return full discovered history plus newer official residential totals.

    as_of limits observation months, not the historical vintage of revisions.
    cache_dir can be None to disable disk caching. Network errors and incomplete
    monthly coverage are reported instead of silently returning stale data.
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
    # Current blocks can include history beyond the page title. Read every
    # official block, keeping the current/recent version of overlapping rows.
    ordered = [entry for entry in blocks if entry[0] == "agt-primary"]
    ordered += sorted((entry for entry in blocks if entry[0] != "agt-primary" and entry[1] <= cutoff.year), key=lambda entry: entry[2], reverse=True)
    monthly = {metric_id: {} for metric_id, *_ in SERIES}
    warnings, selected_dates = [], set()
    for block, _, _ in ordered:
        urls = [f"{base}/{block}/t1.json", f"{base}/{block}/t2.json"]
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                count_payload, amount_payload = list(pool.map(lambda url: _get(url, cache_dir), urls))
        except Exception as error:
            warnings.append(f"{block}: {error}")
            continue
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
        # Select an entire observation month from one revision block. Explicit
        # missing components in a newer block must overwrite old values with
        # nulls; neither this merge nor the outer pipeline may resurrect them.
        block_dates = set.union(*(set(series) for series in block_series.values()))
        for date in block_dates - selected_dates:
            selected_dates.add(date)
            missing = []
            for metric_id, _, _, _, _, table in SERIES:
                payload = count_payload if table == "t1" else amount_payload
                record = block_series[metric_id].get(date)
                if record is None:
                    record = (None, payload["url"], payload.get("last_modified"))
                    missing.append(metric_id)
                monthly[metric_id][date] = record
            if missing and date <= cutoff:
                warnings.append(f"Residential breakdown incomplete in current revision {block} {date:%Y-%m}: " + ", ".join(missing))
    selected = sorted(date for date in set.intersection(*(set(series) for series in monthly.values())) if date <= cutoff)
    if not selected:
        raise ValueError(f"Could not obtain residential history as of {cutoff}: {'; '.join(warnings)}")
    records = []
    for date in selected:
        _validate_sales_month(monthly, date)
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
            if value is None:
                records[-1].update(status="unavailable", missing_reason="Official value missing in the selected monthly revision; older revision is not substituted")
    try:
        records = _release_supplement(records, cache_dir, cutoff)
    except Exception as error:
        warnings.append(f"Land Registry latest monthly release could not be verified: {error}")
    if warnings:
        records = [dict(row, refresh_warning="; ".join(warnings)) for row in records]
    return records


def collect(cache_dir=None, as_of=None):
    """Return residential sales and separately defined all-property deeds.

    A failed instrument source never blocks valid sales or manufactures a count.
    All observations retain their actual period; any partial failure is visible.
    """
    cutoff = _as_date(as_of)
    records = _collect_sales(cache_dir, cutoff)
    try:
        latest_sales = max((row["period"] for row in records if row.get("value") is not None), default=None)
        return records + _collect_instruments(cache_dir, cutoff, latest_sales_period=latest_sales)
    except Exception as error:
        warning = f"Land Registry instrument history could not be verified: {error}"
        rows = [dict(row, refresh_warning="; ".join(filter(None, (row.get("refresh_warning"), warning)))) for row in records]
        if isinstance(error, InstrumentCollectionError):
            rows = [dict(row, refresh_failed_periods=error.failed_periods,
                         refresh_failed_metric_ids=list(INSTRUMENT_METRIC_IDS)) for row in rows]
        return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default=None, help="Observation cutoff YYYY-MM-DD")
    parser.add_argument("--cache-dir", default=None, help="Optional raw response cache folder")
    arguments = parser.parse_args()
    print(json.dumps(collect(arguments.cache_dir, arguments.as_of), ensure_ascii=False, indent=2))
