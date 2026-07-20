CREATE TABLE CityState (
    city_state_id INT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state CHAR(2) NOT NULL,
    PRIMARY KEY (city_state_id),
    UNIQUE (city, state)
);

CREATE TABLE ZipCodeDemographics (
    zip CHAR(5) NOT NULL,
    population INT NOT NULL DEFAULT 0,
    latitude DECIMAL(9,6) NOT NULL DEFAULT 0,
    longitude DECIMAL(9,6) NOT NULL DEFAULT 0,
    PRIMARY KEY (zip),
    CHECK (population >= 0)
);

CREATE TABLE Address (
    address_id INT NOT NULL,
    street_number VARCHAR(50) NOT NULL,
    street_name VARCHAR(255) NOT NULL,
    zip CHAR(5) NOT NULL,
    city_state_id INT NOT NULL,
    PRIMARY KEY (address_id),
    UNIQUE (street_number, street_name, zip, city_state_id),
    FOREIGN KEY (zip) REFERENCES ZipCodeDemographics(zip),
    FOREIGN KEY (city_state_id) REFERENCES CityState(city_state_id)
);

CREATE TABLE ApartmentListing (
    listing_id INT NOT NULL,
    address_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    bedrooms INT NOT NULL DEFAULT 0,
    price DECIMAL(10,2) NOT NULL DEFAULT 0,
    bathrooms DECIMAL(4,1) NOT NULL DEFAULT 0,
    square_feet INT NOT NULL DEFAULT 0,
    listing_time DATETIME NOT NULL,
    latitude DECIMAL(9,6) NOT NULL DEFAULT 0,
    longitude DECIMAL(9,6) NOT NULL DEFAULT 0,
    PRIMARY KEY (listing_id),
    FOREIGN KEY (address_id) REFERENCES Address(address_id),
    CHECK (bedrooms >= 0),
    CHECK (price >= 0),
    CHECK (bathrooms >= 0),
    CHECK (square_feet >= 0)
);

CREATE TABLE Amenity (
    amenity_id INT NOT NULL,
    amenity_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (amenity_id),
    UNIQUE (amenity_name)
);

CREATE TABLE ListingAmenity (
    listing_id INT NOT NULL,
    amenity_id INT NOT NULL,
    PRIMARY KEY (listing_id, amenity_id),
    FOREIGN KEY (listing_id) REFERENCES ApartmentListing(listing_id),
    FOREIGN KEY (amenity_id) REFERENCES Amenity(amenity_id)
);

CREATE TABLE AppUser (
    user_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    PRIMARY KEY (user_name),
    UNIQUE (email)
);

CREATE TABLE Review (
    user_name VARCHAR(100) NOT NULL,
    listing_id INT NOT NULL,
    rating INT NOT NULL,
    review_text TEXT,
    review_time DATETIME NOT NULL,
    PRIMARY KEY (user_name, listing_id),
    FOREIGN KEY (user_name) REFERENCES AppUser(user_name),
    FOREIGN KEY (listing_id) REFERENCES ApartmentListing(listing_id),
    CHECK (rating BETWEEN 1 AND 5)
);

CREATE TABLE SavedListing (
    user_name VARCHAR(100) NOT NULL,
    listing_id INT NOT NULL,
    saved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_name, listing_id),
    FOREIGN KEY (user_name) REFERENCES AppUser(user_name),
    FOREIGN KEY (listing_id) REFERENCES ApartmentListing(listing_id)
);
