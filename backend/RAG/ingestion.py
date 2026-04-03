import os
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
import psycopg2
from datetime import datetime

# ----------------------------
# Paths & DB configs
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "../statistics/reviews_churn_added.csv")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

PG_HOST = "localhost"
PG_DB = "customer_reviews"
PG_USER = "admin"
PG_PASS = "7777"

# ----------------------------
# Load CSV
# ----------------------------
df = pd.read_csv(CSV_FILE)

# Ensure date column is proper
def parse_date(raw):
    try:
        return pd.to_datetime(raw).date()
    except:
        return None

df['date'] = df['date_raw'].apply(parse_date)

# Convert is_business to boolean
def parse_boolean(val):
    if pd.isna(val):
        return False
    if isinstance(val, bool):
        return val
    return str(val).lower() in ['true', '1', 'yes']

df['is_business'] = df.get('is_business', False).apply(parse_boolean)

# Fill missing churn_score with 0
df['churn_score'] = df.get('churn_score', 0).fillna(0)

# ----------------------------
# Initialize embedding model
# ----------------------------
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# ----------------------------
# Initialize Chroma
# ----------------------------
import shutil
if os.path.exists(CHROMA_PATH):
    shutil.rmtree(CHROMA_PATH)
    print("Chroma DB folder deleted for fresh ingestion.")

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.create_collection(name="churn_reviews")
print("New Chroma collection created.")

# ----------------------------
# Connect to PostgreSQL
# ----------------------------
conn = psycopg2.connect(host=PG_HOST, dbname=PG_DB, user=PG_USER, password=PG_PASS)
cursor = conn.cursor()

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

# Truncate table to refresh data
cursor.execute("TRUNCATE TABLE trustpilot RESTART IDENTITY")
conn.commit()
print("Table truncated for fresh ingestion.")

# ----------------------------
# Ingest CSV into PostgreSQL & Chroma
# ----------------------------
for idx, row in df.iterrows():
    cursor.execute("""
        INSERT INTO trustpilot 
        (name, rating, title, body, date, date_raw, issue_list, is_business, churn_score, churn_risk_level)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        row.get('name'),
        row.get('rating'),
        row.get('title'),
        row.get('body'),
        row.get('date'),
        row.get('date_raw'),
        row.get('issue_list'),
        row.get('is_business'),
        row.get('churn_score'),
        row.get('churn_risk_level')
    ))
    # Ingest text into Chroma
    for col in ['title', 'body', 'issue_list']:
        if pd.isna(row[col]):
            continue
        text = f"{col}: {row[col]}"
        embedding = embed_model.encode([text])[0]
        collection.add(
            documents=[text],
            metadatas=[{"row_id": idx, "column": col, "rating": row['rating']}],
            ids=[f"{idx}_{col}"],
            embeddings=[embedding]
        )

conn.commit()
cursor.close()
conn.close()
print("Ingestion complete!")