-- Checkpoint 4 performance indexes.
-- Run this only after recording the baseline performance from Checkpoint 3.

CREATE INDEX idx_listingamenity_amenity_listing
ON ListingAmenity (amenity_id, listing_id);

CREATE INDEX idx_listing_address_price_bedrooms_sqft
ON ApartmentListing (address_id, price, bedrooms, square_feet);

CREATE INDEX idx_listing_price_address_sqft
ON ApartmentListing (price, address_id, square_feet);

CREATE INDEX idx_listing_cover_lookup
ON ApartmentListing (listing_id, address_id, price, title);
