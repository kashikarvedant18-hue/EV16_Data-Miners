from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)

data_rows = []
logging.info("ESWD scraping started")

# Initialize Selenium WebDriver
options = webdriver.ChromeOptions()
# options.add_argument('--headless=new')  # Disabled for testing
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

events = {"safe":["Avalanche", "Funnel", "Gustnado","Devil", "Ice", "Snow"],
          "unsafe":["Hail", "Wind", "Lightning", "Tornado", "Precip"]}

for key in events:
    if key == "unsafe":
        r=2
    else:
        r=1
    
    for event in events[key]:
        logging.info(f"Starting event type: {event}")
        for i in range(2000, 2001):
            logging.info(f" Year: {i}")
            syear = str(i)
            eyear = str(i)

            if r == 1:
                mrange = 13
                multiplier = 1
            else:
                mrange = 2
                multiplier = 6

            for j in range(1, mrange):
                smonth = str(j).zfill(2)
                emonth = str(j + 1).zfill(2) if j < 12 else "01"
                logging.info(f"  Month: {smonth}")
                
                if j == 12:
                    eyear = str(i + 1)
                if emonth == "02":
                    edate = "28"
                elif emonth in ["04", "06", "09", "11"]:
                    edate = "30"
                else:
                    edate = "31"
                
                url = "https://eswd.eu/en?filter={\"startCoordinates\":{},\"endCoordinates\":{},\"time\":{\"startDateTime\":\"" + syear + "-" + str(int(smonth)*multiplier).zfill(2) + "-01T00:00:00.000Z\",\"endDateTime\":\"" + eyear + "-" + str(int(emonth)*multiplier).zfill(2) + "-" + edate + "T00:00:00.000Z\"},\"qualityLevels\":[],\"eventTypes\":[\""+ event +"\"],\"countries\":[],\"advancedFilters\":[],\"includeDeleted\":false}"

                logging.info(f"   Requesting ESWD | Event={event} | {syear}-{smonth}")

                driver.get(url)
                time.sleep(5)  # Wait for page to fully load
                
                # Debug: Check what buttons are available
                buttons = driver.find_elements(By.TAG_NAME, "button")
                logging.info(f"   Found {len(buttons)} buttons on page")
                for idx, btn in enumerate(buttons[:5]):  # Check first 5 buttons
                    try:
                        btn_text = btn.text or btn.get_attribute("class") or f"button_{idx}"
                        logging.info(f"   Button {idx}: {btn_text}")
                    except:
                        pass
                
                # Try to click search button with JavaScript
                try:
                    search_btn = driver.find_element(By.CSS_SELECTOR, "button.btn--action.btn--s")
                    logging.info(f"   Search button found, text: {search_btn.text}")
                    
                    # Scroll to button and ensure it's visible
                    driver.execute_script("arguments[0].scrollIntoView(true);", search_btn)
                    time.sleep(1)
                    
                    # Try clicking
                    driver.execute_script("arguments[0].click();", search_btn)
                    logging.info(f"   Clicked search button")
                    time.sleep(5)  # Wait longer after click
                    
                    # Check for loading indicators or event list
                    event_list = driver.find_elements(By.CSS_SELECTOR, "div.event-list, ul.event-list, div[class*='event']")
                    logging.info(f"   Found {len(event_list)} event-related divs")
                    
                    # Wait for event cards to load
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.event-card"))
                    )
                    logging.info(f"   Event cards loaded!")
                    time.sleep(2)  # Extra time for all cards to render
                except Exception as e:
                    logging.info(f"   Error: {str(e)[:200]}")
                    # Save page source for debugging
                    with open(f"debug_page_{event}_{smonth}.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    logging.info(f"   Saved page source to debug file")
                    time.sleep(2)
                
                soup = BeautifulSoup(driver.page_source, "html.parser")
                event_cards = soup.select("div.event-card")
                logging.info(f"   Found {len(event_cards)} event cards")

                for card in event_cards:
                    row = {}
                    
                    try:
                        row["event_type"] = card.select_one("p.event-card__heading").text.strip()
                    except:
                        row["event_type"] = event
                    
                    try:
                        row["qc_level"] = card.select_one("p.qc-level").text.strip()
                    except:
                        row["qc_level"] = "N/A"
                    
                    intensity = card.select_one("p.intenstity-value")
                    row["intensity"] = intensity.text.strip() if intensity else "N/A"
                    
                    blocks = card.select("div.event-card__content-wrapper[title]")
                    
                    try:
                        row["city"] = blocks[0].select_one("span.text--bold").text.strip()
                        row["region_country"] = blocks[0].select("p")[1].text.strip()
                    except:
                        row["city"] = "N/A"
                        row["region_country"] = "N/A"
                    
                    try:
                        row["datetime_utc"] = blocks[1].select_one("span.text--bold").text.strip()
                    except:
                        row["datetime_utc"] = "N/A"
                    
                    try:
                        row["reporter"] = blocks[2].text.replace("Reporter:", "").strip()
                    except:
                        row["reporter"] = "N/A"
                    
                    try:
                        row["description"] = blocks[-1].text.strip()
                    except:
                        row["description"] = "N/A"
                    
                    row["query_year"] = i
                    row["query_month"] = smonth
                    row["queried_event"] = event
                    
                    data_rows.append(row)

driver.quit()

df = pd.DataFrame(data_rows)
df.to_csv("eswd_events.csv", index=False)
print(df.head())


timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"eswd_events_{timestamp}.csv"

df.to_csv(
    filename,
    index=False,
    encoding="utf-8-sig"
)
logging.info(f"Data saved to {filename}")

# -*- coding: utf-8 -*-
"""Untitled2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1RotT-SHiMvoioEGkpE5f25_bJthlTP3-
"""

# Commented out IPython magic to ensure Python compatibility.
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# %matplotlib inline

df.head()

df.tail()

df.describe()

df.shape

df.info()

df['intensity'] = df['intensity'].str.replace(
    r'^F-Scale:\s*', '', regex=True
)
df.head()

df2 = pd.DataFrame()
df2[['Region', 'Country']] = df['region_country'].str.split(',', n=1, expand=True)

df2['Country'] = df2['Country'].fillna(df2['Region'])
df2['Region'] = df2['Region'].where(df2['Country'] != df2['Region'])
df2.head(10)

df.info()

3655/5200

true_dat = (df['event_type'] == df['queried_event']).all()
true_dat

df =df.drop(columns=['queried_event'])
df.info()

df.nunique()



from sklearn.preprocessing import LabelEncoder

le = LabelEncoder()

df['region'] = df2['Region']
df['country'] = df2['Country']

df['event_type'] = le.fit_transform(df['event_type'])
df['qc_level'] = le.fit_transform(df['qc_level'])
df['region'] = le.fit_transform(df['region'])
df['reporter'] = le.fit_transform(df['reporter'])
df.drop(columns=['region_country'], inplace=True)
df.head()

