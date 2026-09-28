"""Rung 2b: instance-level configurable webdriver patch + capture the report POST."""
import json, os, time, traceback

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

PATCH = """() => {
  Object.defineProperty(navigator, 'webdriver', {get: () => undefined, configurable: true});
  const of = window.fetch;
  window.fetch = async function(...args) {
    const res = await of.apply(this, args);
    if (String(args[0]).includes('/api/report')) {
      try { window.__report = await res.clone().json(); } catch (e) {}
    }
    return res;
  };
}"""

opts = Options()
opts.binary_location = "/usr/lib/firefox-developer-edition/firefox"
opts.web_socket_url = True

driver = webdriver.Firefox(options=opts)
print(f"[{time.strftime('%H:%M:%S')}] up", flush=True)

from selenium.webdriver.common._bidi.script import Script
s = Script(driver)
s.add_preload_script(PATCH)
print("patch v2 registered (instance-level, configurable + fetch hook)", flush=True)

driver.get("https://amiabot.app/")

report = None
deadline = time.time() + 35
while time.time() < deadline:
    report = driver.execute_script("return window.__report || null")
    if report:
        break
    time.sleep(2)

if report:
    os.makedirs("/tmp/selenium-firefox", exist_ok=True)
    json.dump(report, open("/tmp/selenium-firefox/report_wd3.json", "w"), indent=1)
    v = report["verdict"]
    print(f"SCORE {v['score']} -> {v['classification']} (risk {v['risk']})", flush=True)
    for x in v.get("reasons", []):
        print(f"  reason: {x['id']} ({x.get('points')}pts, {x.get('severity')}) - {x.get('message','')[:60]}", flush=True)
    b, a, w = report["client"]["browser"], report["client"]["automation"], report["client"]["workers"]
    print(f"webdriver win={b.get('webdriver')} auto={a.get('webdriver')} "
          f"worker={w.get('webWorker',{}).get('webdriver')} iframe={w.get('iframe',{}).get('webdriver')} "
          f"sw={w.get('serviceWorker',{}).get('webdriver')}", flush=True)
    print(f"behavior score: {report['client']['behavior']['score']}", flush=True)
    print(f"cloudflare bot score: {report.get('cloudflareBotManagement',{}).get('score')}", flush=True)
else:
    print("no report captured in 35s - page state:", flush=True)
    txt = driver.execute_script("return document.body.innerText")
    print("\n".join(l.strip() for l in txt.splitlines() if l.strip())[:500], flush=True)

print(f"[{time.strftime('%H:%M:%S')}] idling (window stays open)...", flush=True)
try:
    while True:
        time.sleep(5)
        if not driver.execute_script("return !!document.body"):
            break
except Exception:
    pass
