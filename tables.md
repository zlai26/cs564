# Tables

CityState(city_state_id, city, state)

- Primary key: city_state_id
- Candidate keys: city_state_id; (city, state)
- Foreign keys: none

ZipCodeDemographics(zip, population, latitude, longitude)

- Primary key: zip
- Candidate keys: zip
- Foreign keys: none

Address(address_id, street_number, street_name, zip, city_state_id)

- Primary key: address_id
- Candidate keys: address_id; (street_number, street_name, zip, city_state_id)
- Foreign keys: zip references ZipCodeDemographics(zip); city_state_id references CityState(city_state_id)

ApartmentListing(listing_id, address_id, title, description, bedrooms, price, bathrooms, square_feet, listing_time, latitude, longitude)

- Primary key: listing_id
- Candidate keys: listing_id
- Foreign keys: address_id references Address(address_id)

Amenity(amenity_id, amenity_name)

- Primary key: amenity_id
- Candidate keys: amenity_id; amenity_name
- Foreign keys: none

ListingAmenity(listing_id, amenity_id)

- Primary key: (listing_id, amenity_id)
- Candidate keys: (listing_id, amenity_id)
- Foreign keys: listing_id references ApartmentListing(listing_id); amenity_id references Amenity(amenity_id)
- Bridge table for the many-to-many relationship between ApartmentListing and Amenity

AppUser(user_name, email)

- Primary key: user_name
- Candidate keys: user_name; email
- Foreign keys: none

Review(user_name, listing_id, rating, review_text, review_time)

- Primary key: (user_name, listing_id)
- Candidate keys: (user_name, listing_id)
- Foreign keys: user_name references AppUser(user_name); listing_id references ApartmentListing(listing_id)

SavedListing(user_name, listing_id)

- Primary key: (user_name, listing_id)
- Candidate keys: (user_name, listing_id)
- Foreign keys: user_name references AppUser(user_name); listing_id references ApartmentListing(listing_id)
- Bridge table for the many-to-many relationship between AppUser and ApartmentListing
