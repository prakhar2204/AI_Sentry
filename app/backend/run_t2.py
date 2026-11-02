import sys, json, time
from pathlib import Path

# 1. Prepare output dir and custom REST YAML config for OpenAI chat completions
out_dir = Path('./t2_test_output')
out_dir.mkdir(parents=True, exist_ok=True)
config_path = out_dir / 'llama_chat_config.yaml'

config_yaml = '''plugins:
  generators:
    rest:
      RestGenerator:
        uri: http://127.0.0.1:8080/v1/chat/completions
        method: post
        response_json: true
        response_json_field: \"$.choices[0].message.content\"
        req_template_json_object:
          model: smollm2-135m
          messages:
            - role: user
              content: \"$INPUT\"
        headers:
          Content-Type: application/json
'''
config_path.write_text(config_yaml, encoding='utf-8')

# 2. Run Garak via subprocess (same execution model as GarakEngine)
import subprocess
report_prefix = out_dir / 't2_promptinject'
cmd = [
    sys.executable, '-m', 'garak',
    '--target_type', 'rest',
    '--config', str(config_path),
    '--spec', 'probes.promptinject.HijackHateHumans',
    '--generations', '1',
    '--report_prefix', str(report_prefix)
]

print('>>> Running Garak probe against http://127.0.0.1:8080/v1/chat/completions...')
t0 = time.time()
res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f'>>> Probe finished in {time.time() - t0:.1f}s (returncode: {res.returncode})')
if res.returncode != 0:
    print('=== STDOUT ===\n', res.stdout[-1500:])
    print('=== STDERR ===\n', res.stderr[-1500:])
else:
    print('SUCCESS: Probe report generated under t2_test_output/')
