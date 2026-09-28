"""Open Firefox Developer Edition (headed) via Selenium and navigate to amiabot.app."""
import sys
import time

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

URL = "https://amiabot.app/"

opts = Options()
opts.binary_location = "/usr/lib/firefox-developer-edition/firefox"

print(f"[{time.strftime('%H:%M:%S')}] starting Firefox Dev Edition via geckodriver...", flush=True)
driver = webdriver.Firefox(options=opts)  # Selenium Manager downloads geckodriver if missing
print(f"[{time.strftime('%H:%M:%S')}] browser up: {driver.capabilities.get('browserVersion')}", flush=True)

driver.get(URL)
print(f"[{time.strftime('%H:%M:%S')}] loaded: {driver.title!r} @ {driver.current_url}", flush=True)

# Keep the browser open for bermudi; exit quietly if he closes the window.
try:
    while driver.current_url:
        time.sleep(5)
except Exception as e:
    print(f"[{time.strftime('%H:%M:%S')}] browser gone ({type(e).__name__}), exiting", flush=True)
    sys.exit(0)
