-- Checkpoint 3 application tables and demo data.
-- Run this after the teammate schema in create_tables.sql and after importing
-- the six cleaned CSV tables with scripts\import_mysql_data.py.
--
-- This file preserves referential-integrity constraints. AppUser, Review, and
-- SavedListing are the application-side tables from the revised ER design.

CREATE TABLE IF NOT EXISTS AppUser (
    user_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    PRIMARY KEY (user_name),
    UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS Review (
    user_name VARCHAR(100) NOT NULL,
    listing_id INT NOT NULL,
    rating INT NOT NULL,
    review_text TEXT,
    review_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_name, listing_id),
    FOREIGN KEY (user_name) REFERENCES AppUser(user_name),
    FOREIGN KEY (listing_id) REFERENCES ApartmentListing(listing_id),
    CHECK (rating BETWEEN 1 AND 5)
);

CREATE TABLE IF NOT EXISTS SavedListing (
    user_name VARCHAR(100) NOT NULL,
    listing_id INT NOT NULL,
    saved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_name, listing_id),
    FOREIGN KEY (user_name) REFERENCES AppUser(user_name),
    FOREIGN KEY (listing_id) REFERENCES ApartmentListing(listing_id)
);

-- If SavedListing already exists from the older starter schema, add the
-- relationship attribute used by the revised ER design.
SET @saved_listing_needs_saved_at = (
    SELECT COUNT(*) = 0
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'SavedListing'
      AND COLUMN_NAME = 'saved_at'
);

SET @saved_listing_alter_sql = IF(
    @saved_listing_needs_saved_at,
    'ALTER TABLE SavedListing ADD COLUMN saved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP',
    'SELECT ''SavedListing.saved_at already exists'' AS status'
);

PREPARE saved_listing_alter_stmt FROM @saved_listing_alter_sql;
EXECUTE saved_listing_alter_stmt;
DEALLOCATE PREPARE saved_listing_alter_stmt;

INSERT INTO AppUser (user_name, email) VALUES
    ('alex', 'alex@example.com'),
    ('maya', 'maya@example.com'),
    ('jordan', 'jordan@example.com'),
    ('casey', 'casey@example.com'),
    ('sam', 'sam@example.com')
ON DUPLICATE KEY UPDATE email = VALUES(email);

INSERT INTO SavedListing (user_name, listing_id, saved_at) VALUES
    ('alex', 1, '2026-07-10 09:00:00'),
    ('alex', 22, '2026-07-11 10:30:00'),
    ('alex', 24, '2026-07-12 14:45:00'),
    ('maya', 2, '2026-07-10 11:00:00'),
    ('maya', 23, '2026-07-12 16:20:00'),
    ('jordan', 3, '2026-07-13 08:15:00'),
    ('casey', 4, '2026-07-14 13:10:00'),
    ('sam', 5, '2026-07-15 18:05:00')
ON DUPLICATE KEY UPDATE saved_at = VALUES(saved_at);

INSERT INTO Review (user_name, listing_id, rating, review_text, review_time) VALUES
    ('alex', 1, 4, 'Good value and clear listing details.', '2026-07-10 09:20:00'),
    ('maya', 2, 5, 'Large floor plan and useful location.', '2026-07-10 11:40:00'),
    ('jordan', 3, 4, 'Strong option for the price range.', '2026-07-13 08:40:00'),
    ('casey', 4, 3, 'Acceptable but smaller than expected.', '2026-07-14 13:30:00'),
    ('sam', 5, 4, 'Affordable one-bedroom listing.', '2026-07-15 18:30:00')
ON DUPLICATE KEY UPDATE
    rating = VALUES(rating),
    review_text = VALUES(review_text),
    review_time = VALUES(review_time);

