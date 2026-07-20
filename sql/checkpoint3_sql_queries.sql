-- Checkpoint 3: 10 Level 2/Level 3 SQL queries.
-- Assumes:
--   1. create_tables.sql from the cleaned-data repository has been run.
--   2. python scripts\import_mysql_data.py has imported the six CSV tables.
--   3. checkpoint3_app_tables_and_seed.sql has been run for app demo tables.

-- Q1. Level 2: Search listings by city/state, price, and bedroom count.
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

-- Q2. Level 2: Find listings that include a selected amenity.
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

-- Q3. Level 2: Summarize rental market statistics by city/state.
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

-- Q4. Level 2: Show which amenities are common and their average listing price.
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
ORDER BY listing_count DESC, avg_price ASC;

-- Q5. Level 2: Display one user's saved listings with location details.
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
ORDER BY s.saved_at DESC;

-- Q6. Level 3: Compare each listing with the average price in its city/state.
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
LIMIT 20;

-- Q7. Level 3: Find listings within 10 miles of a selected ZIP center.
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

-- Q8. Level 3: Find listings that have both Parking and Pool amenities.
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
LIMIT 20;

-- Q9. Level 3: Find below-market listings in high-population ZIP codes.
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
LIMIT 20;

-- Q10. Level 3: Recommend listings based on amenities in a user's saved listings.
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

