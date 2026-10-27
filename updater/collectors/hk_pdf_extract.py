#!/usr/bin/env python3
"""Extract 10 housing tables from an RVD Property Review Monthly Supplement.

Requires Python 3.10+, pdfplumber and pypdf. The source PDF is read only.

Usage:
    python hk_pdf_extract.py --source supplement.pdf --output source-tables/edition
    python hk_pdf_extract.py --source supplement.pdf --output extracted --rvd-dir csvs

The edition is read from the cover. Table numbers AND English titles must match
exactly one page; missing/ambiguous tables or unparsed data rows produce exit 1
and a failed manifest. This parser targets the current RVD table layout, not
arbitrary PDFs. Raw cells, page text, layout text and coordinates remain available
for review. A newer official CSV may legitimately revise an older PDF snapshot;
optional CSV differences are reported, never silently substituted.
"""

import argparse
import calendar
import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

import pdfplumber
from pypdf import PdfReader


CLASSES = ["A", "B", "C", "D", "E"]
INDEX_COLUMNS = CLASSES + ["A, B & C", "D & E", "All Classes"]
REGIONS = ["Hong Kong", "Kowloon", "New Territories"]
# x positions are template hints scaled to page width; page numbers are discovered.
TABLES = [
    ("1.1", 160, [f"Class {c} | {r}" for c in CLASSES for r in REGIONS], "HKD/sqm/month", "PRIVATE DOMESTIC - AVERAGE RENTS BY CLASS"),
    ("1.2", 144, [f"Class {c} | {r}" for c in CLASSES for r in REGIONS], "HKD/sqm", "PRIVATE DOMESTIC - AVERAGE PRICES BY CLASS"),
    ("1.3", 165, [f"Class {c}" if c in CLASSES else (f"Classes {c}" if c != "All Classes" else c) for c in INDEX_COLUMNS], "index", "PRIVATE DOMESTIC - RENTAL INDICES BY CLASS"),
    ("1.4", 160, [f"Class {c}" if c in CLASSES else (f"Classes {c}" if c != "All Classes" else c) for c in INDEX_COLUMNS], "index", "PRIVATE DOMESTIC - PRICE INDICES BY CLASS"),
    ("1.5", 170, [f"{c} | {r}" for c in ["A, B & C", "D & E", "Overall"] for r in ["Urban", "N.T.", "All"]], "index", "PRIVATE DOMESTIC - PRICE INDICES FOR SELECTED POPULAR DEVELOPMENTS"),
    ("5.1", 180, [f"Domestic Class {c}" for c in CLASSES], "% return", "PROPERTY MARKET YIELDS - PRIVATE DOMESTIC"),
    ("6.1", 180, ["Completions Hong Kong", "Completions Kowloon", "Completions New Territories", "Completions Overall", "Completions / forecast %", "Forecast completions Overall"], "units; %", "COMPLETIONS AND FORECAST COMPLETIONS - PRIVATE DOMESTIC"),
    ("7.1", 200, ["Number of agreements", "Consideration (HKD million)"], "agreements; HKD million", "DOMESTIC SALES - NUMBER OF SALE AND PURCHASE AGREEMENTS AND TOTAL CONSIDERATION"),
    ("7.2", 175, [f"{r} | {m}" for r in ["<2m", "2m-<3m", "3m-<5m", "5m-<10m", ">=10m"] for m in ["Number", "%"]] + ["Total agreements"], "agreements; %", "DOMESTIC SALES - NUMBER OF SALE AND PURCHASE AGREEMENTS BY CONSIDERATION RANGE"),
    ("7.3", 170, ["Primary number", "Primary %", "Primary consideration (HKD million)", "Secondary number", "Secondary %", "Secondary consideration (HKD million)", "Total agreements"], "agreements; %; HKD million", "DOMESTIC PRIMARY AND SECONDARY SALES - NUMBER OF SALE AND PURCHASE AGREEMENTS AND TOTAL CONSIDERATION"),
]


class ExtractionError(Exception):
    """A source does not satisfy the supported table contract."""


def compact(text):
    return re.sub(r"[^A-Z0-9]", "", unicodedata.normalize("NFKC", text).upper())


def cover_edition(text):
    months = {name.lower(): n for n, name in enumerate(calendar.month_name) if name}
    pattern = r"\b(" + "|".join(months) + r")\s+(\d{4})\b"
    matches = {(int(y), months[m.lower()]) for m, y in re.findall(pattern, text, re.I)}
    if len(matches) != 1:
        raise ExtractionError(f"Cover must contain one unambiguous English month/year; found {sorted(matches)}")
    year, month = matches.pop()
    return f"{year}-{month:02d}", f"{calendar.month_name[month]} {year}"


