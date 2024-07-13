-- Drop tables in the correct order
DROP TABLE IF EXISTS comment_sentiments;
DROP TABLE IF EXISTS similar_launches;
DROP TABLE IF EXISTS similar_cars;
DROP TABLE IF EXISTS car_sales;
DROP TABLE IF EXISTS unclassified_car_sales;
DROP TABLE IF EXISTS car_articles;
DROP TABLE IF EXISTS article_sections;
DROP TABLE IF EXISTS articles;
DROP TABLE IF EXISTS car_prices;
DROP TABLE IF EXISTS sales_reports;
DROP TABLE IF EXISTS cars;
DROP TABLE IF EXISTS launches;
DROP TABLE IF EXISTS page_comments;
DROP TABLE IF EXISTS pages;

-- Create tables
CREATE TABLE pages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    url VARCHAR(2048),
    image_url VARCHAR(2048),
    title VARCHAR(255),
    type VARCHAR(50),
    html_content MEDIUMTEXT,
    html_comments MEDIUMTEXT,
    date_published DATE,
    date_scraped DATETIME DEFAULT CURRENT_TIMESTAMP,
    date_parsed DATETIME DEFAULT NULL,
    date_comments_processed DATETIME DEFAULT NULL
);

CREATE TABLE page_comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    page_id INT,
    commenter_name VARCHAR(255),
    date_commented DATETIME,
    comment TEXT,
    reply_to_id INT DEFAULT NULL,
    sentiment VARCHAR(50) DEFAULT NULL,
    date_processed DATETIME DEFAULT NULL,
    FOREIGN KEY (page_id) REFERENCES pages(id)
);

CREATE TABLE launches (
    id INT PRIMARY KEY AUTO_INCREMENT,
    page_id INT,
    title VARCHAR(255),
    content MEDIUMTEXT,
    date_parsed DATETIME DEFAULT NULL,
    date_processed DATETIME DEFAULT NULL,
    FOREIGN KEY (id_page) REFERENCES pages(id)
);

CREATE TABLE similar_launches (
    id INT PRIMARY KEY AUTO_INCREMENT,
    launch_id INT,
    url VARCHAR(2048),
    FOREIGN KEY (launch_id) REFERENCES launches(id)
);

CREATE TABLE cars (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `launch_id` INT NOT NULL,
    `launch_price` INT,
    `current_price` INT,
    `price_date` DATETIME,
    `seller_name` VARCHAR(255),
    `make` VARCHAR(255),
    `model` VARCHAR(255),
    `variant` VARCHAR(255),
    `body_type` VARCHAR(50),
    `origin_country` VARCHAR(100),
    `engine_type` VARCHAR(50),
    `power` INT,
    `torque` INT,
    `num_cylinders` INT,
    `num_valves` INT,
    `battery_capacity` DECIMAL(5,2),
    `range` INT,
    `transmission_type` VARCHAR(50),
    `num_gears` INT,
    `length` INT,
    `width` INT,
    `height` INT,
    `trunk_capacity` INT,
    `maximum_capacity` INT,
    `fuel_capacity` INT,
    `ground_clearance` INT,
    `wheelbase` INT,
    `acceleration_0_100` DECIMAL(5,2),
    `max_speed` INT,
    `fuel_consumption` DECIMAL(5,2),
    `front_suspension` VARCHAR(100),
    `rear_suspension` VARCHAR(100),
    `front_brakes` VARCHAR(100),
    `rear_brakes` VARCHAR(100),
    `traction` VARCHAR(50),
    `weight` INT,
    `comfort_has_leather_seats` BOOLEAN DEFAULT FALSE,
    `comfort_has_auto_climate_control` BOOLEAN DEFAULT FALSE,
    `comfort_has_interior_ambient_lighting` BOOLEAN DEFAULT FALSE,
    `comfort_has_multimedia_system` BOOLEAN DEFAULT FALSE,
    `comfort_multimedia_system_screen_size` DECIMAL(5,2),
    `comfort_has_apple_carplay` BOOLEAN DEFAULT FALSE,
    `safety_num_airbags` INT,
    `safety_has_abs_brakes` BOOLEAN DEFAULT FALSE,
    `safety_has_lane_keeping_assist` BOOLEAN DEFAULT FALSE,
    `safety_has_forward_collision_warning` BOOLEAN DEFAULT FALSE,
    `safety_has_auto_emergency_brake` BOOLEAN DEFAULT FALSE,
    `safety_has_auto_high_beams` BOOLEAN DEFAULT FALSE,
    `safety_has_auto_drowsiness_detection` BOOLEAN DEFAULT FALSE,
    `safety_has_blind_spot_monitor` BOOLEAN DEFAULT FALSE,
    `safety_ncap_rating` INT,
    `features_has_front_camera` BOOLEAN DEFAULT FALSE,
    `features_has_rear_camera` BOOLEAN DEFAULT FALSE,
    `features_has_360_camera` BOOLEAN DEFAULT FALSE,
    `features_has_front_parking_sensors` BOOLEAN DEFAULT FALSE,
    `features_has_rear_parking_sensors` BOOLEAN DEFAULT FALSE,
    `features_has_parking_assist` BOOLEAN DEFAULT FALSE,
    `features_has_digital_instrument_cluster` BOOLEAN DEFAULT FALSE,
    `features_has_cruise_control` BOOLEAN DEFAULT FALSE,
    `features_has_adaptive_cruise_control` BOOLEAN DEFAULT FALSE,
    `features_has_tpms` BOOLEAN DEFAULT FALSE,
    `features_has_led_headlights` BOOLEAN DEFAULT FALSE,
    `features_has_engine_ignition_button` BOOLEAN DEFAULT FALSE,
    `features_has_keyless_entry` BOOLEAN DEFAULT FALSE,
    `features_has_sunroof` BOOLEAN DEFAULT FALSE,
    `features_num_speakers` INT,
    `warranty_years` INT,
    `warranty_kms` INT,
    FOREIGN KEY (launch_id) REFERENCES launches(id)
);

