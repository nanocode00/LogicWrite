"""Verify the staged v3 dataset; success does not mean it is active."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
path = ROOT / 'evaluation/golden_expansion/legacy_migration_2026_11_13/validate_migration.py'
spec = importlib.util.spec_from_file_location('staged_v3_migration', path)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)

if __name__ == '__main__':
    print(json.dumps(migration.validate(), ensure_ascii=False))
