
import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()

class DatabaseUtil:

    def __init__(self, db_config):
        self.db_config = db_config

        try:
            self.connection = mysql.connector.connect(**db_config)

            print("Connected to MySQL successfully")

        except Exception as e:
            print(f"Error connecting to the database: {e}")
            self.connection = None


    # ========================================================
    # GET DATABASE SCHEMA DETAILS
    # ========================================================

    def schema_details(self, schema_name):

        schema_info_context = ""

        connection = self.connection
        cursor = None

        if not connection or not connection.is_connected():
            return "Database connection is not available."

        try:

            cursor = connection.cursor()

            schema_info_context = f"Database Schema: {schema_name}\n"

            # Get all tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_type = 'BASE TABLE';
            """, (schema_name,))

            tables_list = cursor.fetchall()

            for table in tables_list:

                table_name = table[0]

                schema_info_context += f"\nTable: {table_name}\n"

                # Get columns and data types
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = %s
                    AND table_name = %s;
                """, (schema_name, table_name))

                columns_list = cursor.fetchall()

                for column in columns_list:

                    column_name = column[0]
                    data_type = column[1]

                    schema_info_context += (
                        f"  Column: {column_name}, "
                        f"Data Type: {data_type}\n"
                    )

                # Get sample data
                cursor.execute(
                    f"SELECT * FROM `{table_name}` LIMIT 5;"
                )

                sample_data = cursor.fetchall()

                schema_info_context += "  Sample Data:\n"

                for row in sample_data:

                    schema_info_context += f"    {row}\n"

        except Exception as e:

            print(f"Error fetching schema details: {e}")

            schema_info_context = (
                f"Error fetching schema details: {e}"
            )

        finally:

            if cursor:
                cursor.close()

            if connection and connection.is_connected():
                connection.close()

        return schema_info_context


    # ========================================================
    # EXECUTE SQL QUERY
    # ========================================================

    def execute_sql(self, query):

        connection = None
        cursor = None

        try:

            connection = mysql.connector.connect(**self.db_config)

            cursor = connection.cursor()

            cursor.execute(query)

            # Fetch results only for queries that return rows
            if cursor.with_rows:
                result = cursor.fetchall()
            else:
                result = f"{cursor.rowcount} rows affected"

            connection.commit()

            return str(result)

        except Exception as e:

            print(f"Error executing query: {e}")

            if connection and connection.is_connected():
                connection.rollback()

            return None

        finally:

            if cursor:
                cursor.close()

            if connection and connection.is_connected():
                connection.close()


# ============================================================
# CREATE DATABASE UTIL OBJECT
# ============================================================

obj = DatabaseUtil({
    "host": os.getenv("host"),
    "port": os.getenv("port"),
    "user": os.getenv("user"),
    "password": os.getenv("password"),
    "database": os.getenv("database")
})


# ============================================================
# GET SCHEMA DETAILS
# ============================================================

result = obj.schema_details("ola_rides")


# ============================================================
# SAVE SCHEMA DETAILS
# ============================================================

with open("test_schema_details.txt", "w") as f:
    f.write(result)

print("Schema details saved successfully!")
