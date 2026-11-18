"""Model-bound, editable capacity and price estimates. No cloud login required."""
from datetime import date
import math
from core.model_profile import inspect_model

CATALOG = {
    'aws': {'region': 'us-east-1', 'service': 'SageMaker real-time endpoint',
        'source': 'https://aws.amazon.com/sagemaker/ai/pricing/',
        'machines': [('ml.m5.xlarge', 4, 16, 0, .23), ('ml.m5.2xlarge', 8, 32, 0, .46),
                     ('ml.m5.4xlarge', 16, 64, 0, .922), ('ml.g4dn.xlarge', 4, 16, 16, .7364)]},
    'azure': {'region': 'eastus', 'service': 'Azure ML managed online endpoint',
        'source': 'https://prices.azure.com/api/retail/prices',
        'machines': [('Standard_DS3_v2', 4, 14, 0, .293), ('Standard_DS4_v2', 8, 28, 0, .586),
                     ('Standard_DS5_v2', 16, 56, 0, 1.172)]},
    'gcp': {'region': 'us-central1', 'service': 'Vertex AI online endpoint',
        'source': 'https://cloud.google.com/vertex-ai/pricing',
        'machines': [('n1-standard-4', 4, 15, 0, .21849885), ('n1-standard-8', 8, 30, 0, .4369977),
                     ('n1-standard-16', 16, 60, 0, .8739954), ('n1-standard-4+t4', 4, 15, 16, .56849885)]},
    'private': {'region': 'self-hosted', 'service': 'Docker on your own infrastructure',
        'source': 'user-supplied electricity and hardware costs',
        'machines': [('existing-hardware', 0, 0, 0, 0)]},
}
CATALOG_DATE = '2026-11-17'


def recommendations(source, edits=None, scanned_fingerprint=None):
    edits = edits or {}
    initial = inspect_model(source)
    if scanned_fingerprint and initial['fingerprint'] != scanned_fingerprint:
        raise ValueError('The model artifact changed since the scan. Scan the new artifact before deploying it.')
    offers = []
    for provider, catalog in CATALOG.items():
        edit = edits.get(provider, {})
        model = inspect_model(source, edit.get('context_length', 4096), edit.get('concurrency', 1))
        hours, replicas = float(edit.get('hours_per_month', 730)), int(edit.get('replicas', 1))
        if not 0 < hours <= 744 or not 1 <= replicas <= 10:
            raise ValueError('Hours must be 1–744 per month; replicas must be 1–10')
        machines = catalog['machines']
        choices = [{'id': m[0], 'vcpus': m[1], 'ram_gib': m[2], 'vram_gib': m[3], 'hourly_usd': m[4]} for m in machines]
        fits = lambda m: provider == 'private' or (m[2] >= model['required_ram_gib'] and (not m[3] or (model['format'] == 'gguf' and m[3] >= model['recommended_vram_gib'])))
        eligible = [m for m in machines if fits(m)]
        selected = next((m for m in machines if m[0] == edit.get('instance_type')), None)
        if edit.get('instance_type') and selected is None:
            raise ValueError('Choose an instance from the supported catalog')
        chosen = selected or (min(eligible, key=lambda m: m[4]) if eligible else machines[-1])
        region = edit.get('region', catalog['region'])
        if region != catalog['region']:
            raise ValueError('This pricing catalog currently covers the displayed reference regions only. Other regions need a verified regional price catalog.')
        hourly = chosen[4]
        if provider == 'private':
            watts, kwh, hardware = (float(edit.get(k, default)) for k, default in [('power_watts', 200), ('electricity_usd_kwh', .15), ('hardware_monthly_usd', 0)])
            if any(not math.isfinite(v) or v < 0 for v in (watts, kwh, hardware)):
                raise ValueError('Private hosting costs cannot be negative')
            monthly = watts / 1000 * kwh * hours + hardware
        else:
            monthly = hourly * hours * replicas
        config = {'deployment_mode': 'managed_model', 'region': region, 'instance_type': chosen[0],
            'replicas': replicas, 'hours_per_month': hours, 'context_length': model['context_length'],
            'concurrency': model['concurrency'], 'model_source': model['source'],
            'model_fingerprint': model['fingerprint'], 'model_format': model['format'],
            'accelerator': 'gpu' if chosen[3] else 'cpu', 'endpoint_scope': 'authenticated',
            'scan_id': edit.get('scan_id', ''), 'estimated_monthly_usd': round(monthly, 2)}
        if provider == 'private':
            config.update(power_watts=watts, electricity_usd_kwh=kwh, hardware_monthly_usd=hardware)
        warnings = ['Reference estimate; not a binding account-specific quote.',
            'Compute is billed while deployed, including idle time. Changing hours does not schedule shutdown.',
            'Storage, image builds, registries, logging, traffic, taxes and discounts are excluded.']
        if provider == 'private':
            warnings = ['Electricity/hardware assumptions are editable. This does not include internet, maintenance or replacement costs.']
        offers.append({'provider': provider, 'service': catalog['service'], 'config': config,
            'model': model, 'instances': choices, 'fits': fits(chosen),
            'reason': f'Lowest reference compute price among catalog instances with at least {model["required_ram_gib"]} GiB RAM. Latency has not been benchmarked.',
            'estimate': {'monthly_usd': round(monthly, 2), 'hourly_usd': hourly, 'currency': 'USD',
                'hours_per_month': hours, 'replicas': replicas, 'source': catalog['source'],
                'as_of': CATALOG_DATE, 'basis': 'reference_catalog', 'warnings': warnings}})
    return {'model': initial, 'offers': offers, 'generated_on': date.today().isoformat()}
