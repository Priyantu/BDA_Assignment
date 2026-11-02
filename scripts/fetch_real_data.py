"""Download real data S1 (boundaries), S3 (weather). Run LOCALLY (needs internet):
   python scripts/fetch_real_data.py
S1: geoBoundaries BGD ADM2 (district). S3: Open-Meteo archive at district centroids (cached)."""
import os, json, time, urllib.request, urllib.parse, csv, sys
sys.path.insert(0, "generator")
from districts import ROWS
os.makedirs("data/real", exist_ok=True)
# --- S1 ---
meta = json.load(urllib.request.urlopen("https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM2/"))
urllib.request.urlretrieve(meta["simplifiedGeometryGeoJSON"], "data/real/bgd_adm2.geojson")
print("S1 saved (check it has 64 features; names may differ slightly from districts.py)")
# --- S3 ---
out = "data/real/weather_daily.csv"
rows = []
for r in ROWS:
    cache = f"data/real/_cache_wx_{r['district_id']}.json"
    if not os.path.exists(cache):
        q = urllib.parse.urlencode(dict(latitude=r["centroid_lat"], longitude=r["centroid_lon"], start_date="2021-01-01",
            end_date="2026-01-10", daily="precipitation_sum,temperature_2m_mean,relative_humidity_2m_mean", timezone="Asia/Dhaka"))
        for attempt in range(5):
            try:
                open(cache, "wb").write(urllib.request.urlopen("https://archive-api.open-meteo.com/v1/archive?" + q).read()); break
            except Exception as e:
                print("retry", r["district"], e); time.sleep(30 * (attempt + 1))
        time.sleep(2)
    d = json.load(open(cache))["daily"]
    for i, t in enumerate(d["time"]):
        rows.append([r["district_id"], t, d["precipitation_sum"][i], d["temperature_2m_mean"][i], d["relative_humidity_2m_mean"][i]])
with open(out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["district_id", "date", "precip_mm", "temp_mean_c", "humidity_pct"]); w.writerows(rows)
print("S3 saved", len(rows), "rows. Now re-run: python generator/generate.py  (it will use real weather)")
