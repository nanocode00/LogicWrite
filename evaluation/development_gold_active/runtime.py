"""Label-blind input inventory and post-prediction active reference resolution."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = 'evaluation/g3_g4/development_gold_v3_active_2026-11-13/development-gold.json'
INDEX_PATH = 'evaluation/active_development_gold.json'
CASE_IDS = tuple([f'SP-{i:03}' for i in range(1,13)] + [f'GC-{i:03}' for i in range(1,13)] + [f'SP-{i:03}' for i in range(13,18)])


def module(name,path):
    spec=importlib.util.spec_from_file_location('active_gold_'+name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def input_path(cid):
    if cid not in CASE_IDS:raise ValueError('case outside active v3 input inventory')
    base=('evaluation/g3_g4/inputs' if cid.startswith('GC-') else
          'evaluation/semantic_pilot/inputs' if int(cid[3:])<=12 else 'evaluation/golden_expansion/inputs')
    return ROOT/base/(cid+'.json')


class IndependentInputs:
    def __truediv__(self,filename):
        if not filename.endswith('.json'):raise ValueError('JSON input required')
        return input_path(filename[:-5])


def activation_module():
    return module('activation', (ROOT/GOLD_PATH).parent/'validate.py')


def active_reference():
    activation_module().validate()
    index=json.loads((ROOT/INDEX_PATH).read_text())
    if index['active_dataset']['path']!=GOLD_PATH:raise ValueError('unexpected active dataset')
    return ROOT/GOLD_PATH
