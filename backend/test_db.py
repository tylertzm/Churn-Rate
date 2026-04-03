import psycopg2
from datetime import datetime

# DB configs (same as ingestion.py)
PG_HOST = "localhost"
PG_DB = "customer_reviews"
PG_USER = "admin"
PG_PASS = "7777"

def test_db_operations():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(host=PG_HOST, dbname=PG_DB, user=PG_USER, password=PG_PASS)
        cursor = conn.cursor()
        print("Connected to database successfully.")

        # Create table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trustpilot (
            id SERIAL PRIMARY KEY,
            name TEXT,
            rating INT,
            title TEXT,
            body TEXT,
            date DATE,
            date_raw TEXT,
            issue_list TEXT,
            is_business BOOLEAN,
            churn_score NUMERIC,
            churn_risk_level TEXT
        )
        """)
        conn.commit()
        print("Table created or already exists.")

        # Insert a test row
        test_data = (
            "Test User",
            5,
            "Test Title",
            "Test Body",
            datetime.now().date(),
            "2023-01-01",
            "test issue",
            True,
            0.5,
            "low"
        )
        cursor.execute("""
            INSERT INTO trustpilot
            (name, rating, title, body, date, date_raw, issue_list, is_business, churn_score, churn_risk_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, test_data)
        inserted_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Inserted test row with ID: {inserted_id}")

        # Verify insertion
        cursor.execute("SELECT * FROM trustpilot WHERE id = %s", (inserted_id,))
        row = cursor.fetchone()
        if row:
            print("Row inserted successfully:", row)
        else:
            print("Row not found after insertion.")

        # Delete the test row
        cursor.execute("DELETE FROM trustpilot WHERE id = %s", (inserted_id,))
        conn.commit()
        print(f"Deleted row with ID: {inserted_id}")

        # Verify deletion
        cursor.execute("SELECT * FROM trustpilot WHERE id = %s", (inserted_id,))
        row = cursor.fetchone()
        if row:
            print("Row still exists after deletion:", row)
        else:
            print("Row deleted successfully.")

        cursor.close()
        conn.close()
        print("Database connection closed.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_db_operations()