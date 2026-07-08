#!/usr/bin/env python3
"""Convert raw apartment and ZIP data into CSVs for the project schema."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


ZIP_RE = re.compile(r",\s*(\d{3,5})(?:-\d{4})?\s*,\s*([A-Za-z]{2})")
SYNTHETIC_STREET_NAMES = (
    "Maple Avenue",
    "Oak Street",
    "Lakeview Drive",
    "Pine Street",
    "Cedar Lane",
    "Washington Avenue",
    "Park Road",
    "Sunset Boulevard",
    "Riverside Drive",
    "Highland Avenue",
    "Meadow Lane",
    "Hillcrest Road",
    "Lincoln Street",
    "Willow Avenue",
    "Cherry Lane",
    "Forest Drive",
    "Adams Street",
    "Valley Road",
    "Spring Street",
    "Magnolia Avenue",
)
STREET_RE = re.compile(
    r"^\s*"
    r"([0-9]+[A-Za-z]?(?:[-/][0-9A-Za-z]+)?(?:\s+[0-9]+/[0-9]+)?)"
    r"\s+(.+?)\s*$"
)
APARTMENT_HEADERS = [
    "id",
    "category",
    "title",
    "body",
    "amenities",
    "bathrooms",
    "bedrooms",
    "currency",
    "fee",
    "has_photo",
    "pets_allowed",
    "price",
    "price_display",
    "price_type",
    "square_feet",
    "address",
    "cityname",
    "state",
    "latitude",
    "longitude",
    "source",
    "time",
]


@dataclass(frozen=True)
class AddressRow:
    street_number: str
    street_name: str
    zip_code: str
    city_state_id: int


@dataclass(frozen=True)
class ListingRow:
    listing_id: int
    address_id: int
    title: str
    description: str
    bedrooms: int
    price: str
    bathrooms: str
    square_feet: str
    time_posted: str
    latitude: str
    longitude: str


def clean(value: str | None) -> str:
    value = (value or "").strip()
    value = value.replace("\r", " ").replace("\n", " ").replace("\0", "")
    return "" if value.lower() == "null" else value


def mysql_value(value: object) -> object:
    if value is None or value == "":
        return ""
    return value


def parse_int(value: str | None) -> int | None:
    value = clean(value)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_decimal(value: str | None) -> str:
    value = clean(value)
    if not value:
        return ""
    try:
        float(value)
    except ValueError:
        return ""
    return value


def parse_timestamp(value: str | None, shift: timedelta | None = None) -> str:
    timestamp = parse_int(value)
    if timestamp is None:
        return ""
    value_datetime = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    if shift is not None:
        value_datetime += shift
    return value_datetime.strftime("%Y-%m-%d %H:%M:%S")


def extract_zip(body: str | None) -> str:
    match = ZIP_RE.search(body or "")
    if not match:
        return ""
    return match.group(1).zfill(5)


def split_street(address: str) -> tuple[str, str]:
    address = clean(address)
    match = STREET_RE.match(address)
    if not match:
        return "", address
    return " ".join(match.group(1).split()), match.group(2).strip()


def synthetic_street(listing_id: int) -> tuple[str, str]:
    address_space = 9999 * len(SYNTHETIC_STREET_NAMES)
    slot = (listing_id * 7919) % address_space
    street_number = str(slot % 9999 + 1)
    street_name = f"{SYNTHETIC_STREET_NAMES[slot // 9999]} (S)"
    return street_number, street_name


def csv_reader(path: Path, delimiter: str = ",") -> Iterable[dict[str, str]]:
    csv.field_size_limit(sys.maxsize)
    with path.open(newline="", encoding="utf-8", errors="replace") as raw_file:
        yield from csv.DictReader(raw_file, delimiter=delimiter)


def split_semicolon_line(line: str) -> tuple[list[str], bool]:
    fields: list[str] = []
    current: list[str] = []
    in_quote = False
    quote_started_at_field_start = False
    i = 0

    while i < len(line):
        char = line[i]

        if char == '"':
            at_field_start = not current or (quote_started_at_field_start and in_quote)
            escaped_quote = in_quote and i + 1 < len(line) and line[i + 1] == '"'
            if escaped_quote:
                current.append('"')
                i += 2
                continue
            if at_field_start:
                in_quote = not in_quote
                quote_started_at_field_start = in_quote
            else:
                current.append(char)
        elif char == ";" and not in_quote:
            fields.append("".join(current))
            current = []
            quote_started_at_field_start = False
        else:
            current.append(char)

        i += 1

    fields.append("".join(current))
    return fields, not in_quote


def parse_apartment_physical_line(line: str) -> list[str]:
    fields, balanced = split_semicolon_line(line)
    if balanced and len(fields) == len(APARTMENT_HEADERS):
        return fields

    literal_fields = line.split(";")
    if len(literal_fields) == len(APARTMENT_HEADERS):
        return literal_fields

    return fields


def apartment_reader(path: Path) -> Iterable[dict[str, str]]:
    with path.open(encoding="utf-8", errors="replace") as raw_file:
        header = raw_file.readline().rstrip("\r\n")
        if header.split(";") != APARTMENT_HEADERS:
            raise ValueError(f"Unexpected apartment header in {path}")

        for line_number, line in enumerate(raw_file, start=2):
            fields = parse_apartment_physical_line(line.rstrip("\r\n"))
            if len(fields) != len(APARTMENT_HEADERS):
                raise ValueError(
                    f"Line {line_number} parsed to {len(fields)} fields; "
                    f"expected {len(APARTMENT_HEADERS)}"
                )
            yield dict(zip(APARTMENT_HEADERS, fields))


def write_csv(path: Path, headers: list[str], rows: Iterable[Iterable[object]]) -> int:
    count = 0
    with path.open("w", newline="", encoding="utf-8") as out_file:
        writer = csv.writer(out_file, lineterminator="\n")
        writer.writerow(headers)
        for row in rows:
            writer.writerow([mysql_value(value) for value in row])
            count += 1
    return count


def build_city_state(raw_dir: Path) -> tuple[dict[tuple[str, str], int], list[tuple[int, str, str]]]:
    pairs: set[tuple[str, str]] = set()

    for row in csv_reader(raw_dir / "uszips.csv"):
        city = clean(row.get("city"))
        state = clean(row.get("state_id")).upper()
        if city and state:
            pairs.add((city, state))

    for row in apartment_reader(raw_dir / "apartments_for_rent_classified_100K.csv"):
        city = clean(row.get("cityname"))
        state = clean(row.get("state")).upper()
        if city and state:
            pairs.add((city, state))

    ordered = sorted(pairs, key=lambda item: (item[1], item[0].casefold(), item[0]))
    city_state_ids = {pair: index for index, pair in enumerate(ordered, start=1)}
    rows = [(city_state_ids[pair], pair[0], pair[1]) for pair in ordered]
    return city_state_ids, rows


def build_demographics(raw_dir: Path) -> list[tuple[str, str, str, str]]:
    rows: OrderedDict[str, tuple[str, str, str, str]] = OrderedDict()

    for row in csv_reader(raw_dir / "uszips.csv"):
        zip_code = clean(row.get("zip")).zfill(5)
        population = parse_int(row.get("population"))
        latitude = parse_decimal(row.get("lat")) or "0"
        longitude = parse_decimal(row.get("lng")) or "0"
        if not zip_code:
            continue
        rows[zip_code] = (zip_code, population or 0, latitude, longitude)

    return list(rows.values())


def build_zip_lookup(raw_dir: Path) -> tuple[dict[tuple[str, str], str], set[str], str]:
    first_zip_by_city_state: dict[tuple[str, str], str] = {}
    all_zips: set[str] = set()
    first_zip = ""

    for row in csv_reader(raw_dir / "uszips.csv"):
        zip_code = clean(row.get("zip")).zfill(5)
        city = clean(row.get("city"))
        state = clean(row.get("state_id")).upper()
        if not zip_code:
            continue
        if not first_zip:
            first_zip = zip_code
        all_zips.add(zip_code)
        if city and state:
            first_zip_by_city_state.setdefault((city, state), zip_code)

    return first_zip_by_city_state, all_zips, first_zip


def build_time_shift(raw_dir: Path, target_max_date: date) -> timedelta:
    max_timestamp: int | None = None

    for row in apartment_reader(raw_dir / "apartments_for_rent_classified_100K.csv"):
        timestamp = parse_int(row.get("time"))
        if timestamp is not None and (max_timestamp is None or timestamp > max_timestamp):
            max_timestamp = timestamp

    if max_timestamp is None:
        return timedelta()

    max_datetime = datetime.fromtimestamp(max_timestamp, tz=timezone.utc)
    target_datetime = datetime.combine(
        target_max_date,
        max_datetime.timetz(),
        tzinfo=timezone.utc,
    )
    return target_datetime - max_datetime


def choose_zip(
    row: dict[str, str],
    city: str,
    state: str,
    first_zip_by_city_state: dict[tuple[str, str], str],
    all_zips: set[str],
    first_zip: str,
) -> str:
    zip_code = extract_zip(row.get("body"))
    if zip_code in all_zips:
        return zip_code
    return first_zip_by_city_state.get((city, state), first_zip)


def build_listing_tables(
    raw_dir: Path, city_state_ids: dict[tuple[str, str], int], time_shift: timedelta
) -> tuple[
    list[tuple[int, str, str, str, int]],
    list[tuple[int, int, str, str, int, str, str, str, str, str, str]],
    list[tuple[int, str]],
    list[tuple[int, int]],
    dict[str, int],
]:
    addresses: OrderedDict[AddressRow, int] = OrderedDict()
    listings: list[ListingRow] = []
    amenity_names: set[str] = set()
    listing_amenity_names: list[tuple[int, str]] = []
    first_zip_by_city_state, all_zips, first_zip = build_zip_lookup(raw_dir)
    stats = {
        "reused_previous_city_state": 0,
        "used_zip_from_uszips": 0,
        "generated_address": 0,
        "defaulted_bedrooms": 0,
        "defaulted_price": 0,
    }
    last_city_state: tuple[str, str] | None = None

    for row in apartment_reader(raw_dir / "apartments_for_rent_classified_100K.csv"):
        city = clean(row.get("cityname"))
        state = clean(row.get("state")).upper()
        if city and state:
            last_city_state = (city, state)
        elif last_city_state is not None:
            city, state = last_city_state
            stats["reused_previous_city_state"] += 1

        city_state_id = city_state_ids.get((city, state))
        if city_state_id is None:
            raise ValueError(f"No city_state_id found for listing city/state: {city}, {state}")

        raw_zip = extract_zip(row.get("body"))
        zip_code = choose_zip(row, city, state, first_zip_by_city_state, all_zips, first_zip)
        if raw_zip != zip_code:
            stats["used_zip_from_uszips"] += 1

        raw_address = clean(row.get("address"))
        if raw_address:
            street_number, street_name = split_street(raw_address)
            if not street_number:
                street_number = "0"
        else:
            street_number, street_name = synthetic_street(len(listings) + 1)
            stats["generated_address"] += 1

        address = AddressRow(street_number, street_name, zip_code, city_state_id)
        if address not in addresses:
            addresses[address] = len(addresses) + 1
        address_id = addresses[address]

        title = clean(row.get("title"))
        if not title:
            title = f"Apartment Listing {clean(row.get('id')) or len(listings) + 1}"

        bedrooms = parse_int(row.get("bedrooms"))
        if bedrooms is None:
            bedrooms = 0
            stats["defaulted_bedrooms"] += 1

        price = parse_decimal(row.get("price"))
        if not price:
            price = "0"
            stats["defaulted_price"] += 1

        time_posted = parse_timestamp(row.get("time"), time_shift)
        if not time_posted:
            time_posted = "1970-01-01 00:00:00"

        listing_id = len(listings) + 1
        listing = ListingRow(
            listing_id=listing_id,
            address_id=address_id,
            title=title,
            description=clean(row.get("body")),
            bedrooms=bedrooms,
            price=price,
            bathrooms=parse_decimal(row.get("bathrooms")) or "0",
            square_feet=parse_int(row.get("square_feet")) or 0,
            time_posted=time_posted,
            latitude=parse_decimal(row.get("latitude")) or "0",
            longitude=parse_decimal(row.get("longitude")) or "0",
        )
        listings.append(listing)

        for amenity in clean(row.get("amenities")).split(","):
            amenity = amenity.strip()
            if not amenity:
                continue
            amenity_names.add(amenity)
            listing_amenity_names.append((listing_id, amenity))

    amenity_rows = [(index, name) for index, name in enumerate(sorted(amenity_names), start=1)]
    amenity_ids = {name: amenity_id for amenity_id, name in amenity_rows}
    listing_amenity_rows = [
        (listing_id, amenity_ids[name])
        for listing_id, name in listing_amenity_names
    ]

    address_rows = [
        (address_id, row.street_number, row.street_name, row.zip_code, row.city_state_id)
        for row, address_id in addresses.items()
    ]
    listing_rows = [
        (
            row.listing_id,
            row.address_id,
            row.title,
            row.description,
            row.bedrooms,
            row.price,
            row.bathrooms,
            row.square_feet,
            row.time_posted,
            row.latitude,
            row.longitude,
        )
        for row in listings
    ]

    return address_rows, listing_rows, amenity_rows, listing_amenity_rows, stats


def process(raw_dir: Path, import_dir: Path, target_max_date: date) -> dict[str, int]:
    import_dir.mkdir(parents=True, exist_ok=True)

    city_state_ids, city_state_rows = build_city_state(raw_dir)
    demographics_rows = build_demographics(raw_dir)
    time_shift = build_time_shift(raw_dir, target_max_date)
    address_rows, listing_rows, amenity_rows, listing_amenity_rows, stats = build_listing_tables(
        raw_dir, city_state_ids, time_shift
    )
    demographic_zips = {row[0] for row in demographics_rows}
    for _address_id, _street_number, _street_name, zip_code, _city_state_id in address_rows:
        if zip_code not in demographic_zips:
            demographics_rows.append((zip_code, 0, 0, 0))
            demographic_zips.add(zip_code)
    demographics_rows.sort(key=lambda row: row[0])

    counts = {
        "CityState": write_csv(
            import_dir / "CityState.csv",
            ["city_state_id", "city", "state"],
            city_state_rows,
        ),
        "ZipCodeDemographics": write_csv(
            import_dir / "ZipCodeDemographics.csv",
            ["zip", "population", "latitude", "longitude"],
            demographics_rows,
        ),
        "Address": write_csv(
            import_dir / "Address.csv",
            ["address_id", "street_number", "street_name", "zip", "city_state_id"],
            address_rows,
        ),
        "ApartmentListing": write_csv(
            import_dir / "ApartmentListing.csv",
            [
                "listing_id",
                "address_id",
                "title",
                "description",
                "bedrooms",
                "price",
                "bathrooms",
                "square_feet",
                "listing_time",
                "latitude",
                "longitude",
            ],
            listing_rows,
        ),
        "Amenity": write_csv(
            import_dir / "Amenity.csv",
            ["amenity_id", "amenity_name"],
            amenity_rows,
        ),
        "ListingAmenity": write_csv(
            import_dir / "ListingAmenity.csv",
            ["listing_id", "amenity_id"],
            listing_amenity_rows,
        ),
    }
    counts.update(stats)
    counts["shifted_listing_days"] = time_shift.days
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process raw apartment data into MySQL-importable CSV files."
    )
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--import-dir", type=Path, default=Path("data/import"))
    parser.add_argument(
        "--target-max-date",
        type=date.fromisoformat,
        default=date(2026, 7, 28),
        help="Shift listing times so the latest listing falls on this YYYY-MM-DD date.",
    )
    args = parser.parse_args()

    counts = process(args.raw_dir, args.import_dir, args.target_max_date)
    for name, count in counts.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
