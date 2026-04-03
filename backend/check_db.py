import psycopg2

# DB configs
PG_HOST = "localhost"
PG_DB = "customer_reviews"
PG_USER = "admin"
PG_PASS = "7777"

def check_db():
    try:
        conn = psycopg2.connect(host=PG_HOST, dbname=PG_DB, user=PG_USER, password=PG_PASS)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = cursor.fetchall()
        print("Tables in database:", [t[0] for t in tables])

        if 'trustpilot' in [t[0] for t in tables]:
            # Count rows
            cursor.execute("SELECT COUNT(*) FROM trustpilot")
            count = cursor.fetchone()[0]
            print(f"Number of rows in trustpilot table: {count}")

            if count > 0:
                # Show first few rows
                cursor.execute("SELECT id, name, rating, title FROM trustpilot LIMIT 5")
                rows = cursor.fetchall()
                print("First 5 rows:")
                for row in rows:
                    print(row)
        else:
            print("trustpilot table does not exist.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()