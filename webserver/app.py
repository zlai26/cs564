from __future__ import annotations

import getpass
import os
from decimal import Decimal
from math import ceil
from typing import Any
from urllib.parse import urlencode

from flask import Flask, redirect, render_template, request, url_for
import mysql.connector
from mysql.connector import Error


app = Flask(__name__)

DB_CONFIG: dict[str, Any] = {}
RESULT_LIMIT = 1000
PAGE_SIZE = 20

AMENITY_ICON_RULES = [
    ("air", "air.ico", "AC"),
    ("internet", "internet.ico", "Wi"),
    ("wifi", "internet.ico", "Wi"),
    ("gym", "gym.ico", "H"),
    ("fitness", "gym.ico", "H"),
    ("pool", "pool.ico", "~"),
    ("parking", "parking.ico", "P"),
    ("pet", "pet.ico", "PT"),
    ("dishwasher", "dishwasher.ico", "D"),
    ("laundry", "laundry.ico", "L"),
    ("washer", "laundry.ico", "WD"),
    ("storage", "storage.ico", "S"),
    ("clubhouse", "clubhouse.ico", "CH"),
    ("patio", "patio.ico", "PD"),
    ("deck", "patio.ico", "PD"),
]


CHECKPOINT_QUERIES = [
    {
        "id": "q1",
        "title": "Search by City, Price, and Bedrooms",
        "sql": """
            SELECT
                l.listing_id,
                l.title,
                cs.city,
                cs.state,
                l.bedrooms,
                l.bathrooms,
                l.square_feet,
                l.price
            FROM ApartmentListing AS l
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
            WHERE cs.city = 'Raleigh'
              AND cs.state = 'NC'
              AND l.price BETWEEN 900 AND 1800
              AND l.bedrooms >= 2
            ORDER BY l.price ASC, l.square_feet DESC
            LIMIT 20
        """,
    },
    {
        "id": "q2",
        "title": "Listings with Parking",
        "sql": """
            SELECT
                l.listing_id,
                l.title,
                cs.city,
                cs.state,
                l.price,
                a.amenity_name
            FROM ApartmentListing AS l
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
            JOIN ListingAmenity AS la ON l.listing_id = la.listing_id
            JOIN Amenity AS a ON la.amenity_id = a.amenity_id
            WHERE a.amenity_name = 'Parking'
              AND l.price > 0
            ORDER BY l.price ASC
            LIMIT 20
        """,
    },
    {
        "id": "q3",
        "title": "Rental Market by City",
        "sql": """
            SELECT
                cs.city,
                cs.state,
                COUNT(*) AS listing_count,
                ROUND(AVG(l.price), 2) AS avg_price,
                MIN(l.price) AS min_price,
                MAX(l.price) AS max_price,
                ROUND(AVG(l.square_feet), 0) AS avg_square_feet
            FROM ApartmentListing AS l
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
            WHERE l.price > 0
            GROUP BY cs.city, cs.state
            HAVING COUNT(*) >= 20
            ORDER BY avg_price ASC
            LIMIT 20
        """,
    },
    {
        "id": "q4",
        "title": "Common Amenities",
        "sql": """
            SELECT
                a.amenity_name,
                COUNT(*) AS listing_count,
                ROUND(AVG(l.price), 2) AS avg_price,
                ROUND(AVG(l.square_feet), 0) AS avg_square_feet
            FROM Amenity AS a
            JOIN ListingAmenity AS la ON a.amenity_id = la.amenity_id
            JOIN ApartmentListing AS l ON la.listing_id = l.listing_id
            WHERE l.price > 0
            GROUP BY a.amenity_id, a.amenity_name
            HAVING COUNT(*) >= 100
            ORDER BY listing_count DESC, avg_price ASC
        """,
    },
    {
        "id": "q5",
        "title": "Saved Listings for Alex",
        "sql": """
            SELECT
                s.user_name,
                s.saved_at,
                l.listing_id,
                l.title,
                cs.city,
                cs.state,
                ad.zip,
                l.price,
                l.bedrooms,
                l.square_feet
            FROM SavedListing AS s
            JOIN ApartmentListing AS l ON s.listing_id = l.listing_id
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
            WHERE s.user_name = 'alex'
            ORDER BY s.saved_at DESC
        """,
    },
    {
        "id": "q6",
        "title": "Price Compared with City Average",
        "sql": """
            SELECT
                l.listing_id,
                l.title,
                market.city,
                market.state,
                l.price,
                market.avg_city_price,
                ROUND(l.price - market.avg_city_price, 2) AS difference_from_city_avg,
                CASE
                    WHEN l.price < market.avg_city_price * 0.90 THEN 'Below market'
                    WHEN l.price > market.avg_city_price * 1.10 THEN 'Above market'
                    ELSE 'Near market'
                END AS price_position
            FROM ApartmentListing AS l
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN (
                SELECT
                    ad2.city_state_id,
                    cs2.city,
                    cs2.state,
                    ROUND(AVG(l2.price), 2) AS avg_city_price
                FROM ApartmentListing AS l2
                JOIN Address AS ad2 ON l2.address_id = ad2.address_id
                JOIN CityState AS cs2 ON ad2.city_state_id = cs2.city_state_id
                WHERE l2.price > 0
                GROUP BY ad2.city_state_id, cs2.city, cs2.state
            ) AS market ON ad.city_state_id = market.city_state_id
            WHERE l.price > 0
            ORDER BY difference_from_city_avg ASC
            LIMIT 20
        """,
    },
    {
        "id": "q7",
        "title": "Listings within 10 Miles of ZIP 27607",
        "sql": """
            SELECT
                l.listing_id,
                l.title,
                cs.city,
                cs.state,
                ad.zip,
                l.price,
                ROUND(
                    3959 * 2 * ASIN(SQRT(
                        POWER(SIN(RADIANS(l.latitude - z.latitude) / 2), 2) +
                        COS(RADIANS(z.latitude)) * COS(RADIANS(l.latitude)) *
                        POWER(SIN(RADIANS(l.longitude - z.longitude) / 2), 2)
                    )),
                    2
                ) AS distance_miles
            FROM ApartmentListing AS l
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
            JOIN ZipCodeDemographics AS z ON z.zip = '27607'
            WHERE l.latitude <> 0
              AND l.longitude <> 0
            HAVING distance_miles <= 10
            ORDER BY distance_miles ASC, l.price ASC
            LIMIT 20
        """,
    },
    {
        "id": "q8",
        "title": "Listings with Parking and Pool",
        "sql": """
            SELECT
                l.listing_id,
                l.title,
                cs.city,
                cs.state,
                l.price,
                GROUP_CONCAT(a.amenity_name ORDER BY a.amenity_name SEPARATOR ', ') AS matched_amenities
            FROM ApartmentListing AS l
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
            JOIN ListingAmenity AS la ON l.listing_id = la.listing_id
            JOIN Amenity AS a ON la.amenity_id = a.amenity_id
            WHERE a.amenity_name IN ('Parking', 'Pool')
            GROUP BY l.listing_id, l.title, cs.city, cs.state, l.price
            HAVING COUNT(DISTINCT a.amenity_name) = 2
            ORDER BY l.price ASC
            LIMIT 20
        """,
    },
    {
        "id": "q9",
        "title": "Below-Market High-Population ZIPs",
        "sql": """
            SELECT
                l.listing_id,
                l.title,
                ad.zip,
                z.population,
                l.price,
                zip_market.avg_zip_price
            FROM ApartmentListing AS l
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN ZipCodeDemographics AS z ON ad.zip = z.zip
            JOIN (
                SELECT
                    ad2.zip,
                    AVG(l2.price) AS avg_zip_price
                FROM ApartmentListing AS l2
                JOIN Address AS ad2 ON l2.address_id = ad2.address_id
                WHERE l2.price > 0
                GROUP BY ad2.zip
            ) AS zip_market ON ad.zip = zip_market.zip
            WHERE z.population > (
                    SELECT AVG(population)
                    FROM ZipCodeDemographics
                    WHERE population > 0
                )
              AND l.price > 0
              AND l.price < zip_market.avg_zip_price * 0.85
            ORDER BY z.population DESC, l.price ASC
            LIMIT 20
        """,
    },
    {
        "id": "q10",
        "title": "Recommended Listings for Alex",
        "sql": """
            SELECT
                l.listing_id,
                l.title,
                cs.city,
                cs.state,
                l.price,
                COUNT(DISTINCT la.amenity_id) AS matching_saved_amenities
            FROM ApartmentListing AS l
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
            JOIN ListingAmenity AS la ON l.listing_id = la.listing_id
            JOIN (
                SELECT DISTINCT la_saved.amenity_id
                FROM SavedListing AS s
                JOIN ListingAmenity AS la_saved ON s.listing_id = la_saved.listing_id
                WHERE s.user_name = 'alex'
            ) AS preferred ON la.amenity_id = preferred.amenity_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM SavedListing AS already_saved
                WHERE already_saved.user_name = 'alex'
                  AND already_saved.listing_id = l.listing_id
            )
            GROUP BY l.listing_id, l.title, cs.city, cs.state, l.price
            HAVING COUNT(DISTINCT la.amenity_id) >= 2
            ORDER BY matching_saved_amenities DESC, l.price ASC
            LIMIT 20
        """,
    },
]


