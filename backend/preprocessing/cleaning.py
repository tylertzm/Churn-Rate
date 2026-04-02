import csv
import string
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Note: Input is in scraping/trustpilot/ but our cleaning.py is in preprocessing/
# So we go up one level then into scraping/
INPUT_FILE = os.path.join(BASE_DIR, "..", "scraping", "trustpilot", "reviews.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "..", "scraping", "trustpilot", "reviews_clean.csv")

def run():
    # Remove punctuation except commas
    punctuation_to_remove = string.punctuation.replace(",", "")
    translator = str.maketrans("", "", punctuation_to_remove)

    TITLE_COL = 2
    BODY_COL = 3

    merged_rows = []

    if not os.path.exists(INPUT_FILE):
        print(f"File not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        current_row = None
        for line in f:
            line = line.rstrip("\n")  # remove line break
            
            # Split on commas, naive approach to detect start of a row
            parts = line.split(",", 2)
            if len(parts) >= 3 and parts[1].isdigit():
                if current_row:
                    merged_rows.append(current_row)
                current_row = line
            else:
                if current_row:
                    current_row += " " + line
                else:
                    current_row = line
        if current_row:
            merged_rows.append(current_row)

    # Now parse merged rows as CSV and clean title/body
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as out_csv:
        writer = csv.writer(out_csv, quoting=csv.QUOTE_ALL)
        
        for row_str in merged_rows:
            reader = csv.reader([row_str], quotechar='"')
            for row in reader:
                if len(row) > TITLE_COL:
                    row[TITLE_COL] = row[TITLE_COL].translate(translator)
                if len(row) > BODY_COL:
                    row[BODY_COL] = row[BODY_COL].translate(translator)
                writer.writerow(row)
    print("Normalizing reviews complete.")

if __name__ == "__main__":
    run()