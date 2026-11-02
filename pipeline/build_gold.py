import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'synthetic'
OUT = ROOT / 'pipeline' / 'gold'
OUT.mkdir(exist_ok=True, parents=True)


def _disease_from_icd(code):
    code = str(code).upper()
    if code in {'A90', 'A91'}:
        return 'dengue'
    if code.startswith('A0'):
        return 'diarrhoea'
    if code in {'J10', 'J11'}:
        return 'ili'
    if code.startswith('B5'):
        return 'malaria'
    return 'other'


def load_encounters():
    files = sorted(DATA.glob('encounters_*.csv'))
    if not files:
        raise FileNotFoundError(f'No encounter files found under {DATA}')

    df = pd.concat((pd.read_csv(fp) for fp in files), ignore_index=True)
    facility_map = pd.read_csv(DATA / 'facility_registry.csv', usecols=['facility_id', 'district_id'])
    df = df.merge(facility_map, on='facility_id', how='left')
    df['onset_date'] = pd.to_datetime(df['onset_date'])
    df['epi_week'] = df['onset_date'].dt.to_period('W-MON').dt.start_time
    df['disease'] = df['icd10_code'].map(_disease_from_icd)
    return df


def build_weekly_alerts():
    df = load_encounters()
    counts = (
        df.groupby(['epi_week', 'district_id', 'disease'])
        .size()
        .reset_index(name='case_count')
        .sort_values(['district_id', 'disease', 'epi_week'])
    )
    counts.to_parquet(OUT / 'weekly_alerts.parquet', index=False)
    return counts


def build_stock_summary():
    files = sorted(DATA.glob('stock_snapshots_*.jsonl'))
    if not files:
        raise FileNotFoundError(f'No stock snapshot files found under {DATA}')

    rows = []
    for fp in files:
        with open(fp, 'r', encoding='utf-8') as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))

    stock = pd.DataFrame(rows)
    stock['snapshot_date'] = pd.to_datetime(stock['snapshot_date'])
    stock['epi_week'] = stock['snapshot_date'].dt.to_period('W-MON').dt.start_time
    summary = stock.groupby(['epi_week', 'facility_id']).agg(
        occupied_beds=('occupied_beds', 'mean'),
        iv_saline=('iv_saline', 'mean'),
        ns1_kits=('ns1_kits', 'mean'),
        ors_sachets=('ors_sachets', 'mean'),
        antimalarials=('antimalarials', 'mean'),
    ).reset_index()
    summary.to_parquet(OUT / 'stock_summary.parquet', index=False)
    return summary


def _rolling_baseline(series, baseline_weeks=8):
    out = []
    for idx in range(len(series)):
        window = series.iloc[max(0, idx - baseline_weeks):idx]
        if window.empty:
            out.append((float(series.iloc[idx]), float(series.iloc[idx]), 0.0, 0.0))
            continue
        mean = float(window.mean())
        std = float(window.std(ddof=0) or 1.0)
        current = float(series.iloc[idx])
        z_score = (current - mean) / std if std else 0.0
        out.append((current, mean, std, z_score))
    return out


