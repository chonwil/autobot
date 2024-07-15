-- PostgreSQL dump

SET client_encoding = 'UTF8';

-- Drop tables in reverse order of dependencies
DROP TABLE IF EXISTS "unclassified_car_sales";
DROP TABLE IF EXISTS "similar_launches";
DROP TABLE IF EXISTS "similar_cars";
DROP TABLE IF EXISTS "car_sales";
DROP TABLE IF EXISTS "sales_reports";
DROP TABLE IF EXISTS "post_comments";
DROP TABLE IF EXISTS "comment_sentiments";
DROP TABLE IF EXISTS "car_articles";
DROP TABLE IF EXISTS "car_prices";
DROP TABLE IF EXISTS "cars";
DROP TABLE IF EXISTS "car_models";
DROP TABLE IF EXISTS "article_sections";
DROP TABLE IF EXISTS "articles";
DROP TABLE IF EXISTS "launches";
DROP TABLE IF EXISTS "posts";

--
-- Table structure for table "posts"
--

CREATE TABLE "posts" (
  "id" SERIAL PRIMARY KEY,
  "url" TEXT,
  "image_url" TEXT,
  "title" VARCHAR(255),
  "type" VARCHAR(50),
  "html_content" TEXT,
  "html_comments" TEXT,
  "date_published" DATE,
  "date_scraped" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "date_parsed" TIMESTAMP,
  "date_comments_processed" TIMESTAMP
);

--
-- Table structure for table "launches"
--

CREATE TABLE "launches" (
  "id" SERIAL PRIMARY KEY,
  "post_id" INTEGER,
  "car_model_id" INTEGER,
  "title" VARCHAR(255),
  "content" TEXT,
  "date_processed" TIMESTAMP,
  FOREIGN KEY ("post_id") REFERENCES "posts" ("id")
);

--
-- Table structure for table "articles"
--

CREATE TABLE "articles" (
  "id" SERIAL PRIMARY KEY,
  "post_id" INTEGER,
  "related_launch_url" TEXT,
  "title" VARCHAR(255),
  "type" VARCHAR(50),
  "content" TEXT,
  "summary" TEXT,
  "sentiment" VARCHAR(50),
  "sentiment_score" REAL,
  "sentiment_evidence" TEXT,
  "sentiment_emotions" TEXT,
  "comments_sentiment" VARCHAR(50),
  "comments_summary" TEXT,
  "date_processed" TIMESTAMP,
  FOREIGN KEY ("post_id") REFERENCES "posts" ("id")
);

--
-- Table structure for table "article_sections"
--

CREATE TABLE "article_sections" (
  "id" SERIAL PRIMARY KEY,
  "article_id" INTEGER,
  "title" VARCHAR(255),
  "content" TEXT,
  "summary" TEXT,
  "sentiment" VARCHAR(50),
  "sentiment_score" REAL,
  "sentiment_evidence" TEXT,
  "sentiment_emotions" TEXT,
  "date_processed" TIMESTAMP,
  FOREIGN KEY ("article_id") REFERENCES "articles" ("id")
);

--
-- Table structure for table "cars"
--

CREATE TABLE "car_models" (
  "id" SERIAL PRIMARY KEY,
  "make" VARCHAR(255),
  "model" VARCHAR(255)
);

--
-- Table structure for table "cars"
--

CREATE TABLE "cars" (
  "id" SERIAL PRIMARY KEY,
  "launch_id" INTEGER NOT NULL,
  "launch_price" INTEGER,
  "current_price" INTEGER,
  "price_date" TIMESTAMP,
  "seller_name" VARCHAR(255),
  "variant" VARCHAR(255),
  "full_model_name" VARCHAR(255),
  "body_type" VARCHAR(50),
  "origin_country" VARCHAR(100),
  "engine_type" VARCHAR(50),
  "power" INTEGER,
  "torque" INTEGER,
  "num_cylinders" INTEGER,
  "num_valves" INTEGER,
  "battery_capacity" DECIMAL(5,2),
  "range_kms" INTEGER,
  "transmission_type" VARCHAR(50),
  "num_gears" INTEGER,
  "length" INTEGER,
  "width" INTEGER,
  "height" INTEGER,
  "trunk_capacity" INTEGER,
  "maximum_capacity" INTEGER,
  "fuel_capacity" INTEGER,
  "ground_clearance" INTEGER,
  "wheelbase" INTEGER,
  "acceleration_0_100" DECIMAL(5,2),
  "max_speed" INTEGER,
  "fuel_consumption" DECIMAL(5,2),
  "front_suspension" VARCHAR(100),
  "rear_suspension" VARCHAR(100),
  "front_brakes" VARCHAR(100),
  "rear_brakes" VARCHAR(100),
  "traction" VARCHAR(50),
  "weight" INTEGER,
  "comfort_has_leather_seats" BOOLEAN DEFAULT FALSE,
  "comfort_has_auto_climate_control" BOOLEAN DEFAULT FALSE,
  "comfort_has_interior_ambient_lighting" BOOLEAN DEFAULT FALSE,
  "comfort_has_multimedia_system" BOOLEAN DEFAULT FALSE,
  "comfort_multimedia_system_screen_size" DECIMAL(5,2),
  "comfort_has_apple_carplay" BOOLEAN DEFAULT FALSE,
  "safety_num_airbags" INTEGER,
  "safety_has_abs_brakes" BOOLEAN DEFAULT FALSE,
  "safety_has_lane_keeping_assist" BOOLEAN DEFAULT FALSE,
  "safety_has_forward_collision_warning" BOOLEAN DEFAULT FALSE,
  "safety_has_auto_emergency_brake" BOOLEAN DEFAULT FALSE,
  "safety_has_auto_high_beams" BOOLEAN DEFAULT FALSE,
  "safety_has_auto_drowsiness_detection" BOOLEAN DEFAULT FALSE,
  "safety_has_blind_spot_monitor" BOOLEAN DEFAULT FALSE,
  "safety_ncap_rating" INTEGER,
  "features_has_front_camera" BOOLEAN DEFAULT FALSE,
  "features_has_rear_camera" BOOLEAN DEFAULT FALSE,
  "features_has_360_camera" BOOLEAN DEFAULT FALSE,
  "features_has_front_parking_sensors" BOOLEAN DEFAULT FALSE,
  "features_has_rear_parking_sensors" BOOLEAN DEFAULT FALSE,
  "features_has_parking_assist" BOOLEAN DEFAULT FALSE,
  "features_has_digital_instrument_cluster" BOOLEAN DEFAULT FALSE,
  "features_has_cruise_control" BOOLEAN DEFAULT FALSE,
  "features_has_adaptive_cruise_control" BOOLEAN DEFAULT FALSE,
  "features_has_tpms" BOOLEAN DEFAULT FALSE,
  "features_has_led_headlights" BOOLEAN DEFAULT FALSE,
  "features_has_engine_ignition_button" BOOLEAN DEFAULT FALSE,
  "features_has_keyless_entry" BOOLEAN DEFAULT FALSE,
  "features_has_sunroof" BOOLEAN DEFAULT FALSE,
  "features_num_speakers" INTEGER,
  "warranty_years" INTEGER,
  "warranty_kms" INTEGER,
  FOREIGN KEY ("launch_id") REFERENCES "launches" ("id")
);

