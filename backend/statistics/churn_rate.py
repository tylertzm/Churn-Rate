import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Input is in ../scraping/trustpilot/
INPUT_FILE = os.path.join(BASE_DIR, "..", "scraping", "trustpilot", "reviews_clean.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "reviews_churn_added.csv")

def run():
    if not os.path.exists(INPUT_FILE):
        print(f"File not found: {INPUT_FILE}")
        return

    # 1. Load your dataset
    df = pd.read_csv(INPUT_FILE)
    df['date'] = pd.to_datetime(df['date'])

    # 2. Issue Mapping Configuration
    issue_map = {
        'Support failure': ['support', 'chat', 'phone', 'hung up', 'understanding', 'ignored', 'minutes', 'help'],
        'Account/Funds Blocked': ['block', 'frozen', 'thief', 'money', 'court', 'legal', 'review', '3000', 'hold'],
        'Technical/Hardware': ['iphone', 'mastercard', 'card reader', 'machine', 'connection', 'app', 'crash', 'prob', 'bluetooth'],
        'Pricing/Refunds': ['fee', 'charge', 'refund', 'expensive', 'cost', 'money back']
    }

    # 3. Enhanced Labeling Logic
    def analyze_review(row):
        text = (str(row['title']) + " " + str(row['body'])).lower()
        
        # Identify Issues
        issues = [issue for issue, keys in issue_map.items() if any(k in text for k in keys)]
        if not issues and row['rating'] <= 2:
            issues = ["General Dissatisfaction"]
        
        # Business Detection Logic
        name_str = str(row['name']).lower()
        is_biz = any(term in name_str for term in ['.com', 'ltd', 'limited', 'shop', 'inc', 'business', 'uk', 'thyme'])
        
        # Calculate Churn Score
        score = 60 if row['rating'] == 1 else (40 if row['rating'] == 2 else 0)
        if is_biz and score > 0: score += 10 
        
        return pd.Series([issues, is_biz, min(score, 100)])

    # Apply the logic
    df[['issue_list', 'is_business', 'churn_score']] = df.apply(analyze_review, axis=1)

    # 4. Filter for "At Risk" (Churners)
    churners = df[df['churn_score'] >= 60].copy()

    # --- FINAL INTEGRATED REPORT ---
    print("\n" + "="*40)
    print("🚀 INTEGRATED CHURN INTELLIGENCE REPORT")
    print("="*40)

    # Stat 1: Root Cause Volume (Exploded)
    exploded_issues = churners['issue_list'].explode()
    print("\n[1] TOTAL ISSUE VOLUME")
    print(exploded_issues.value_counts())

    # Stat 2: Business Impact
    biz_churners = churners[churners['is_business']].copy()
    print(f"\n[2] HIGH-VALUE BUSINESS RISK")
    print(f"Total Businesses at Risk: {len(biz_churners)}")

    # Stat 3: Velocity
    latest_day = df['date'].dt.date.max()
    print(f"\n[3] RECENT ACTIVITY")
    print(f"Latest Review Date: {latest_day}")
    print("="*40)

    # Save the full analysis set as the primary source of truth
    df['churn_risk_level'] = df['churn_score'].map(lambda s: 'CRITICAL (Immediate Action Needed)' if s >= 70 else ('HIGH RISK (Churn Likely)' if s >= 60 else ('MEDIUM RISK (Monitor)' if s >= 40 else 'LOW RISK (Healthy)')))
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Analysis saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run()