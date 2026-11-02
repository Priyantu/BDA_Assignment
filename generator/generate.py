"""EpiScope synthetic generator (S4 encounters, S5 registry, S6 stock, ground truth,
plus placeholder S2/S3 if real files are absent). Deterministic for (--sf, --seed).
SF=1 -> ~25M encounters. Default SF=0.004 -> ~100k rows for development.
All outputs are SYNTHETIC. Run: python generator/generate.py --sf 0.004 --seed 42
"""
import argparse, os, json, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from districts import ROWS

ap = argparse.ArgumentParser()
ap.add_argument("--sf", type=float, default=0.004)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--start", default="2021-01-04")  # a Monday
ap.add_argument("--end", default="2025-12-28")
ap.add_argument("--out", default="data/synthetic")
ap.add_argument("--weather", default="data/real/weather_daily.csv")  # S3 real, if present
a = ap.parse_args()
rng = np.random.default_rng(a.seed)
os.makedirs(a.out, exist_ok=True)

dist = pd.DataFrame(ROWS); ND = len(dist)
weeks = pd.date_range(a.start, a.end, freq="W-MON"); NW = len(weeks)
days = pd.date_range(a.start, pd.Timestamp(a.end) + pd.Timedelta(days=6))
woy = ((weeks.dayofyear - 1) // 7).values % 52
pop = dist.population_est.values.astype(float)
DIS = ["dengue", "diarrhoea", "ili", "malaria", "other"]
CODES = {"dengue": (["A90", "A91"], [.7, .3]), "diarrhoea": (["A00", "A09"], [.1, .9]),
         "ili": (["J10", "J11"], [.4, .6]), "malaria": (["B50", "B51", "B52", "B53", "B54"], [.1, .6, .05, .05, .2]),
         "other": (["K29", "R50", "J06", "N39", "L03", "I10"], [.2, .3, .2, .1, .1, .1])}

# ---- S3 weather (real if available, else synthetic placeholder) ----
if os.path.exists(a.weather):
    w = pd.read_csv(a.weather, parse_dates=["date"]); wsrc = "real"
else:
    wsrc = "SYNTHETIC_PLACEHOLDER"
    dd = np.tile(days.values, ND); did = np.repeat(dist.district_id.values, len(days))
    doy = pd.DatetimeIndex(dd).dayofyear.values
    mons = np.exp(-((doy - 200) / 45.0) ** 2)
    rain = rng.gamma(0.3 + 1.2 * mons, 6 + 14 * mons) * (rng.random(len(dd)) < 0.15 + 0.6 * mons)
    lat = np.repeat(dist.centroid_lat.values, len(days))
    temp = 26 - 0.6 * (lat - 23) + 5 * np.sin((doy - 110) / 365 * 2 * np.pi) + rng.normal(0, 1.2, len(dd))
    hum = np.clip(65 + 20 * mons + rng.normal(0, 5, len(dd)), 30, 100)
    w = pd.DataFrame(dict(district_id=did, date=dd, precip_mm=rain.round(1), temp_mean_c=temp.round(1), humidity_pct=hum.round(0)))
    w.to_csv(os.path.join(a.out, "weather_daily_SYNTHETIC_PLACEHOLDER.csv"), index=False)
w["wk"] = ((w.date - weeks[0]).dt.days // 7).clip(0, NW - 1)
wk = w.groupby(["district_id", "wk"]).agg(rain=("precip_mm", "sum"), temp=("temp_mean_c", "mean")).reset_index()
RAIN = np.zeros((ND, NW)); TEMP = np.full((ND, NW), 26.0)
RAIN[wk.district_id - 1, wk.wk] = wk.rain; TEMP[wk.district_id - 1, wk.wk] = wk.temp

def lagmean(x, lo, hi):  # mean of x over lags lo..hi weeks
    out = np.zeros_like(x)
    for l in range(lo, hi + 1):
        out[:, l:] += x[:, :NW - l]
    return out / (hi - lo + 1)

rain_l = lagmean(RAIN, 4, 8); rain_z = (rain_l - rain_l.mean(1, keepdims=True)) / (rain_l.std(1, keepdims=True) + 1e-9)
temp_l = lagmean(TEMP, 4, 8); temp_z = (temp_l - temp_l.mean(1, keepdims=True)) / (temp_l.std(1, keepdims=True) + 1e-9)
rain_1 = lagmean(RAIN, 1, 1); extreme = (rain_1 > np.percentile(RAIN[RAIN > 0], 92)).astype(float)

# ---- district weights ----
big = np.isin(dist.district.values, ["Dhaka", "Chattogram", "Gazipur", "Narayanganj", "Khulna", "Rajshahi", "Sylhet", "Cumilla"])
hill = np.isin(dist.district.values, ["Bandarban", "Rangamati", "Khagrachhari", "Cox's Bazar", "Sylhet", "Moulvibazar"])
wt = {"dengue": pop * np.where(big, 3.0, 0.5) * rng.lognormal(0, .3, ND),
      "diarrhoea": pop * rng.lognormal(0, .25, ND), "ili": pop * rng.lognormal(0, .2, ND),
      "malaria": pop * np.where(hill, 2.5, 0.01) * rng.lognormal(0, .3, ND), "other": pop * 8 * rng.lognormal(0, .1, ND)}
ang = woy / 52 * 2 * np.pi
season = {"dengue": np.exp(1.6 * np.cos(ang - 36 / 52 * 2 * np.pi)),
          "diarrhoea": np.exp(.7 * np.cos(ang - 15 / 52 * 2 * np.pi)) + .5 * np.exp(.8 * np.cos(ang - 31 / 52 * 2 * np.pi)),
          "ili": np.exp(1.0 * np.cos(ang - 28 / 52 * 2 * np.pi)), "malaria": np.exp(1.1 * np.cos(ang - 30 / 52 * 2 * np.pi)),
          "other": np.ones(NW)}
MU = np.zeros((len(DIS), ND, NW)); MULT = np.ones((len(DIS), ND, NW))
for k, d in enumerate(DIS):
    base = wt[d][:, None] * season[d][None, :]
    if d == "dengue": base = base * np.exp(.45 * rain_z + .25 * temp_z)
    if d == "diarrhoea": base = base * (1 + .8 * extreme)
    MU[k] = base
# ---- injected outbreaks ----
dn = {d: i for i, d in enumerate(DIS)}
obs = []
def add(disease, did, sw, dur, peak, kind):
    sw = int(np.clip(sw, 0, NW - 2)); ew = int(min(NW - 1, sw + dur))
    L = ew - sw + 1; t = np.arange(L)
    shape = (t / (L - 1)) if kind == "slow_growing" else np.clip(np.sin(np.pi * t / (L - 1)), 0, None) ** 1.2
    if kind == "national_novel": shape = np.clip(np.sin(np.pi * t / (L - 1)), 0, None) ** 1.5
    m = 1 + (peak - 1) * shape
    rows = range(ND) if did == 0 else [did - 1]
    for r in rows: MULT[dn[disease], r, sw:ew + 1] = np.maximum(MULT[dn[disease], r, sw:ew + 1], m)
    obs.append(dict(outbreak_id=f"OB{len(obs)+1:03d}", district_id="ALL" if did == 0 else did, disease=disease,
                    start_date=str(weeks[sw].date()), end_date=str((weeks[ew] + pd.Timedelta(days=6)).date()),
                    peak_multiplier=round(float(peak), 2), kind=kind))
add("ili", 0, 62, 20, 6.0, "national_novel")          # nationwide novel respiratory surge (2022)
add("dengue", 1, 130, 22, 4.5, "localised")           # a slow-growing one below
add("diarrhoea", 31, 100, 24, 3.0, "slow_growing")
rr = np.random.default_rng(a.seed + 1)
for _ in range(28):
    d = rr.choice(["dengue", "diarrhoea", "ili", "malaria"], p=[.4, .25, .2, .15])
    did = int(rr.integers(1, ND + 1))
    if d == "malaria": did = int(rr.choice(dist.district_id[hill]))
    sw = int(rr.integers(8, NW - 14)); add(d, did, sw, int(rr.integers(5, 14)), float(rr.uniform(2.5, 6)), "localised")
MU *= MULT
# normalise to target volume, apply NB noise
target = 25e6 * a.sf
MU *= target / MU.sum()
disp = 8.0
lam = rng.gamma(disp, MU / disp)
CNT = rng.poisson(lam).astype(np.int64)
print("encounters:", CNT.sum(), "target:", int(target), "weather:", wsrc)

# ---- S5 facility registry ----
nf = 640
fd = rng.choice(ND, nf, p=pop / pop.sum() * .7 + .3 / ND)
fd[:ND] = np.arange(ND)  # every district has >=1
ftype = rng.choice(["hospital", "UHC", "clinic"], nf, p=[.2, .35, .45])
beds = np.where(ftype == "hospital", rng.integers(100, 600, nf), np.where(ftype == "UHC", rng.integers(31, 100, nf), rng.integers(5, 30, nf)))
beds = (beds * np.where(big[fd], 1.6, 1)).astype(int)
icu = np.where(ftype == "hospital", (beds * .06).astype(int), np.where(ftype == "UHC", rng.integers(0, 4, nf), 0))
fac = pd.DataFrame(dict(facility_id=[f"F{i:05d}" for i in range(nf)], facility_name=[f"{t} {i}" for i, t in enumerate(ftype)],
        type=ftype, district_id=dist.district_id.values[fd], lat=(dist.centroid_lat.values[fd] + rng.normal(0, .08, nf)).round(4),
        lon=(dist.centroid_lon.values[fd] + rng.normal(0, .08, nf)).round(4), beds=beds, icu_beds=icu))
fac.to_csv(os.path.join(a.out, "facility_registry.csv"), index=False)
fw = [(fac.beds.values[fd == d] ** 1.0) for d in range(ND)]; fi = [np.where(fd == d)[0] for d in range(ND)]

# ---- S4 encounters ----
parts = []
dow_w = np.array([1.0, 1.0, 1.0, 1.0, 1.0, .45, .45])  # Mon..Sun onset weights
adm = {"dengue": .10, "diarrhoea": .04, "ili": .03, "malaria": .15, "other": .02}
labp = {"dengue": .35, "diarrhoea": .05, "ili": .1, "malaria": .8, "other": .0}
agem = {"dengue": (22, 12), "diarrhoea": (12, 18), "ili": (25, 20), "malaria": (28, 15), "other": (40, 20)}
for k, dname in enumerate(DIS):
    di, wi = np.nonzero(CNT[k]); n = CNT[k][di, wi]
    d_rep = np.repeat(di, n); w_rep = np.repeat(wi, n)
    m_rep = np.repeat(MULT[k][di, wi], n)
    N = len(d_rep)
    if N == 0: continue
    off = rng.choice(7, N, p=dow_w / dow_w.sum())
    onset = weeks.values[w_rep] + off.astype("timedelta64[D]")
    delay = np.minimum(21, np.floor(rng.lognormal(.6, .9, N))).astype(int)
    rep = pd.DatetimeIndex(onset) + pd.to_timedelta(delay, unit="D")
    fid = np.empty(N, dtype=int)
    for d in np.unique(d_rep):
        idx = np.where(d_rep == d)[0]; p = fw[d] / fw[d].sum()
        fid[idx] = rng.choice(fi[d], len(idx), p=p)
    codes, cp = CODES[dname]
    mu_a, sd_a = agem[dname]
    age = np.clip(rng.normal(mu_a, sd_a, N), 0, 95).astype(int)
    surge = np.clip((m_rep - 1) / 3, 0, 1)
    adm_f = rng.random(N) < np.clip(adm[dname] * (1 + 1.2 * surge), 0, .6)
    died = adm_f & (rng.random(N) < (.02 if dname in ("dengue", "malaria") else .01))
    outc = np.where(died, "died", np.where(adm_f & (rng.random(N) < .1), "referred", "recovered"))
    parts.append(pd.DataFrame(dict(facility_idx=fid, onset_date=pd.DatetimeIndex(onset), report_date=rep, age_years=age,
        sex=rng.choice(["M", "F"], N), icd10_code=rng.choice(codes, N, p=cp), lab_confirmed=rng.random(N) < labp[dname] * (1 + .5 * surge),
        admitted=adm_f, outcome=outc)))
enc = pd.concat(parts, ignore_index=True)
# weekend (Fri/Sat) & holiday reporting dip -> push to next Sunday/working day
rd = enc.report_date
shift = np.where(rd.dt.dayofweek == 4, 2, np.where(rd.dt.dayofweek == 5, 1, 0))
hol = rd.dt.strftime("%m-%d").isin(["02-21", "03-26", "12-16", "04-14"]).values
enc["report_date"] = rd + pd.to_timedelta(shift + hol.astype(int), unit="D")
enc["facility_id"] = fac.facility_id.values[enc.facility_idx]
# reporting artefact: busiest Dhaka-district facility silent 3 wks then back-fills
dh = np.where(fd == 0)[0]; cnt = enc[enc.facility_idx.isin(dh)].facility_idx.value_counts()
af = cnt.index[0]; s0 = weeks[NW // 2]; s1 = s0 + pd.Timedelta(days=21); bf = s1 + pd.Timedelta(days=3)
mask = (enc.facility_idx == af) & (enc.report_date >= s0) & (enc.report_date < s1)
enc.loc[mask, "report_date"] = bf
obs.append(dict(outbreak_id="ARTEFACT01", district_id=1, disease="ALL", start_date=str(s0.date()), end_date=str(bf.date()),
                peak_multiplier=0, kind=f"reporting_artefact:facility={fac.facility_id.values[af]} silent then backfill (NOT a true outbreak)"))
enc = enc.sort_values("report_date", kind="stable").reset_index(drop=True)
N = len(enc)
enc["encounter_id"] = [f"E{i:010d}" for i in range(N)]
enc["patient_id"] = [f"P{x:08d}" for x in rng.integers(0, 10**8, N)]
# injected defects
o = rng.random(N) < .005; enc.loc[o, "facility_id"] = [f"F9{x:04d}" for x in rng.integers(0, 9999, o.sum())]
b = rng.random(N) < .01; enc.loc[b, "age_years"] = rng.choice([212, -3, 150, 999], b.sum())
cols = ["encounter_id", "patient_id", "facility_id", "onset_date", "report_date", "age_years", "sex", "icd10_code", "lab_confirmed", "admitted", "outcome"]
enc = enc[cols]
dup = enc.sample(frac=.02, random_state=a.seed)
enc = pd.concat([enc, dup]).sort_values("report_date", kind="stable").reset_index(drop=True)
for c in ["onset_date", "report_date"]: enc[c] = enc[c].dt.strftime("%Y-%m-%d")
yr = enc.report_date.str[:4]
for y, g in enc.groupby(yr): g.to_csv(os.path.join(a.out, f"encounters_{y}.csv"), index=False)
print("S4 rows incl. duplicates:", len(enc))

# ---- ground truth (detection code must NEVER read this) ----
pd.DataFrame(obs).to_csv(os.path.join(a.out, "ground_truth_outbreaks.csv"), index=False)

# ---- S6 stock & occupancy (JSON lines per year) ----
tot = CNT.sum(0); load = tot / (tot.mean(1, keepdims=True) + 1e-9)
dwk = np.clip(((days - weeks[0]).days // 7).values, 0, NW - 1)
res = {"iv_saline": 30, "ns1_kits": 8, "ors_sachets": 100, "antimalarials": 5}
for y in sorted(set(days.year)):
    di = np.where(days.year == y)[0]; recs = []
    for f in range(nf):
        d = fd[f]; t = np.arange(len(di)); ph = rng.integers(0, 30)
        saw = 1 - ((t + ph) % 30) / 30.0
        occ = np.clip(beds[f] * (.45 + .3 * load[d, dwk[di]] ** .7 + rng.normal(0, .05, len(di))), 0, beds[f] * 1.2).astype(int)
        r = dict(snapshot_date=days[di].strftime("%Y-%m-%d"), facility_id=fac.facility_id.values[f], occupied_beds=occ)
        for kx, sc in res.items(): r[kx] = np.maximum(0, (sc * beds[f] ** .8 * (.15 + .85 * saw) * rng.uniform(.8, 1.2, len(di)))).astype(int)
        recs.append(pd.DataFrame(r))
    pd.concat(recs).to_json(os.path.join(a.out, f"stock_snapshots_{y}.jsonl"), orient="records", lines=True)
dist.to_csv(os.path.join(a.out, "district_reference_APPROX.csv"), index=False)
print("done ->", a.out)
