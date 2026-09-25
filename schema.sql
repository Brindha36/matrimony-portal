CREATE DATABASE IF NOT EXISTS matrimony_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE matrimony_system;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(50),
    profile_id VARCHAR(50),
    name VARCHAR(255),
    dob VARCHAR(100),
    star_rasi VARCHAR(255),
    height_complexion VARCHAR(255),
    education TEXT,
    job_and_company TEXT,
    salary VARCHAR(100),
    native_place VARCHAR(255),
    father_details TEXT,
    property_details TEXT,
    expectation TEXT,
    contact_person TEXT,
    phone_numbers VARCHAR(255),
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS uploads_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(50),
    filename VARCHAR(255),
    profiles_extracted INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Default login credentials: admin / admin123
INSERT IGNORE INTO users (username, password) 
VALUES ('admin', SHA2('admin123', 256));