import pytest
from core.manifest import ProbeCategory
from core.scan_plan import get_scan_plan


@pytest.fixture(autouse=True)
def available(monkeypatch):
    monkeypatch.setattr('core.adapters.garak_adapter.GarakAdapter.is_available', staticmethod(lambda: True))
    monkeypatch.setattr('core.adapters.pyrit_adapter.PyRITAdapter.is_available', staticmethod(lambda: True))


@pytest.mark.parametrize('depth,total', [('quick', 6), ('standard', 12), ('deep', 21)])
def test_all_categories_match_garak_execution_plan(depth, total, tmp_path):
    from core.garak_engine import GarakEngine, ALL_CATEGORIES
    categories = [c.value for c in ProbeCategory]
    plan = get_scan_plan({'engine': 'auto', 'categories': categories, 'scan_depth': depth, 'mode': 'local'})
    engine = GarakEngine('http://localhost:8000', tmp_path, depth=depth)
    assert plan['total_probes'] == total == len(engine.probe_specs_for_depth(ALL_CATEGORIES))
    assert all(plan['per_category'].values())
    assert plan['shared_categories']['toxicity'] == ['harmful_output']
    assert plan['estimated_cost_usd'] == 0
    assert plan['estimated_time_sec'] is None


@pytest.mark.parametrize('category', ['encoding_injection', 'malware_generation', 'toxicity', 'harmful_output'])
def test_new_categories_are_not_estimated_as_zero(category):
    plan = get_scan_plan({'categories': [category], 'scan_depth': 'quick'})
    assert plan['total_probes'] == 1
    assert plan['per_category'] == {category: 1}
    assert plan['estimated_cost_usd'] is None


def test_duplicate_and_shared_categories_do_not_double_count():
    plan = get_scan_plan({'categories': ['toxicity', 'toxicity', 'harmful_output'], 'scan_depth': 'deep'})
    assert plan['total_probes'] == 4
    assert plan['per_category'] == {'toxicity': 4, 'harmful_output': 4}


def test_pyrit_plan_uses_its_own_attack_table(tmp_path):
    from core.pyrit_engine import PyRITEngine, ALL_CATEGORIES
    plan = get_scan_plan({'engine': 'pyrit', 'categories': [c.value for c in ProbeCategory], 'scan_depth': 'deep'})
    engine = PyRITEngine('http://localhost:8000', tmp_path, depth='deep')
    assert plan['total_probes'] == len(engine.attack_specs_for_depth(ALL_CATEGORIES)) == 12


def test_explicit_missing_engine_fails_before_model_loading(monkeypatch):
    monkeypatch.setattr('core.adapters.pyrit_adapter.PyRITAdapter.is_available', staticmethod(lambda: False))
    with pytest.raises(RuntimeError, match='pyrit is not installed'):
        get_scan_plan({'engine': 'pyrit', 'categories': ['prompt_injection']})


@pytest.mark.parametrize('config', [{'categories': []}, {'categories': ['unknown']}, {'scan_depth': 'invalid'}, {'engine': 'unknown'}])
def test_invalid_plan_rejected(config):
    with pytest.raises(ValueError):
        get_scan_plan(config)