def prompt(value_name: str, default: str, secret: bool = False) -> str:
    label = f"{value_name} [{default}]: "
    if secret:
        value = getpass.getpass(label)
    else:
        value = input(label)
    return value.strip() or default


def configure_database() -> None:
    DB_CONFIG.update(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        database=os.environ.get("MYSQL_DATABASE") or prompt("Schema", "cs564"),
        user=os.environ.get("MYSQL_USER") or prompt("User", "root"),
        password=os.environ.get("MYSQL_PASSWORD")
        if os.environ.get("MYSQL_PASSWORD") is not None
        else prompt("Password", "", secret=True),
    )


def db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> tuple[list[dict[str, Any]], str | None]:
    try:
        with db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql, params)
                rows = [
                    {key: normalize_value(value) for key, value in row.items()}
                    for row in cursor.fetchall()
                ]
                return rows, None
    except Error as exc:
        return [], str(exc)


def call_proc(name: str, args: list[Any]) -> tuple[list[dict[str, Any]], str | None]:
    try:
        with db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.callproc(name, args)
                rows: list[dict[str, Any]] = []
                for result in cursor.stored_results():
                    rows.extend(
                        {
                            key: normalize_value(value)
                            for key, value in row.items()
                        }
                        for row in result.fetchall()
                    )
                conn.commit()
                return rows, None
    except Error as exc:
        return [], str(exc)