def build_outbreak_validation(baseline_weeks=8):
    weekly = build_weekly_alerts().copy()
    weekly['district_id'] = pd.to_numeric(weekly['district_id'], errors='coerce')
    truths = pd.read_csv(DATA / 'ground_truth_outbreaks.csv', parse_dates=['start_date', 'end_date'])

    results = []
    thresholds = [1.5, 2.0, 2.5, 3.0, 4.0]
    for threshold in thresholds:
        detections = []
        for (district_id, disease), group in weekly.groupby(['district_id', 'disease'], sort=True):
            ordered = group.sort_values('epi_week').reset_index(drop=True)
            for idx in range(baseline_weeks, len(ordered)):
                baseline = ordered.iloc[max(0, idx - baseline_weeks):idx]['case_count']
                if baseline.empty:
                    continue
                mean = float(baseline.mean())
                std = float(baseline.std(ddof=0) or 1.0)
                current = float(ordered.iloc[idx]['case_count'])
                z_score = (current - mean) / std if std else 0.0
                if current >= max(mean * 1.15, 3.0) and z_score >= threshold:
                    detections.append({
                        'district_id': int(district_id),
                        'disease': disease,
                        'epi_week': ordered.iloc[idx]['epi_week'],
                    })

        true_positive = 0
        false_positive = 0
        for detection in detections:
            row = None
            for _, outbreak in truths.iterrows():
                district_ok = outbreak['district_id'] == 'ALL' or int(outbreak['district_id']) == detection['district_id']
                disease_ok = outbreak['disease'] == 'ALL' or outbreak['disease'] == detection['disease']
                if district_ok and disease_ok and outbreak['start_date'] <= detection['epi_week'] <= outbreak['end_date']:
                    row = outbreak
                    break
            if row is not None:
                true_positive += 1
            else:
                false_positive += 1

        actual_outbreaks = len(truths)
        precision = true_positive / len(detections) if detections else 0.0
        recall = true_positive / actual_outbreaks if actual_outbreaks else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        results.append({
            'threshold': threshold,
            'detections': len(detections),
            'true_positive': true_positive,
            'false_positive': false_positive,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'actual_outbreaks': actual_outbreaks,
        })

    metrics = pd.DataFrame(results).sort_values('f1', ascending=False)
    metrics.to_csv(OUT / 'outbreak_backtest_metrics.csv', index=False)
    return metrics


def build_forecast_backtest(window=8, horizon=4):
    weekly = build_weekly_alerts().copy()
    forecast_rows = []
    for (district_id, disease), group in weekly.groupby(['district_id', 'disease'], sort=True):
        ordered = group.sort_values('epi_week').reset_index(drop=True)
        for idx in range(window, len(ordered) - horizon + 1):
            history = ordered.iloc[max(0, idx - window):idx]['case_count'].astype(float)
            if len(history) < max(3, window // 2):
                continue
            x = pd.Series(range(len(history)), index=history.index)
            slope = (x.cov(history) / x.var(ddof=0)) if x.var(ddof=0) else 0.0
            intercept = float(history.mean() - slope * x.mean())
            predicted_values = []
            for offset in range(1, horizon + 1):
                pred = intercept + slope * (len(history) + offset - 1)
                actual = float(ordered.iloc[idx + offset - 1]['case_count'])
                predicted_values.append((pred, actual))
            for pred, actual in predicted_values:
                forecast_rows.append({
                    'district_id': int(district_id),
                    'disease': disease,
                    'forecast_week': ordered.iloc[idx + predicted_values.index((pred, actual))]['epi_week'],
                    'actual_cases': actual,
                    'predicted_cases': max(pred, 0.0),
                })

    forecast = pd.DataFrame(forecast_rows)
    if not forecast.empty:
        forecast['absolute_error'] = (forecast['actual_cases'] - forecast['predicted_cases']).abs()
        forecast['mape'] = (forecast['absolute_error'] / forecast['actual_cases'].replace(0, pd.NA)).fillna(0.0)
    forecast.to_csv(OUT / 'forecast_backtest.csv', index=False)
    return forecast


if __name__ == '__main__':
    build_weekly_alerts()
    build_stock_summary()
    outbreak = build_outbreak_validation()
    forecast = build_forecast_backtest()
    best_threshold = outbreak.iloc[0] if not outbreak.empty else None
    print('gold tables built')
    if best_threshold is not None:
        print(
            'outbreak validation: '
            f"threshold={best_threshold['threshold']}, "
            f"f1={best_threshold['f1']:.3f}, "
            f"precision={best_threshold['precision']:.3f}, "
            f"recall={best_threshold['recall']:.3f}"
        )
    if not forecast.empty:
        print(f'forecast validation: mean absolute error={forecast["absolute_error"].mean():.2f}, mean APE={forecast["mape"].mean():.3f}')
