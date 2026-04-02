import asyncio
import csv
import json
import os
import time
from datetime import datetime
from playwright.async_api import async_playwright
import dateparser

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://www.trustpilot.com/review/sumup.com?languages=en&date=last6months"
STATE_FILE = os.path.join(BASE_DIR, "scrape_state.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "reviews.csv")
CSV_HEADERS = ["name", "rating", "title", "body", "date", "date_raw"]

async def handle_cookies(page):
    """Wait for and accept the cookie banner if it appears."""
    try:
        accept_button = page.locator("#onetrust-accept-btn-handler")
        if await accept_button.is_visible(timeout=3000):
            await accept_button.click()
            print("Cookie banner accepted.")
    except:
        pass 

def parse_trustpilot_date(date_str, datetime_attr=None):
    """Parses date using ISO attribute or relative text."""
    if datetime_attr:
        return datetime.fromisoformat(datetime_attr.replace("Z", "+00:00"))
    return dateparser.parse(date_str)

async def scrape_reviews():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Robust State Loading: If empty or invalid, just scrape everything
        last_scraped_date = None
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    content = f.read().strip()
                    if content: # Only parse if file isn't empty
                        state = json.loads(content)
                        last_scraped_date = datetime.fromisoformat(state['last_date'])
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"State file issue ({e}). Starting fresh scrape.")
        
        all_new_reviews = []
        page_num = 1
        keep_scraping = True

        try:
            while keep_scraping:
                paged_url = f"{BASE_URL}&page={page_num}"
                print(f"Scraping Page {page_num}: {paged_url}")
                
                response = await page.goto(paged_url, wait_until="domcontentloaded")
                
                if response.status != 200:
                    print(f"Reached end of content (Status {response.status}).")
                    break

                await handle_cookies(page)

                container_selector = '#__next > div > div > main > div > div.styles_pageBackground__TWm9B > div.styles_pageWrapper__Vt_nX > div.styles_reviews__V5lTX > div > div > div.styles_mainContent__d9oos > section.styles_reviewListContainer__2bg_p'
                try:
                    await page.wait_for_selector(container_selector, timeout=10000)
                except:
                    print("Review list container not found. Ending.")
                    break

                container = page.locator(container_selector)
                review_elements = await container.locator('[data-service-review-card-paper="true"]').all()
                if not review_elements:
                    print("No reviews found in the container. Ending.")
                    break

                for el in review_elements:
                    # Extraction logic: use robust fallbacks
                    name_el = el.locator('span[data-consumer-name-typography="true"]')
                    name = await name_el.inner_text() if await name_el.count() > 0 else "Anonymous"

                    rating_img = el.locator('img[class*="StarRating_starRating"]')
                    rating_alt = await rating_img.get_attribute("alt") if await rating_img.count() > 0 else ""
                    rating = rating_alt.split(" ")[1] if " " in rating_alt else "N/A"

                    # Title can have different typography names
                    title_el = el.locator('h2[data-service-review-title-typography="true"]')
                    if await title_el.count() == 0:
                        title_el = el.locator('h2[data-review-title-typography="true"]')
                    title = await title_el.inner_text() if await title_el.count() > 0 else ""

                    see_more = el.locator('button:has-text("See more"), span:has-text("See more")')
                    if await see_more.count() > 0 and await see_more.is_visible():
                        try:
                            await see_more.click(timeout=1000)
                            await asyncio.sleep(0.5) 
                        except: pass

                    # Body can have different typography names
                    body_el = el.locator('p[data-service-review-text-typography="true"]')
                    if await body_el.count() == 0:
                        body_el = el.locator('p[data-relevant-review-text-typography="true"]')
                    if await body_el.count() == 0:
                        body_el = el.locator('p[data-service-review-content-typography="true"]')
                    body = await body_el.inner_text() if await body_el.count() > 0 else ""

                    time_el = el.locator('time')
                    date_text = await time_el.first.inner_text() if await time_el.count() > 0 else "Unknown"
                    datetime_attr = await time_el.first.get_attribute('datetime')
                    review_date = parse_trustpilot_date(date_text, datetime_attr)

                    # Incremental check
                    if last_scraped_date and review_date and review_date <= last_scraped_date:
                        print(f"Reached previously scraped data ({review_date}). Stopping.")
                        keep_scraping = False
                        break

                    all_new_reviews.append({
                        "name": name.strip(),
                        "rating": rating,
                        "title": title.strip(),
                        "body": body.strip(),
                        "date": review_date.isoformat() if review_date else None,
                        "date_raw": date_text
                    })

                # Incrementally save results after each page
                if all_new_reviews:
                    file_exists = os.path.exists(OUTPUT_FILE)
                    with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                        if not file_exists:
                            writer.writeheader()
                        writer.writerows(all_new_reviews)
                    
                    # Update state with the newest date found so far
                    valid_dates = [datetime.fromisoformat(r['date']) for r in all_new_reviews if r.get('date')]
                    if valid_dates:
                        newest_date = max(valid_dates)
                        with open(STATE_FILE, 'w') as f:
                            json.dump({"last_date": newest_date.isoformat()}, f)
                    
                    print(f"Page {page_num-1} saved with {len(all_new_reviews)} reviews.")
                    all_new_reviews = [] # Clear for next page
                
                if not keep_scraping:
                    break

                page_num += 1
                await asyncio.sleep(1.5)
        finally:
            print("Cycle finished.")
            await browser.close()

async def run():
    print(f"\n[{datetime.now()}] Starting modular scrape cycle...")
    try:
        await scrape_reviews()
        print("Scrape cycle complete.")
    except Exception as e:
        print(f"Scrape cycle failed: {e}")

if __name__ == "__main__":
    asyncio.run(run())