def execute_write(sql: str, params: tuple[Any, ...] = ()) -> str | None:
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()
            return None
    except Error as exc:
        return str(exc)


def maybe_number(value: str, cast_type: type = int) -> Any:
    value = value.strip()
    if not value:
        return None
    return cast_type(value)


def amenity_icons(amenities: str | None, limit: int = 4) -> dict[str, Any]:
    names = [
        amenity.strip()
        for amenity in str(amenities or "").split(",")
        if amenity.strip()
    ]
    icons = []
    for name in names:
        normalized = name.lower()
        first_letter = next((char for char in name.upper() if char.isalnum()), "A")
        if normalized in {"ac", "a/c"}:
            filename = "air.ico"
            fallback_text = "AC"
        else:
            filename = ""
            fallback_text = first_letter
        for token, candidate_filename, candidate_text in AMENITY_ICON_RULES:
            if token in normalized:
                filename = candidate_filename
                fallback_text = candidate_text
                break
        icons.append({"label": name, "filename": filename, "fallback_text": fallback_text})

    return {"visible": icons[:limit], "extra": max(len(icons) - limit, 0)}


app.jinja_env.filters["amenity_icons"] = amenity_icons


def get_query_results() -> list[dict[str, Any]]:
    results = []
    for query in CHECKPOINT_QUERIES:
        rows, error = fetch_all(query["sql"])
        results.append({**query, "rows": rows, "error": error})
    return results


def get_amenity_options() -> tuple[list[str], str | None]:
    rows, error = fetch_all(
        """
            SELECT amenity_name
            FROM Amenity
            ORDER BY amenity_name
        """
    )
    return [row["amenity_name"] for row in rows], error