def locate_tables(texts):
    pages = {}
    for table_id, _, _, _, title in TABLES:
        candidates = [n + 1 for n, text in enumerate(texts)
                      if re.search(r"(?m)^\s*" + re.escape(table_id) + r"\s*$", text[:200])
                      and compact(title) in compact(text[:1600])]
        if len(candidates) != 1:
            raise ExtractionError(f"Table {table_id}: expected one page matching table number and title '{title}', found {candidates}")
        pages[table_id] = candidates[0]
    return pages


def row_groups(page):
    groups = []
    for word in sorted(page.extract_words(x_tolerance=3, y_tolerance=2), key=lambda w: (w["top"], w["x0"])):
        if groups and abs(groups[-1][0] - word["top"]) < 1:
            groups[-1][1].append(word)
        else:
            groups.append([word["top"], [word]])
    return [(y, sorted(words, key=lambda w: w["x0"])) for y, words in groups]


def clusters(words):
    result = []
    for word in words:
        if result and word["x0"] - result[-1][-1]["x1"] < 9:
            result[-1].append(word)
        else:
            result.append([word])
    return result


def numeric(raw):
    text = re.sub(r"[\s()*]", "", raw)
    if text == "-":
        return None
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        raise ValueError(f"unparsed numeric cell: {raw!r}")
    return float(text) if "." in text else int(text)


def period_info(raw, year, force_ytd=False):
    provisional = "*" in raw
    text = raw.replace("*", "").strip()
    match = re.match(r"^(\d{4})(?:\s+|$)", text)
    if match:
        year = int(match.group(1))
        text = text[match.end():].strip()
    if year is None:
        raise ValueError("period has no preceding year")
    if not text:
        return str(year), "annual", year, provisional
    numbers = list(map(int, re.findall(r"\d+", text)))
    if len(numbers) == 1 and 1 <= numbers[0] <= 12:
        return f"{year}-{numbers[0]:02d}", "monthly", year, provisional
    if len(numbers) == 2 and 1 <= numbers[0] <= numbers[1] <= 12:
        first, last = numbers
        if not force_ytd and last - first == 2 and first in (1, 4, 7, 10):
            return f"{year}-Q{(first - 1) // 3 + 1}", "quarterly", year, provisional
        return f"{year}-{first:02d}/{year}-{last:02d}", "year_to_date", year, provisional
    raise ValueError(f"unparsed period: {raw!r}")


def supply_context(text):
    normalized = " ".join(text.split())
    match = re.search(r"(\d{4})\s+Completions\s*\(\s*up\s+to\s+(\d{1,2})\.(\d{1,2})\.(\d{4})\s*\)", normalized, re.I)
    forecast = re.search(r"Forecast completions for the whole year of (\d{4})", normalized, re.I)
    if not match or not forecast:
        raise ExtractionError("Table 6.1: cannot parse cumulative cut-off date and forecast year")
    year, day, month, end_year = map(int, match.groups())
    cutoff = date(end_year, month, day)
    if year != end_year:
        raise ExtractionError("Table 6.1: cumulative year disagrees with cut-off year")
    if "completion figures are provisional" not in normalized.lower():
        raise ExtractionError("Table 6.1: provisional status needs review; expected source note missing")
    return {"cutoff_date": cutoff.isoformat(), "period": f"{year}-01/{year}-{month:02d}", "forecast_year": int(forecast.group(1))}


