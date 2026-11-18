"""Read the selected engine's configured work without loading a model."""
from core.engine_runner import _select_engine
from core.manifest import DEPTH_CATEGORIES, ProbeCategory, ScanDepth, ScanMode


def get_scan_plan(config: dict) -> dict:
    depth = ScanDepth(config.get('scan_depth', 'standard'))
    mode = ScanMode(config.get('mode', 'api'))
    categories = config.get('categories')
    if categories is None:
        categories = [c.value for c in DEPTH_CATEGORIES[depth]]
    if not isinstance(categories, list) or not categories:
        raise ValueError('Select at least one scan category')
    categories = list(dict.fromkeys(ProbeCategory(c).value for c in categories))
    engine = _select_engine(config.get('engine', 'auto'))
    if engine.name != 'mock' and not engine.is_available():
        raise RuntimeError(f'{engine.name} is not installed in the backend environment')

    aliases = {'data_leak': 'data_leakage', 'harmful_output': 'toxicity'}
    if engine.name == 'garak':
        from core.garak_engine import CATEGORY_PROBE_MAP as specs, _DEPTH_SLICE as slices
    elif engine.name == 'pyrit':
        from core.pyrit_engine import PYRIT_CATEGORY_MAP as specs, _DEPTH_SLICE as slices
    else:
        from core.mock_engine import _FINDING_TEMPLATES as specs
        slices = {depth: None}
        aliases = {}

    families = {category: aliases.get(category, category) for category in categories}
    counts = {family: len(specs.get(family, [])[:slices[depth]]) for family in set(families.values())}
    total = sum(counts.values())
    if not total:
        raise ValueError('The selected engine has no probes for these categories')
    shared = {category: [other for other in categories if other != category and families[other] == family]
              for category, family in families.items()}
    model = None
    capacity = None
    source = config.get('local_model_path') or (config.get('target') if mode == ScanMode.LOCAL else None)
    if source and not str(source).startswith(('http://', 'https://')):
        from core.model_profile import inspect_model, capacity_check
        model = inspect_model(source)
        capacity = capacity_check(model)
    return {
        'model_profile': model, 'capacity': capacity,
        'engine': engine.name, 'mode': mode.value, 'scan_depth': depth.value,
        'total_probes': total,
        'per_category': {category: counts[family] for category, family in families.items()},
        'shared_categories': {category: others for category, others in shared.items() if others},
        # A probe specification can send many requests. Do not invent token prices
        # or duration without model throughput/provider pricing information.
        'estimated_time_sec': None,
        'estimated_time_display': 'Depends on model speed and probe responses',
        'estimated_cost_usd': 0 if mode == ScanMode.LOCAL or engine.name == 'mock' else None,
        'is_heavy': depth == ScanDepth.DEEP,
        'note': 'Counts are probe specifications, not model requests. Shared categories run once.',
    }
