-- Checkpoint 3: stored procedures for meaningful application tasks.
-- Run checkpoint3_app_tables_and_seed.sql before this file.

DROP PROCEDURE IF EXISTS sp_search_listings;
DROP PROCEDURE IF EXISTS sp_add_or_update_review;
DROP PROCEDURE IF EXISTS sp_save_listing;
DROP PROCEDURE IF EXISTS sp_remove_saved_listing;
DROP PROCEDURE IF EXISTS sp_update_listing_price;

DELIMITER $$

CREATE PROCEDURE sp_search_listings (
    IN p_city VARCHAR(100),
    IN p_state CHAR(2),
    IN p_min_price DECIMAL(10,2),
    IN p_max_price DECIMAL(10,2),
    IN p_min_bedrooms INT,
    IN p_amenity_name VARCHAR(100),
    IN p_result_limit INT
)
BEGIN
    DECLARE v_limit INT DEFAULT 25;

    IF p_result_limit IS NOT NULL AND p_result_limit > 0 THEN
        SET v_limit = LEAST(p_result_limit, 100);
    END IF;

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
        GROUP_CONCAT(DISTINCT a.amenity_name ORDER BY a.amenity_name SEPARATOR ', ') AS amenities
    FROM ApartmentListing AS l
    JOIN Address AS ad ON l.address_id = ad.address_id
    JOIN CityState AS cs ON ad.city_state_id = cs.city_state_id
    LEFT JOIN ListingAmenity AS la ON l.listing_id = la.listing_id
    LEFT JOIN Amenity AS a ON la.amenity_id = a.amenity_id
    WHERE (p_city IS NULL OR cs.city = p_city)
      AND (p_state IS NULL OR cs.state = p_state)
      AND (p_min_price IS NULL OR l.price >= p_min_price)
      AND (p_max_price IS NULL OR l.price <= p_max_price)
      AND (p_min_bedrooms IS NULL OR l.bedrooms >= p_min_bedrooms)
      AND (
          p_amenity_name IS NULL
          OR EXISTS (
              SELECT 1
              FROM ListingAmenity AS la_filter
              JOIN Amenity AS a_filter ON la_filter.amenity_id = a_filter.amenity_id
              WHERE la_filter.listing_id = l.listing_id
                AND a_filter.amenity_name = p_amenity_name
          )
      )
    GROUP BY
        l.listing_id, l.title, cs.city, cs.state, ad.zip,
        l.bedrooms, l.bathrooms, l.square_feet, l.price
    ORDER BY l.price ASC, l.square_feet DESC
    LIMIT v_limit;
END$$

CREATE PROCEDURE sp_add_or_update_review (
    IN p_user_name VARCHAR(100),
    IN p_email VARCHAR(255),
    IN p_listing_id INT,
    IN p_rating INT,
    IN p_review_text TEXT
)
BEGIN
    IF p_rating < 1 OR p_rating > 5 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Rating must be between 1 and 5.';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM ApartmentListing
        WHERE listing_id = p_listing_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cannot review a listing that does not exist.';
    END IF;

    INSERT INTO AppUser (user_name, email)
    VALUES (p_user_name, p_email)
    ON DUPLICATE KEY UPDATE email = VALUES(email);

    INSERT INTO Review (user_name, listing_id, rating, review_text, review_time)
    VALUES (p_user_name, p_listing_id, p_rating, p_review_text, NOW())
    ON DUPLICATE KEY UPDATE
        rating = VALUES(rating),
        review_text = VALUES(review_text),
        review_time = VALUES(review_time);

    SELECT
        r.user_name,
        r.listing_id,
        r.rating,
        r.review_text,
        r.review_time
    FROM Review AS r
    WHERE r.user_name = p_user_name
      AND r.listing_id = p_listing_id;
END$$

CREATE PROCEDURE sp_save_listing (
    IN p_user_name VARCHAR(100),
    IN p_email VARCHAR(255),
    IN p_listing_id INT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM ApartmentListing
        WHERE listing_id = p_listing_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cannot save a listing that does not exist.';
    END IF;

    INSERT INTO AppUser (user_name, email)
    VALUES (p_user_name, p_email)
    ON DUPLICATE KEY UPDATE email = VALUES(email);

    INSERT INTO SavedListing (user_name, listing_id, saved_at)
    VALUES (p_user_name, p_listing_id, NOW())
    ON DUPLICATE KEY UPDATE saved_at = VALUES(saved_at);

    SELECT
        s.user_name,
        s.listing_id,
        s.saved_at
    FROM SavedListing AS s
    WHERE s.user_name = p_user_name
      AND s.listing_id = p_listing_id;
END$$

CREATE PROCEDURE sp_remove_saved_listing (
    IN p_user_name VARCHAR(100),
    IN p_listing_id INT
)
BEGIN
    DELETE FROM SavedListing
    WHERE user_name = p_user_name
      AND listing_id = p_listing_id;

    SELECT
        p_user_name AS user_name,
        p_listing_id AS listing_id,
        ROW_COUNT() AS rows_removed;
END$$

CREATE PROCEDURE sp_update_listing_price (
    IN p_listing_id INT,
    IN p_new_price DECIMAL(10,2)
)
BEGIN
    IF p_new_price < 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Listing price cannot be negative.';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM ApartmentListing
        WHERE listing_id = p_listing_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cannot update a listing that does not exist.';
    END IF;

    UPDATE ApartmentListing
    SET price = p_new_price
    WHERE listing_id = p_listing_id;

    SELECT
        listing_id,
        title,
        price
    FROM ApartmentListing
    WHERE listing_id = p_listing_id;
END$$

DELIMITER ;

-- Demo calls for copied results/screenshots:
CALL sp_search_listings('Raleigh', 'NC', 900, 1800, 2, NULL, 10);
CALL sp_add_or_update_review('taylor', 'taylor@example.com', 1, 5, 'Great listing for the search criteria.');
CALL sp_save_listing('taylor', 'taylor@example.com', 22);
CALL sp_remove_saved_listing('taylor', 22);
CALL sp_update_listing_price(1, 2195.00);

