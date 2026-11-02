from pathlib import Path


def test_project_structure():
    root = Path(__file__).resolve().parents[1]
    required = [
        root / 'pipeline',
        root / 'dashboard',
        root / 'docs',
        root / 'data' / 'synthetic',
    ]
    for path in required:
        assert path.exists(), f'Missing expected path: {path}'


def test_generated_data_files_exist():
    root = Path(__file__).resolve().parents[1]
    cache = [
        root / 'data' / 'synthetic' / 'facility_registry.csv',
        root / 'data' / 'synthetic' / 'district_reference_APPROX.csv',
        root / 'data' / 'synthetic' / 'ground_truth_outbreaks.csv',
    ]
    for path in cache:
        assert path.exists(), f'Missing generated file: {path}'