def get_user_options() -> tuple[list[dict[str, Any]], str | None]:
    rows, error = fetch_all(
        """
            SELECT user_name, email
            FROM AppUser
            ORDER BY user_name
        """
    )
    return rows, error


def get_dashboard_data() -> dict[str, Any]:
    stats_sql = """
        SELECT
            COUNT(*) AS listings,
            ROUND(AVG(price), 0) AS avg_price,
            MIN(price) AS min_price,
            MAX(price) AS max_price
        FROM ApartmentListing
        WHERE price > 0
    """
    review_sql = "SELECT COUNT(*) AS reviews, ROUND(AVG(rating), 2) AS avg_rating FROM Review"
    zip_sql = """
        SELECT
            ROUND(AVG(population), 0) AS avg_population,
            MAX(population) AS max_population,
            COUNT(*) AS zip_count
        FROM ZipCodeDemographics
        WHERE population > 0
    """

    stats, stats_error = fetch_all(stats_sql)
    reviews, reviews_error = fetch_all(review_sql)
    zip_stats, zip_error = fetch_all(zip_sql)

    return {
        "stats": stats[0] if stats else {},
        "reviews": reviews[0] if reviews else {},
        "zip_stats": zip_stats[0] if zip_stats else {},
        "errors": [err for err in [stats_error, reviews_error, zip_error] if err],
    }


def get_review_count_for_listings(listing_ids: list[int]) -> tuple[int, str | None]:
    if not listing_ids:
        return 0, None

    placeholders = ", ".join(["%s"] * len(listing_ids))
    rows, error = fetch_all(
        f"""
            SELECT COUNT(*) AS review_count
            FROM Review
            WHERE listing_id IN ({placeholders})
        """,
        tuple(listing_ids),
    )
    if error:
        return 0, error
    return int(rows[0]["review_count"]) if rows else 0, None


def get_listing_detail(listing_id: int, user_name: str) -> tuple[dict[str, Any] | None, str | None]:
    rows, error = fetch_all(
        """
            SELECT
                l.listing_id,
                l.title,
                l.description,
                l.bedrooms,
                l.bathrooms,
                l.square_feet,
                l.price,
                l.listing_time,
                l.latitude,
                l.longitude,
                ad.street_number,
                ad.street_name,
                ad.zip,
                cs.city,
                cs.state,
                z.population,
                GROUP_CONCAT(DISTINCT a.amenity_name ORDER BY a.amenity_name SEPARATOR ', ') AS amenities,
                CASE WHEN saved.listing_id IS NULL THEN 0 ELSE 1 END AS is_saved
            FROM ApartmentListing AS l
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
            LEFT JOIN ZipCodeDemographics AS z ON ad.zip = z.zip
            LEFT JOIN ListingAmenity AS la ON l.listing_id = la.listing_id
            LEFT JOIN Amenity AS a ON la.amenity_id = a.amenity_id
            LEFT JOIN SavedListing AS saved
                ON saved.listing_id = l.listing_id
               AND saved.user_name = %s
            WHERE l.listing_id = %s
            GROUP BY
                l.listing_id, l.title, l.description, l.bedrooms, l.bathrooms,
                l.square_feet, l.price, l.listing_time, l.latitude, l.longitude,
                ad.street_number, ad.street_name, ad.zip, cs.city, cs.state,
                z.population, saved.listing_id
        """,
        (user_name, listing_id),
    )
    if error:
        return None, error
    return rows[0] if rows else None, None


def get_listing_reviews(listing_id: int) -> tuple[list[dict[str, Any]], str | None]:
    return fetch_all(
        """
            SELECT user_name, rating, review_text, review_time
            FROM Review
            WHERE listing_id = %s
            ORDER BY review_time DESC
        """,
        (listing_id,),
    )


