import json
from pathlib import Path
from core.garak_engine import GarakEngine

report_file = next(Path('./t2_test_output').glob('t2_promptinject*.report.jsonl'))
print(f"=== Report File: {report_file.name} ===\n")

# 1. Parse using GarakEngine adapter logic
engine = GarakEngine(target_url='http://127.0.0.1:8080/v1/chat/completions', output_dir='./t2_test_output')
findings = list(engine._parse_report(report_file, 'probes.promptinject.HijackHateHumans', 'prompt_injection'))

# 2. Read raw JSONL records
raw_attempts = []
raw_eval = None
raw_digest = None

with open(report_file, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        entry = data.get('entry_type')
        if entry == 'attempt' and len(raw_attempts) < 3:
            raw_attempts.append(data)
        elif entry == 'eval':
            raw_eval = data
        elif entry == 'digest':
            raw_digest = data

# 3. Side-by-Side Display
print('=' * 80)
print('                  SIDE-BY-SIDE INSPECTION: RAW JSONL vs FINDING OBJECT')
print('=' * 80)

print('\n[A] EVAL RECORD COMPARISON:')
print('  RAW JSONL eval entry:')
if raw_eval:
    print(f"    probe:            {raw_eval.get('probe')}")
    print(f"    detector:         {raw_eval.get('detector')}")
    print(f"    passed / fails:   {raw_eval.get('passed')} / {raw_eval.get('fails')}")
    print(f"    total_evaluated:  {raw_eval.get('total_evaluated')}")
else:
    print("    No eval record found in report")

print('\n  PARSED VulnerabilityFinding object:')
if findings:
    f0 = findings[0]
    print(f"    finding_id:       {f0.finding_id}")
    print(f"    engine:           {f0.engine}")
    print(f"    category:         {f0.category}")
    print(f"    probe:            {f0.probe}")
    print(f"    detector:         {f0.detector}")
    print(f"    passed / failed:  {f0.passed} / {f0.failed} (total: {f0.total})")
    print(f"    pass_rate:        {f0.pass_rate:.4f}")
    print(f"    severity (1-5):   {f0.severity}")
    print(f"    confidence (0-1): {f0.confidence:.2f}")
else:
    print('    No findings generated (0 fails or eval missing)')

print('\n' + '=' * 80)
print('[B] SAMPLE RAW ATTEMPTS (What was sent vs What model returned):')
print('=' * 80)
for idx, att in enumerate(raw_attempts, 1):
    prompt_text = att['prompt']['turns'][0]['content']['text']
    clean_prompt = prompt_text.replace('\n', ' ')[:90] + '...'
    output_text = att['outputs'][0]['text'].replace('\n', ' ')[:90] + '...'
    det_results = att.get('detector_results', {})
    print(f"Attempt #{idx}:")
    print(f"  Prompt:   {clean_prompt}")
    print(f"  Response: {output_text}")
    print(f"  Detector: {det_results}")
    print('-' * 40)