def extract_table(page, plain, table, page_num, out, context):
    table_id, min_x, columns, unit, title = table
    min_x *= page.width / 841.68
    groups = row_groups(page)
    header_word = "Class" if table_id == "6.1" else "Month"
    anchors = [w["bottom"] for _, words in groups for w in words
               if w["text"] == header_word and w["x0"] < min_x]
    if not anchors:
        raise ExtractionError(f"Table {table_id}: missing {header_word} header")
    body_start = max(anchors)
    body_end = page.height * 0.94
    if table_id == "6.1":
        footnotes = [y for y, words in groups if "The completion figures" in " ".join(w["text"] for w in words)]
        if not footnotes:
            raise ExtractionError("Table 6.1: cannot locate end of data before explanatory notes")
        body_end = min(footnotes)
        labels = [(w["text"], w["top"]) for _, words in groups for w in words
                  if w["x0"] < min_x and body_start < w["top"] < body_end
                  and w["text"] in CLASSES + ["Overall"]]
        if [label for label, _ in labels] != CLASSES + ["Overall"]:
            raise ExtractionError(f"Table 6.1: expected A-E and Overall row labels, found {labels}")
    if unit == "index":
        bases = set(re.findall(r"\(\s*(\d{4})\s*=\s*100\s*\)", plain))
        if len(bases) != 1:
            raise ExtractionError(f"Table {table_id}: index base cannot be identified")
        unit = f"{bases.pop()}=100"
    candidates = []
    for y, words in groups:
        if not body_start < y < body_end:
            continue
        left = " ".join(w["text"] for w in words if w["x0"] < min_x)
        right = [w for w in words if w["x0"] >= min_x]
        valid = table_id == "6.1" or bool(re.fullmatch(r"[\d\s*\-]+", left))
        if valid and right:
            candidates.append((y, left, right))
    template = None
    for _, _, right in candidates:
        grouped = clusters(right)
        if len(grouped) == len(columns):
            try:
                [numeric(" ".join(w["text"] for w in cell)) for cell in grouped]
                template = grouped
                break
            except ValueError:
                continue
    if template is None:
        raise ExtractionError(f"Table {table_id}: cannot infer {len(columns)} numeric columns")
    centers = [(cell[0]["x0"] + cell[-1]["x1"]) / 2 for cell in template]
    bounds = [min_x] + [(a + b) / 2 for a, b in zip(centers, centers[1:])] + [page.width]
    rows, rejected = [], []
    year = None
    for y, left, right in candidates:
        cells = [" ".join(w["text"] for w in right if bounds[i] <= (w["x0"] + w["x1"]) / 2 < bounds[i + 1]) for i in range(len(columns))]
        try:
            values = [numeric(cell) for cell in cells]
            if table_id == "6.1":
                if len(rows) >= 6:
                    raise ValueError("more than six supply rows")
                label, label_y = labels[len(rows)]
                if abs(label_y - y) > 20:
                    raise ValueError(f"numeric row is not aligned with class {label}")
                period, frequency, provisional = context["period"], "year_to_date", True
            else:
                first_sales_range = table_id.startswith("7.") and rows and all(r["frequency"] == "annual" for r in rows)
                force_ytd = first_sales_range and bool(re.match(r"\d{4}\s+1\s*-", left))
                period, frequency, year, provisional = period_info(left, year, force_ytd=force_ytd)
                label = period
            rows.append({"period": period, "frequency": frequency, "label": label, "raw_period": left,
                         "provisional": provisional, "y": round(y, 2), "cells": cells, "values": values})
        except ValueError as exc:
            rejected.append({"y": round(y, 2), "raw_period": left, "raw_cells": cells, "error": str(exc)})
    keys = [(r["period"], r["frequency"], r["label"]) for r in rows]
    if not rows or len(keys) != len(set(keys)) or (table_id == "6.1" and len(rows) != 6):
        raise ExtractionError(f"Table {table_id}: missing rows or duplicate period keys")
    if table_id != "6.1" and not any(r["frequency"] == "monthly" for r in rows):
        raise ExtractionError(f"Table {table_id}: no monthly observations")
    stem = "table_" + table_id.replace(".", "_")
    with (out / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["period", "frequency", "row_label", "source_period_raw", "provisional", "pdf_page", "y_top"] + columns)
        for row in rows:
            writer.writerow([row["period"], row["frequency"], row["label"], row["raw_period"], row["provisional"], page_num, row["y"]] + row["cells"])
    item = {"table_id": table_id, "page": page_num, "title": title, "unit": unit, "columns": columns,
            "row_count": len(rows), "cell_count": len(rows) * len(columns),
            "monthly_row_count": sum(r["frequency"] == "monthly" for r in rows),
            "latest_month": max((r["period"] for r in rows if r["frequency"] == "monthly"), default=None),
            "csv": f"{stem}.csv", "raw_text": f"{stem}_source_text.txt", "raw_layout": f"{stem}_source_layout.txt",
            "rejected_rows": rejected, "column_bounds_pdf_points": bounds}
    if table_id == "6.1":
        item.update(context)
        item["note"] = "Completions are cumulative and provisional. Forecast is a full-year estimate made at the beginning of the year. Revisions mean cumulative changes need not equal latest-month completions."
    return item, rows


