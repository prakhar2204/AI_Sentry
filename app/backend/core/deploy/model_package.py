"""Package only inspected model files and the owned inference adapter."""
import json
from pathlib import Path
import shutil
import zipfile
from core.model_profile import inspect_model, artifact_digest


def package_model(config, destination):
    profile = inspect_model(config['model_source'], config['context_length'], config['concurrency'])
    if profile['fingerprint'] != config['model_fingerprint']:
        raise ValueError('Model changed since scan/review. Rescan before deployment.')
    if config.get('model_sha256') and artifact_digest(profile) != config['model_sha256']:
        raise ValueError('Model content changed since scanning; deployment cancelled')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(destination).free < profile['size_bytes'] * 2 + 1024 ** 3:
        raise RuntimeError('Not enough free disk space to package the model (requires twice its size plus 1 GiB)')
    model_directory = destination / 'model'
    model_directory.mkdir(exist_ok=True)
    root = Path(profile['source'])
    for filename in profile['files']:
        source = Path(filename)
        relative = source.relative_to(root) if root.is_dir() else Path('model.gguf')
        target = model_directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    # Detect replacement during packaging, before any upload starts.
    if inspect_model(config['model_source'])['fingerprint'] != config['model_fingerprint']:
        raise ValueError('Model changed while packaging; upload cancelled')
    copied = {'files': [str(model_directory / (Path(p).relative_to(root) if root.is_dir() else 'model.gguf')) for p in profile['files']]}
    if config.get('model_sha256') and artifact_digest(copied) != config['model_sha256']:
        raise ValueError('Packaged model does not match the scanned content; upload cancelled')
    shutil.copyfile(Path(__file__).with_name('serving_runtime.py'), destination / 'runtime.py')
    if profile['format'] == 'gguf':
        base = 'ghcr.io/ggml-org/llama.cpp:server' + ('-cuda' if config['accelerator'] == 'gpu' else '')
        install = 'RUN apt-get update && apt-get install -y python3 ca-certificates && rm -rf /var/lib/apt/lists/*\n'
    else:
        if config['accelerator'] != 'cpu':
            raise ValueError('Transformers GPU deployment requires a validated GPU runtime; choose a CPU instance for this adapter')
        base = 'python:3.12-slim'
        install = 'RUN pip install --no-cache-dir torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir transformers==5.19.0 safetensors==0.8.0\n'
    dockerfile = f'FROM {base}\nUSER root\n{install}COPY runtime.py /sentry/runtime.py\nCOPY model /model\n'
    dockerfile += f'ENV MODEL_FORMAT={profile["format"]} MODEL_CONTEXT={config["context_length"]} MODEL_CONCURRENCY={config["concurrency"]} MODEL_ACCELERATOR={config["accelerator"]}\n'
    dockerfile += 'EXPOSE 8080\nENTRYPOINT ["python3", "/sentry/runtime.py"]\n'
    (destination / 'Dockerfile').write_text(dockerfile, encoding='utf-8')
    (destination / '.dockerignore').write_text('*.zip\n*.tar.gz\n', encoding='utf-8')
    compose = {'services': {'model': {'build': '.', 'ports': ['127.0.0.1:8080:8080'], 'restart': 'unless-stopped'}}}
    if config['accelerator'] == 'gpu':
        compose['services']['model']['gpus'] = 'all'
    (destination / 'compose.json').write_text(json.dumps(compose, indent=2), encoding='utf-8')
    return destination


def zip_context(directory):
    archive = directory.parent / 'source.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as output:
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                output.write(path, path.relative_to(directory).as_posix())
    return archive
