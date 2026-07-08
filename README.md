# COMPSCI 564 Project

## Data Preparation

Raw data is stored in `data/raw/` and processed by
`scripts/raw_data_processor.py`. The script generates MySQL-importable CSV files
under `data/import/`.

Run the processor with:

```bash
python scripts/raw_data_processor.py
```

The default run shifts apartment listing times so the newest listing date becomes
`2026-07-28`. This keeps the original relative ordering of listing times while
making demo queries such as "listed in the last two weeks" useful. To choose a
different latest listing date:

```bash
python scripts/raw_data_processor.py --target-max-date 2026-07-28
```

Generated files that are ready for MySQL import are under `data/import/`:

- `CityState.csv`
- `ZipCodeDemographics.csv`
- `Address.csv`
- `ApartmentListing.csv`
- `Amenity.csv`
- `ListingAmenity.csv`

Processing notes:

- Apartment rows are read as physical lines instead of using Python's CSV parser
  because some raw apartment records contain confusing quotation marks.
- Every physical apartment data line is treated as one listing record.
- Missing listing city/state values reuse the previous valid city/state.
- Missing ZIP values use the first matching ZIP found in `uszips.csv` for that
  city/state.
- Listings with missing addresses share one placeholder `Address` row with
  street number `0`, street name `Unknown`, ZIP `00000`, and city/state
  `Unknown, NA`.
- Missing numeric values that can cause MySQL import trouble are filled with `0`.
- `ZipCodeDemographics` uses ZIP, population, latitude, and longitude from
  `uszips.csv`.

## Table Creation

Copy and paste the contents of `create_tables.sql` into the MySQL command line
or MySQL Workbench before importing the CSV files.

Recommended MySQL import order:

1. `CityState`
2. `ZipCodeDemographics`
3. `Address`
4. `ApartmentListing`
5. `Amenity`
6. `ListingAmenity`