def to_observations(table, item, rows, source, edition, context):
    result = []
    table_id = table[0]
    for row in rows:
        for column, raw, value in zip(item["columns"], row["cells"], row["values"]):
            unit, period, frequency, kind = item["unit"], row["period"], row["frequency"], "observed"
            if table_id == "6.1":
                unit = "%" if column.endswith("%") else "units"
                if column.startswith("Forecast"):
                    period, frequency, kind = str(context["forecast_year"]), "annual", "forecast"
                else:
                    kind = "year_to_date_as_share_of_annual_forecast" if column.endswith("%") else "cumulative_completions"
            elif table_id.startswith("7."):
                unit = "HKD million" if "consideration" in column.lower() else ("%" if column.endswith("%") else "agreements")
            result.append({"table_id": table_id, "pdf_page": item["page"], "period": period, "frequency": frequency,
                           "row_label": row["label"], "column": column, "value": value, "unit": unit, "observation_kind": kind,
                           "raw_cell": raw, "provisional": row["provisional"], "fewer_than_20_transactions": "(" in raw,
                           "missing": value is None, "source_pdf": str(source), "source_edition": edition})
    return result


def compare_csvs(observations, directory):
    aliases = {"1.3": ["1.3M.csv", "hk_rent.csv"], "1.4": ["1.4M.csv", "hk_price.csv"], "5.1": ["5.1M.csv", "hk_review_yields.csv"]}
    comparisons = []
    if directory is None:
        return [{"status": "skipped", "reason": "--rvd-dir was not supplied"}]
    if not directory.is_dir():
        raise ExtractionError(f"RVD directory does not exist: {directory}")
    paths = list(directory.rglob("*.csv"))
    for table_id, names in aliases.items():
        matches = [path for name in names for path in paths if path.name.lower() == name.lower()]
        if not matches:
            comparisons.append({"table_id": table_id, "status": "skipped", "reason": "No recognized CSV filename", "accepted_filenames": names})
            continue
        path = matches[0]
        with path.open(encoding="utf-8-sig", newline="") as handle:
            raw_rows = list(csv.reader(handle))
        header = next((n for n, row in enumerate(raw_rows[:8]) if row and row[0] == "Month"), None)
        if header is None:
            raise ExtractionError(f"CSV {path}: no Month header")
        lookup = {}
        for values in raw_rows[header + 1:]:
            row = dict(zip(raw_rows[header], values))
            match = re.fullmatch(r"(\d{2})-(\d{4})", row.get("Month", ""))
            if match:
                lookup[f"{match[2]}-{match[1]}"] = row
        checked, mismatches = 0, []
        for observation in observations:
            if observation["table_id"] != table_id or observation["frequency"] != "monthly":
                continue
            row, column = lookup.get(observation["period"]), observation["column"]
            if row is not None and column in row:
                checked += 1
                expected = numeric(row[column])
                if observation["value"] != expected:
                    mismatches.append({"period": observation["period"], "column": column, "pdf": observation["value"], "csv": expected})
        comparisons.append({"table_id": table_id, "status": "matched" if checked and not mismatches else "review",
                            "csv_source": str(path), "csv_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "compared_cells": checked, "mismatch_count": len(mismatches), "mismatches": mismatches})
    return comparisons


def reconcile_sales(observations):
    lookup = {(o["table_id"], o["period"], o["column"]): o["value"] for o in observations}
    checks = []
    for observation in observations:
        if observation["table_id"] != "7.1" or observation["column"] != "Number of agreements":
            continue
        period, total = observation["period"], observation["value"]
        total2, total3 = (lookup.get((table, period, "Total agreements")) for table in ("7.2", "7.3"))
        primary, secondary = (lookup.get(("7.3", period, column)) for column in ("Primary number", "Secondary number"))
        bins = [lookup.get(("7.2", period, f"{band} | Number")) for band in ["<2m", "2m-<3m", "3m-<5m", "5m-<10m", ">=10m"]]
        okay = total == total2 == total3 and primary is not None and secondary is not None and primary + secondary == total and all(x is not None for x in bins) and sum(bins) == total
        checks.append({"period": period, "agrees": okay})
    return {"periods_checked": len(checks), "failures": [r for r in checks if not r["agrees"]]}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, type=Path, help="RVD monthly supplement PDF (read only)")
    parser.add_argument("--output", required=True, type=Path, help="Destination for manifest.json, observations and raw tables")
    parser.add_argument("--rvd-dir", type=Path, help="Optional directory of official monthly CSVs; searched recursively")
    args = parser.parse_args(argv)
    source, output = args.source.expanduser().resolve(), args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"status": "running", "source_path": str(source), "source_read_only": True,
                "extracted_at_utc": datetime.now(timezone.utc).isoformat(), "page_numbering": "physical PDF page, 1-based",
                "method": "Match table number and title, then extract numeric columns by PDF word coordinates; preserve raw cells and source text",
                "tables": [], "comparisons": [], "warnings": []}
    write_json(output / "manifest.json", manifest)
    try:
        manifest["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        reader = PdfReader(source)
        texts = [page.extract_text() or "" for page in reader.pages]
        if not texts:
            raise ExtractionError("PDF has no pages")
        edition, edition_label = cover_edition(texts[0])
        manifest.update({"edition": edition, "edition_label": edition_label, "page_count": len(texts),
                         "publication": f"Hong Kong Property Review Monthly Supplement, {edition_label}"})
        (output / "cover_source_text.txt").write_text(texts[0], encoding="utf-8")
        pages = locate_tables(texts)
        manifest["located_pages"] = pages
        context = supply_context(texts[pages["6.1"] - 1])
        observations = []
        with pdfplumber.open(source) as pdf:
            for table in TABLES:
                table_id, page_num = table[0], pages[table[0]]
                stem = "table_" + table_id.replace(".", "_")
                (output / f"{stem}_source_text.txt").write_text(texts[page_num - 1], encoding="utf-8")
                (output / f"{stem}_source_layout.txt").write_text(reader.pages[page_num - 1].extract_text(extraction_mode="layout"), encoding="utf-8")
                item, rows = extract_table(pdf.pages[page_num - 1], texts[page_num - 1], table, page_num, output, context)
                manifest["tables"].append(item)
                observations.extend(to_observations(table, item, rows, source, edition, context))
        manifest["parsed_observation_count"] = len(observations)
        manifest["unparsed_row_count"] = sum(len(t["rejected_rows"]) for t in manifest["tables"])
        if manifest["unparsed_row_count"]:
            raise ExtractionError("Some data rows were not parsed; inspect tables[].rejected_rows")
        manifest["comparisons"] = compare_csvs(observations, args.rvd_dir.expanduser().resolve() if args.rvd_dir else None)
        manifest["sales_reconciliation"] = reconcile_sales(observations)
        if manifest["sales_reconciliation"]["failures"]:
            raise ExtractionError("Sales agreement counts do not reconcile across tables 7.1-7.3")
        latest = max(o["period"] for o in observations if o["frequency"] == "monthly")
        if latest > edition or context["cutoff_date"][:7] > edition:
            raise ExtractionError("Observation date lies after the cover edition; inspect date parsing")
        manifest["latest_month"] = latest
        manifest["important_notes"] = [
            "The PDF is a dated snapshot. A later CSV may contain revisions; comparisons never replace PDF values.",
            "Rows mix annual, quarterly, year-to-date and monthly periods. Forecast completions have annual frequency and observation_kind=forecast.",
            "Parentheses identify fewer than 20 transactions, not negative values. Asterisks identify provisional figures. A dash is missing, never zero.",
            "Completions exclude village houses and include Starter Homes subsidised sale flats; revisions mean cumulative changes need not equal latest-month completions.",
            "Sales agreements are received for registration by the Land Registry and generally relate to transactions executed up to four weeks before submission.",
        ]
        write_json(output / "observations.json", observations)
        with (output / "observations.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(observations[0]))
            writer.writeheader()
            writer.writerows(observations)
        # Keep technical notes using their section heading, without assuming page numbers.
        note_start = next((i for i, text in enumerate(texts) if i > max(pages.values()) - 1 and "TECHNICALNOTES" in compact(text[:1000])), None)
        manifest["technical_note_pages"] = []
        if note_start is not None:
            for i in range(note_start, len(texts)):
                (output / f"technical_notes_page_{i + 1}.txt").write_text(texts[i], encoding="utf-8")
                manifest["technical_note_pages"].append(i + 1)
        else:
            manifest["warnings"].append("Technical notes heading not found; table footnotes remain in source text files")
        if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["sha256"]:
            raise ExtractionError("Source PDF changed during extraction")
        manifest["status"] = "complete"
        write_json(output / "manifest.json", manifest)
        print(json.dumps({"status": "complete", "edition": edition, "tables": len(manifest["tables"]),
                          "observations": len(observations), "latest_month": latest, "manifest": str(output / "manifest.json")}, ensure_ascii=False))
        return 0
    except Exception as exc:
        manifest.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
        write_json(output / "manifest.json", manifest)
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