def get_saved_listings(user_name: str) -> tuple[list[dict[str, Any]], str | None]:
    return fetch_all(
        """
            SELECT
                l.listing_id,
                l.title,
                cs.city,
                cs.state,
                ad.zip,
                l.bedrooms,
                l.bathrooms,
                l.square_feet,
                l.price,
                s.saved_at,
                GROUP_CONCAT(DISTINCT a.amenity_name ORDER BY a.amenity_name SEPARATOR ', ') AS amenities
            FROM SavedListing AS s
            JOIN ApartmentListing AS l ON s.listing_id = l.listing_id
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
            LEFT JOIN ListingAmenity AS la ON l.listing_id = la.listing_id
            LEFT JOIN Amenity AS a ON la.amenity_id = a.amenity_id
            WHERE s.user_name = %s
            GROUP BY
                l.listing_id, l.title, cs.city, cs.state, ad.zip,
                l.bedrooms, l.bathrooms, l.square_feet, l.price, s.saved_at
            ORDER BY s.saved_at DESC
        """,
        (user_name,),
    )


def get_population_summary_for_zips(zips: set[str]) -> tuple[dict[str, Any], str | None]:
    if not zips:
        return {"avg_population": 0, "top_zip": "", "top_zip_population": 0}, None

    placeholders = ", ".join(["%s"] * len(zips))
    rows, error = fetch_all(
        f"""
            SELECT zip, population
            FROM ZipCodeDemographics
            WHERE zip IN ({placeholders})
              AND population > 0
        """,
        tuple(zips),
    )
    if error:
        return {"avg_population": 0, "top_zip": "", "top_zip_population": 0}, error
    if not rows:
        return {"avg_population": 0, "top_zip": "", "top_zip_population": 0}, None

    top_row = max(rows, key=lambda row: row["population"])
    avg_population = round(
        sum(float(row["population"]) for row in rows) / len(rows),
        0,
    )
    return {
        "avg_population": avg_population,
        "top_zip": top_row["zip"],
        "top_zip_population": top_row["population"],
    }, None


def summarize_listing_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    listing_ids = [int(row["listing_id"]) for row in rows if row.get("listing_id") is not None]
    review_count, review_error = get_review_count_for_listings(listing_ids)
    prices = [float(row["price"]) for row in rows if row.get("price")]
    zips = {row["zip"] for row in rows if row.get("zip")}
    population_summary, population_error = get_population_summary_for_zips(zips)

    return {
        "listing_count": len(rows),
        "avg_price": round(sum(prices) / len(prices), 0) if prices else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "review_count": review_count,
        "zip_count": len(zips),
        "avg_population": population_summary.get("avg_population") or 0,
        "top_zip": population_summary.get("top_zip") or "",
        "top_zip_population": population_summary.get("top_zip_population") or 0,
        "error": review_error or population_error,
    }


def listing_has_selected_amenities(row: dict[str, Any], selected_amenities: list[str]) -> bool:
    if not selected_amenities:
        return True

    row_amenities = {
        amenity.strip()
        for amenity in str(row.get("amenities") or "").split(",")
        if amenity.strip()
    }
    return all(amenity in row_amenities for amenity in selected_amenities)


