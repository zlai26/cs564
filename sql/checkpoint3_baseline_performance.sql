-- Checkpoint 3 baseline performance script for Checkpoint 4 indexing.
-- Run before adding any new indexes. Save the runtime and EXPLAIN/EXPLAIN ANALYZE
-- output for the report.

-- Baseline 1: Q1 city/price/bedroom search.
EXPLAIN ANALYZE
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
LIMIT 20;

-- Baseline 2: Q2 amenity filter.
EXPLAIN ANALYZE
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
LIMIT 20;

-- Baseline 3: Q3 city market summary.
EXPLAIN ANALYZE
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
LIMIT 20;

-- Baseline 4: Q7 distance search around a ZIP code.
EXPLAIN ANALYZE
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
LIMIT 20;

-- Baseline 5: Q10 user recommendation query.
EXPLAIN ANALYZE
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
LIMIT 20;

