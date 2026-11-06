CREATE TABLE url_table (
    id SERIAL PRIMARY KEY,
    short_code VARCHAR(10) UNIQUE NOT NULL,
    url TEXT NOT NULL
);