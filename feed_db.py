
import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": os.environ["host"],
    "port": int(os.getenv("port", "3306")),
    "database": os.environ["database"],
    "user": os.environ["user"],
    "password": os.environ["password"],
    "allow_local_infile": True,
}

CSV_DIR = "data"


# ============================================================
# DATABASE CONNECTION
# ============================================================

conn = None
cursor = None

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    conn.autocommit = False

    cursor = conn.cursor()

    print("Connected to MySQL")


    # ========================================================
    # CREATE TABLES
    # ========================================================

    create_tables_sql = [

        # USERS
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            phone VARCHAR(50),
            city VARCHAR(100),
            province VARCHAR(50),
            user_type VARCHAR(20) NOT NULL,
            signup_date DATE,
            is_active BOOLEAN
        ) ENGINE=InnoDB
        """,

        # VEHICLES
        """
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id INTEGER PRIMARY KEY,
            driver_id INTEGER NOT NULL,
            make VARCHAR(50),
            model VARCHAR(50),
            year INTEGER,
            license_plate VARCHAR(20) UNIQUE,
            color VARCHAR(30),
            is_active BOOLEAN,

            CONSTRAINT fk_vehicle_driver
                FOREIGN KEY (driver_id)
                REFERENCES users(user_id)
        ) ENGINE=InnoDB
        """,

        # RIDES
        """
        CREATE TABLE IF NOT EXISTS rides (
            ride_id INTEGER PRIMARY KEY,
            rider_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,

            requested_at TIMESTAMP,
            pickup_time TIMESTAMP,
            dropoff_time TIMESTAMP,

            pickup_latitude DECIMAL(9,6),
            pickup_longitude DECIMAL(9,6),

            dropoff_latitude DECIMAL(9,6),
            dropoff_longitude DECIMAL(9,6),

            distance_km DECIMAL(10,2),
            fare DECIMAL(10,2),
            surge_multiplier DECIMAL(4,2),

            status VARCHAR(30),
            cancellation_reason VARCHAR(100),

            CONSTRAINT fk_ride_rider
                FOREIGN KEY (rider_id)
                REFERENCES users(user_id),

            CONSTRAINT fk_ride_driver
                FOREIGN KEY (driver_id)
                REFERENCES users(user_id)
        ) ENGINE=InnoDB
        """,

        # PAYMENTS
        """
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,

            amount DECIMAL(10,2),

            payment_method VARCHAR(50),
            payment_status VARCHAR(30),

            transaction_id VARCHAR(100) UNIQUE,
            payment_time TIMESTAMP,

            CONSTRAINT fk_payment_ride
                FOREIGN KEY (ride_id)
                REFERENCES rides(ride_id),

            CONSTRAINT fk_payment_user
                FOREIGN KEY (user_id)
                REFERENCES users(user_id)
        ) ENGINE=InnoDB
        """,

        # RATINGS
        """
        CREATE TABLE IF NOT EXISTS ratings (
            rating_id INTEGER PRIMARY KEY,
            ride_id INTEGER NOT NULL,
            rider_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,

            rating INTEGER,
            comment TEXT,
            rated_at TIMESTAMP,

            CONSTRAINT fk_rating_ride
                FOREIGN KEY (ride_id)
                REFERENCES rides(ride_id),

            CONSTRAINT fk_rating_rider
                FOREIGN KEY (rider_id)
                REFERENCES users(user_id),

            CONSTRAINT fk_rating_driver
                FOREIGN KEY (driver_id)
                REFERENCES users(user_id),

            CONSTRAINT chk_rating
                CHECK (rating BETWEEN 1 AND 5)
        ) ENGINE=InnoDB
        """
    ]

    for query in create_tables_sql:
        cursor.execute(query)

    print("Tables created successfully")


    # ========================================================
    # CREATE INDEXES
    # ========================================================

    indexes = {
        "vehicles": [
            ("idx_vehicles_driver_id", "driver_id")
        ],

        "rides": [
            ("idx_rides_rider_id", "rider_id"),
            ("idx_rides_driver_id", "driver_id"),
            ("idx_rides_requested_at", "requested_at"),
            ("idx_rides_status", "status")
        ],

        "payments": [
            ("idx_payments_ride_id", "ride_id"),
            ("idx_payments_user_id", "user_id")
        ],

        "ratings": [
            ("idx_ratings_ride_id", "ride_id"),
            ("idx_ratings_driver_id", "driver_id")
        ]
    }

    for table, table_indexes in indexes.items():

        for index_name, column in table_indexes:

            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                AND table_name = %s
                AND index_name = %s
            """, (table, index_name))

            exists = cursor.fetchone()[0]

            if not exists:
                cursor.execute(
                    f"CREATE INDEX {index_name} "
                    f"ON {table} ({column})"
                )

    print("Indexes created successfully")


    # ========================================================
    # CLEAR EXISTING DATA
    # ========================================================

    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    tables = [
        "ratings",
        "payments",
        "rides",
        "vehicles",
        "users"
    ]

    for table in tables:
        cursor.execute(f"TRUNCATE TABLE {table}")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    print("Existing data cleared")


    # ========================================================
    # LOAD CSV USING MYSQL LOAD DATA LOCAL INFILE
    # ========================================================

    def load_csv(table_name, csv_file, columns):

        file_path = os.path.abspath(
            os.path.join(CSV_DIR, csv_file)
        )

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"CSV file not found: {file_path}"
            )

        # Escape the local file path for SQL
        escaped_path = (
            file_path
            .replace("\\", "\\\\")
            .replace("'", "\\'")
        )

        # Create temporary variables for CSV fields.
        # NULLIF converts empty CSV fields into SQL NULL.

        user_variables = [
            f"@v{i}" for i in range(len(columns))
        ]

        set_columns = ", ".join(
            f"{column} = NULLIF(@v{i}, '')"
            for i, column in enumerate(columns)
        )

        columns_sql = ", ".join(user_variables)

        copy_sql = f"""
            LOAD DATA LOCAL INFILE '{escaped_path}'
            INTO TABLE {table_name}
            FIELDS TERMINATED BY ','
            OPTIONALLY ENCLOSED BY '"'
            ESCAPED BY '\\\\'
            LINES TERMINATED BY '\\n'
            IGNORE 1 LINES
            ({columns_sql})
            SET {set_columns}
        """

        cursor.execute(copy_sql)

        print(
            f"Loaded {csv_file} "
            f"({cursor.rowcount} rows)"
        )


    # ========================================================
    # LOAD USERS
    # ========================================================

    load_csv(
        "users",
        "users.csv",
        [
            "user_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "city",
            "province",
            "user_type",
            "signup_date",
            "is_active",
        ],
    )


    # ========================================================
    # LOAD VEHICLES
    # ========================================================

    load_csv(
        "vehicles",
        "vehicles.csv",
        [
            "vehicle_id",
            "driver_id",
            "make",
            "model",
            "year",
            "license_plate",
            "color",
            "is_active",
        ],
    )


    # ========================================================
    # LOAD RIDES
    # ========================================================

    load_csv(
        "rides",
        "rides.csv",
        [
            "ride_id",
            "rider_id",
            "driver_id",
            "requested_at",
            "pickup_time",
            "dropoff_time",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "distance_km",
            "fare",
            "surge_multiplier",
            "status",
            "cancellation_reason",
        ],
    )


    # ========================================================
    # LOAD PAYMENTS
    # ========================================================

    load_csv(
        "payments",
        "payments.csv",
        [
            "payment_id",
            "ride_id",
            "user_id",
            "amount",
            "payment_method",
            "payment_status",
            "transaction_id",
            "payment_time",
        ],
    )


    # ========================================================
    # LOAD RATINGS
    # ========================================================

    load_csv(
        "ratings",
        "ratings.csv",
        [
            "rating_id",
            "ride_id",
            "rider_id",
            "driver_id",
            "rating",
            "comment",
            "rated_at",
        ],
    )


    # ========================================================
    # VERIFY RECORD COUNTS
    # ========================================================

    tables = [
        "users",
        "vehicles",
        "rides",
        "payments",
        "ratings",
    ]

    print("\nRecord counts:")
    print("-" * 40)

    for table in tables:

        cursor.execute(
            f"SELECT COUNT(*) FROM {table}"
        )

        count = cursor.fetchone()[0]

        print(f"{table:<15} {count:>10,}")


    # ========================================================
    # COMMIT
    # ========================================================

    conn.commit()

    print("\nData loaded successfully!")
    print("Transaction committed.")


except (Error, Exception) as e:

    if conn and conn.is_connected():
        conn.rollback()

    print(f"\nError occurred: {e}")
    raise


finally:

    if cursor:
        cursor.close()

    if conn and conn.is_connected():
        conn.close()

    print("MySQL connection closed.")