--
-- Table structure for table "car_prices"
--

CREATE TABLE "car_prices" (
  "id" SERIAL PRIMARY KEY,
  "launch_url" TEXT NOT NULL,
  "name" VARCHAR(255) NOT NULL,
  "price" INTEGER,
  "date_processed" TIMESTAMP,
  "process_result" VARCHAR(50)
);

--
-- Table structure for table "car_articles"
--

CREATE TABLE "car_articles" (
  "car_id" INTEGER NOT NULL,
  "article_id" INTEGER NOT NULL,
  PRIMARY KEY ("car_id", "article_id"),
  FOREIGN KEY ("car_id") REFERENCES "cars" ("id"),
  FOREIGN KEY ("article_id") REFERENCES "articles" ("id")
);

--
-- Table structure for table "comment_sentiments"
--

CREATE TABLE "comment_sentiments" (
  "id" SERIAL PRIMARY KEY,
  "post_id" INTEGER,
  "attribute" VARCHAR(255),
  "sentiment_score" REAL,
  "sentiment_variance" REAL,
  "sentiment_evidence" TEXT,
  FOREIGN KEY ("post_id") REFERENCES "posts" ("id")
);

--
-- Table structure for table "post_comments"
--

CREATE TABLE "post_comments" (
  "id" SERIAL PRIMARY KEY,
  "post_id" INTEGER,
  "commenter_name" VARCHAR(255),
  "date_commented" TIMESTAMP,
  "comment" TEXT,
  "reply_to_id" INTEGER,
  "sentiment" VARCHAR(50),
  "date_processed" TIMESTAMP,
  FOREIGN KEY ("post_id") REFERENCES "posts" ("id")
);

--
-- Table structure for table "sales_reports"
--

CREATE TABLE "sales_reports" (
  "id" SERIAL PRIMARY KEY,
  "post_id" INTEGER NOT NULL,
  "year" INTEGER,
  "month" INTEGER,
  "type" VARCHAR(7) CHECK ("type" IN ('yearly', 'monthly')),
  "date_processed" TIMESTAMP,
  FOREIGN KEY ("post_id") REFERENCES "posts" ("id")
);

--
-- Table structure for table "car_sales"
--

CREATE TABLE "car_sales" (
  "sales_report_id" INTEGER NOT NULL,
  "car_model_id" INTEGER NOT NULL,
  "units" INTEGER,
  PRIMARY KEY ("car_model_id", "sales_report_id"),
  FOREIGN KEY ("car_model_id") REFERENCES "car_models" ("id"),
  FOREIGN KEY ("sales_report_id") REFERENCES "sales_reports" ("id")
);

--
-- Table structure for table "similar_cars"
--

CREATE TABLE "similar_cars" (
  "launch_car_id" INTEGER NOT NULL,
  "similar_car_id" INTEGER NOT NULL,
  PRIMARY KEY ("launch_car_id", "similar_car_id"),
  FOREIGN KEY ("launch_car_id") REFERENCES "cars" ("id"),
  FOREIGN KEY ("similar_car_id") REFERENCES "cars" ("id")
);

--
-- Table structure for table "similar_launches"
--

CREATE TABLE "similar_launches" (
  "id" SERIAL PRIMARY KEY,
  "launch_id" INTEGER NOT NULL,
  "full_model_name" VARCHAR(255),
  "url" TEXT,
  FOREIGN KEY ("launch_id") REFERENCES "launches" ("id")
);

--
-- Table structure for table "unclassified_car_sales"
--

CREATE TABLE "unclassified_car_sales" (
  "sales_report_id" INTEGER NOT NULL,
  "model" VARCHAR(255) NOT NULL,
  "units" INTEGER,
  PRIMARY KEY ("model", "sales_report_id"),
  FOREIGN KEY ("sales_report_id") REFERENCES "sales_reports" ("id")
);