def run_zip_search(search_values: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    zip_code = search_values["zip_code"].strip()
    miles = maybe_number(search_values["miles"], float) or 10
    selected_amenities = search_values["amenities"]
    rows, error = fetch_all(
        """
            SELECT
                l.listing_id,
                l.title,
                cs.city,
                cs.state,
                ad.zip,
                l.bedrooms,
                l.bathrooms,
                l.square_feet,
                l.price,
                ROUND(
                    3959 * 2 * ASIN(SQRT(
                        POWER(SIN(RADIANS(l.latitude - z.latitude) / 2), 2) +
                        COS(RADIANS(z.latitude)) * COS(RADIANS(l.latitude)) *
                        POWER(SIN(RADIANS(l.longitude - z.longitude) / 2), 2)
                    )),
                    2
                ) AS distance_miles,
                GROUP_CONCAT(DISTINCT a.amenity_name ORDER BY a.amenity_name SEPARATOR ', ') AS amenities
            FROM ApartmentListing AS l
            JOIN Address AS ad ON l.address_id = ad.address_id
            JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
            JOIN ZipCodeDemographics AS z ON z.zip = %s
            LEFT JOIN ListingAmenity AS la ON l.listing_id = la.listing_id
            LEFT JOIN Amenity AS a ON la.amenity_id = a.amenity_id
            WHERE l.latitude <> 0
              AND l.longitude <> 0
              AND (%s IS NULL OR l.price >= %s)
              AND (%s IS NULL OR l.price <= %s)
              AND (%s IS NULL OR l.bedrooms >= %s)
            GROUP BY
                l.listing_id, l.title, cs.city, cs.state, ad.zip,
                l.bedrooms, l.bathrooms, l.square_feet, l.price,
                l.latitude, l.longitude, z.latitude, z.longitude
            HAVING distance_miles <= %s
            ORDER BY distance_miles ASC, l.price ASC
            LIMIT %s
        """,
        (
            zip_code,
            maybe_number(search_values["min_price"], float),
            maybe_number(search_values["min_price"], float),
            maybe_number(search_values["max_price"], float),
            maybe_number(search_values["max_price"], float),
            maybe_number(search_values["bedrooms"], int),
            maybe_number(search_values["bedrooms"], int),
            miles,
            RESULT_LIMIT,
        ),
    )
    if error:
        return [], error

    min_bathrooms = maybe_number(search_values["bathrooms"], float)
    if min_bathrooms is not None:
        rows = [
            row
            for row in rows
            if row.get("bathrooms") is not None and float(row["bathrooms"]) >= min_bathrooms
        ]
    rows = [row for row in rows if listing_has_selected_amenities(row, selected_amenities)]
    return rows[:RESULT_LIMIT], None


def run_listing_search(search_values: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    if search_values["zip_code"].strip():
        return run_zip_search(search_values)

    selected_amenities = search_values["amenities"]
    rows, error = call_proc(
        "sp_search_listings",
        [
            search_values["city"] or None,
            search_values["state"] or None,
            maybe_number(search_values["min_price"], float),
            maybe_number(search_values["max_price"], float),
            maybe_number(search_values["bedrooms"], int),
            selected_amenities[0] if selected_amenities else None,
            RESULT_LIMIT,
        ],
    )
    if error:
        return [], error

    min_bathrooms = maybe_number(search_values["bathrooms"], float)
    if min_bathrooms is not None:
        rows = [
            row
            for row in rows
            if row.get("bathrooms") is not None and float(row["bathrooms"]) >= min_bathrooms
        ]
    rows = [row for row in rows if listing_has_selected_amenities(row, selected_amenities)]
    return rows[:RESULT_LIMIT], None


def page_url(page: int, search_values: dict[str, Any]) -> str:
    params = {
        "user_name": search_values["user_name"],
        "city": search_values["city"],
        "state": search_values["state"],
        "min_price": search_values["min_price"],
        "max_price": search_values["max_price"],
        "bedrooms": search_values["bedrooms"],
        "bathrooms": search_values["bathrooms"],
        "zip_code": search_values["zip_code"],
        "miles": search_values["miles"],
        "amenities": search_values["amenities"],
        "page": page,
    }
    return f"{url_for('index')}?{urlencode(params, doseq=True)}"


def redirect_with_params(next_url: str, **params: str):
    separator = "&" if "?" in next_url else "?"
    return redirect(f"{next_url}{separator}{urlencode(params)}")


def selected_user_context(user_name: str) -> tuple[list[dict[str, Any]], dict[str, Any], str | None]:
    user_options, user_error = get_user_options()
    selected_user = next(
        (user for user in user_options if user["user_name"] == user_name),
        {"user_name": user_name, "email": f"{user_name}@example.com"},
    )
    return user_options, selected_user, user_error


@app.route("/", methods=["GET", "POST"])
def index():
    message = request.args.get("message")
    action_error = request.args.get("error")
    search_rows: list[dict[str, Any]] = []
    search_values = {
        "user_name": "alex",
        "city": "Raleigh",
        "state": "NC",
        "min_price": "900",
        "max_price": "1800",
        "bedrooms": "2",
        "bathrooms": "",
        "zip_code": "",
        "miles": "10",
        "amenities": [],
    }

    if request.args:
        selected_amenities = request.args.getlist("amenities")
        search_values.update(
            {
                "user_name": request.args.get("user_name", search_values["user_name"]),
                "city": request.args.get("city", search_values["city"]),
                "state": request.args.get("state", search_values["state"]),
                "min_price": request.args.get("min_price", search_values["min_price"]),
                "max_price": request.args.get("max_price", search_values["max_price"]),
                "bedrooms": request.args.get("bedrooms", search_values["bedrooms"]),
                "bathrooms": request.args.get("bathrooms", search_values["bathrooms"]),
                "zip_code": request.args.get("zip_code", search_values["zip_code"]),
                "miles": request.args.get("miles", search_values["miles"]),
                "amenities": selected_amenities,
            }
        )

    search_rows, search_error = run_listing_search(search_values)
    if search_error:
        action_error = search_error
    if search_values["zip_code"].strip() and search_rows:
        search_values["city"] = search_rows[0].get("city") or search_values["city"]
        search_values["state"] = search_rows[0].get("state") or search_values["state"]

    dashboard = get_dashboard_data()
    amenity_options, amenity_error = get_amenity_options()
    if amenity_error:
        dashboard["errors"].append(amenity_error)
    user_options, selected_user, user_error = selected_user_context(search_values["user_name"])
    if user_error:
        dashboard["errors"].append(user_error)
    requested_page = request.args.get("page", "1")
    page = int(requested_page) if requested_page.isdigit() else 1
    page_count = max(ceil(len(search_rows) / PAGE_SIZE), 1)
    page = min(max(page, 1), page_count)
    page_start = (page - 1) * PAGE_SIZE
    displayed_rows = search_rows[page_start:page_start + PAGE_SIZE]
    current_summary = summarize_listing_rows(search_rows)
    if current_summary["error"]:
        dashboard["errors"].append(current_summary["error"])
    return render_template(
        "index.html",
        dashboard=dashboard,
        current_summary=current_summary,
        displayed_rows=displayed_rows,
        search_rows=search_rows,
        search_values=search_values,
        page=page,
        page_count=page_count,
        prev_page_url=page_url(page - 1, search_values) if page > 1 else None,
        next_page_url=page_url(page + 1, search_values) if page < page_count else None,
        amenity_options=amenity_options,
        user_options=user_options,
        selected_user=selected_user,
        message=message,
        action_error=action_error,
        db_config=DB_CONFIG,
    )


@app.get("/saved")
def saved_page():
    user_name = request.args.get("user_name", "alex")
    user_options, selected_user, user_error = selected_user_context(user_name)
    saved_rows, saved_error = get_saved_listings(selected_user["user_name"])
    requested_page = request.args.get("page", "1")
    page = int(requested_page) if requested_page.isdigit() else 1
    page_count = max(ceil(len(saved_rows) / PAGE_SIZE), 1)
    page = min(max(page, 1), page_count)
    page_start = (page - 1) * PAGE_SIZE
    displayed_rows = saved_rows[page_start:page_start + PAGE_SIZE]

    def saved_page_url(page_number: int) -> str:
        return f"{url_for('saved_page')}?{urlencode({'user_name': selected_user['user_name'], 'page': page_number})}"

    return render_template(
        "saved.html",
        displayed_rows=displayed_rows,
        saved_rows=saved_rows,
        user_options=user_options,
        selected_user=selected_user,
        page=page,
        page_count=page_count,
        prev_page_url=saved_page_url(page - 1) if page > 1 else None,
        next_page_url=saved_page_url(page + 1) if page < page_count else None,
        errors=[err for err in [user_error, saved_error] if err],
        message=request.args.get("message"),
        action_error=request.args.get("error"),
        db_config=DB_CONFIG,
    )


@app.get("/queries")
def queries_page():
    query_results = get_query_results()
    return render_template(
        "queries.html",
        queries=query_results,
        db_config=DB_CONFIG,
    )


@app.get("/listing/<int:listing_id>")
def listing_detail(listing_id: int):
    user_name = request.args.get("user_name", "alex")
    user_options, user_error = get_user_options()
    selected_user = next(
        (user for user in user_options if user["user_name"] == user_name),
        {"user_name": user_name, "email": f"{user_name}@example.com"},
    )
    listing, listing_error = get_listing_detail(listing_id, selected_user["user_name"])
    reviews, reviews_error = get_listing_reviews(listing_id)
    errors = [err for err in [user_error, listing_error, reviews_error] if err]

    return render_template(
        "listing_detail.html",
        listing=listing,
        reviews=reviews,
        errors=errors,
        selected_user=selected_user,
        user_options=user_options,
        db_config=DB_CONFIG,
        back_url=request.args.get("back") or url_for("index", user_name=selected_user["user_name"]),
    )


@app.get("/admin")
def admin_page():
    users, user_error = get_user_options()
    return render_template(
        "admin.html",
        users=users,
        errors=[err for err in [user_error] if err],
        message=request.args.get("message"),
        action_error=request.args.get("error"),
        db_config=DB_CONFIG,
    )


@app.post("/admin/users/add")
def admin_add_user():
    user_name = request.form.get("user_name", "").strip()
    email = request.form.get("email", "").strip()
    if not user_name or not email:
        return redirect_with_params(url_for("admin_page"), error="User name and email are required.")

    error = execute_write(
        """
            INSERT INTO AppUser (user_name, email)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE email = VALUES(email)
        """,
        (user_name, email),
    )
    if error:
        return redirect_with_params(url_for("admin_page"), error=error)
    return redirect_with_params(url_for("admin_page"), message=f"Saved user {user_name}")


@app.post("/admin/users/remove")
def admin_remove_user():
    user_name = request.form.get("user_name", "").strip()
    if not user_name:
        return redirect_with_params(url_for("admin_page"), error="Choose a user to remove.")

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM SavedListing WHERE user_name = %s", (user_name,))
                cursor.execute("DELETE FROM Review WHERE user_name = %s", (user_name,))
                cursor.execute("DELETE FROM AppUser WHERE user_name = %s", (user_name,))
                removed = cursor.rowcount
            conn.commit()
    except Error as exc:
        return redirect_with_params(url_for("admin_page"), error=str(exc))

    return redirect_with_params(url_for("admin_page"), message=f"Removed {removed} user row(s)")


@app.post("/save")
def save_listing():
    listing_id = int(request.form["listing_id"])
    rows, error = call_proc(
        "sp_save_listing",
        [
            request.form.get("user_name") or "alex",
            request.form.get("email") or "alex@example.com",
            listing_id,
        ],
    )
    next_url = request.form.get("next") or url_for("index")
    if error:
        return redirect_with_params(next_url, error=error)
    return redirect_with_params(next_url, message=f"Saved listing {rows[0]['listing_id'] if rows else listing_id}")


@app.post("/remove-save")
def remove_saved_listing():
    listing_id = int(request.form["listing_id"])
    rows, error = call_proc(
        "sp_remove_saved_listing",
        [request.form.get("user_name") or "alex", listing_id],
    )
    next_url = request.form.get("next") or url_for("index")
    if error:
        return redirect_with_params(next_url, error=error)
    removed = rows[0].get("rows_removed", 0) if rows else 0
    return redirect_with_params(next_url, message=f"Removed {removed} saved listing row(s)")


@app.post("/review")
def review_listing():
    listing_id = int(request.form["listing_id"])
    rows, error = call_proc(
        "sp_add_or_update_review",
        [
            request.form.get("user_name") or "alex",
            request.form.get("email") or "alex@example.com",
            listing_id,
            int(request.form.get("rating") or 5),
            request.form.get("review_text") or "Great apartment option.",
        ],
    )
    next_url = request.form.get("next") or url_for("index")
    if error:
        return redirect_with_params(next_url, error=error)
    return redirect_with_params(next_url, message=f"Review saved for listing {rows[0]['listing_id'] if rows else listing_id}")


@app.post("/price")
def update_price():
    listing_id = int(request.form["listing_id"])
    rows, error = call_proc(
        "sp_update_listing_price",
        [listing_id, float(request.form["new_price"])],
    )
    next_url = request.form.get("next") or url_for("admin_page")
    if error:
        return redirect_with_params(next_url, error=error)
    return redirect_with_params(next_url, message=f"Updated price for listing {rows[0]['listing_id'] if rows else listing_id}")


if __name__ == "__main__":
    configure_database()
    print(f"Starting AptFinder with schema '{DB_CONFIG['database']}' as user '{DB_CONFIG['user']}'.")
    app.run(host="127.0.0.1", port=8000, debug=True, use_reloader=False)