CREATE TABLE similar_cars (
    launch_car_id INT,
    similar_car_id INT,
    PRIMARY KEY (launch_car_id, similar_car_id),
    FOREIGN KEY (launch_car_id) REFERENCES cars(id),
    FOREIGN KEY (similar_car_id) REFERENCES cars(id)
);

CREATE TABLE car_prices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    launch_url VARCHAR(2048) NOT NULL,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2),
    date_parsed DATETIME DEFAULT CURRENT_TIMESTAMP,
    date_processed DATETIME DEFAULT NULL,
    process_result VARCHAR(50) DEFAULT NULL
);

CREATE TABLE sales_reports (
    id INT PRIMARY KEY AUTO_INCREMENT,
    page_id INT NOT NULL,
    year INT,
    month INT,
    type ENUM("yearly", "monthly"),
    date_processed DATETIME,
    FOREIGN KEY (page_id) REFERENCES pages(id)
);

CREATE TABLE car_sales (
    sales_report_id INT,
    car_id INT,
    units INT,
    PRIMARY KEY (car_id, sales_report_id),
    FOREIGN KEY (car_id) REFERENCES cars(id),
    FOREIGN KEY (sales_report_id) REFERENCES sales_reports(id)
);

CREATE TABLE unclassified_car_sales (
    sales_report_id INT,
    model VARCHAR(255),
    units INT,
    PRIMARY KEY (model, sales_report_id),
    FOREIGN KEY (sales_report_id) REFERENCES sales_reports(id)
);

CREATE TABLE `articles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `page_id` int DEFAULT NULL,
  `related_launch_url` VARCHAR(2048),
  `title` varchar(255) DEFAULT NULL,
  `type` varchar(50) DEFAULT NULL,
  `content` mediumtext,
  `summary` text,
  `sentiment` varchar(50) DEFAULT NULL,
  `sentiment_score` float DEFAULT NULL,
  `sentiment_evidence` text,
  `sentiment_emotions` text,
  `comments_sentiment` varchar(50) DEFAULT NULL,
  `comments_summary` text,
  `date_parsed` datetime DEFAULT NULL,
  `date_processed` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `page_id` (`page_id`),
  CONSTRAINT `articles_ibfk_1` FOREIGN KEY (`page_id`) REFERENCES `pages` (`id`)
) ENGINE=InnoDB;


CREATE TABLE `article_sections` (
  `id` int NOT NULL AUTO_INCREMENT,
  `article_id` int DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `content` text,
  `summary` text,
  `sentiment` varchar(50) DEFAULT NULL,
  `sentiment_score` float DEFAULT NULL,
  `sentiment_evidence` text,
  `sentiment_emotions` text,
  `date_parsed` datetime DEFAULT NULL,
  `date_processed` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `article_id` (`article_id`),
  CONSTRAINT `article_sections_ibfk_1` FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`)
) ENGINE=InnoDB;


CREATE TABLE car_articles (
    car_id INT,
    article_id INT,
    PRIMARY KEY (car_id, article_id),
    FOREIGN KEY (car_id) REFERENCES cars(id),
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

CREATE TABLE comment_sentiments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    page_id INT,
    attribute VARCHAR(255),
    sentiment_score FLOAT,
    sentiment_variance FLOAT,
    sentiment_evidence TEXT,
    FOREIGN KEY (page_id) REFERENCES pages(id)
);