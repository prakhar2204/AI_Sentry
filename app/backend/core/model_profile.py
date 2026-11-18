"""Inspect model artifacts without deserializing weights or executing model code."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import struct

GIB = 1024 ** 3


def _gguf_metadata(path):
    values = {}
    with path.open('rb') as stream:
        def read(n):
            if n > 1024 * 1024 or stream.tell() + n > 32 * 1024 * 1024:
                raise ValueError('GGUF metadata exceeds inspection limits')
            value = stream.read(n)
            if len(value) != n:
                raise ValueError('Truncated GGUF header')
            return value
        def number(fmt):
            return struct.unpack('<' + fmt, read(struct.calcsize(fmt)))[0]
        def string():
            return read(number('Q')).decode('utf-8')
        formats = {0: 'B', 1: 'b', 2: 'H', 3: 'h', 4: 'I', 5: 'i', 6: 'f', 7: '?', 10: 'Q', 11: 'q', 12: 'd'}
        def value(kind, nesting=0):
            if kind in formats:
                return number(formats[kind])
            if kind == 8:
                return string()
            if kind == 9 and nesting == 0:
                subtype, count = number('I'), number('Q')
                if count > 500000:
                    raise ValueError('GGUF metadata array is too large')
                for _ in range(count):
                    value(subtype, 1)
                return None
            raise ValueError('Unsupported GGUF metadata type')
        if read(4) != b'GGUF' or number('I') not in (2, 3):
            raise ValueError('Expected a GGUF v2/v3 model')
        number('Q')
        count = number('Q')
        if count > 100000:
            raise ValueError('Invalid GGUF metadata count')
        for _ in range(count):
            key = string()
            item = value(number('I'))
            if item is not None and not key.startswith('tokenizer.'):
                values[key] = item
    return values


def inspect_model(source: str, context_length=4096, concurrency=1) -> dict:
    context_length, concurrency = int(context_length), int(concurrency)
    if not 256 <= context_length <= 131072 or not 1 <= concurrency <= 32:
        raise ValueError('Context must be 256–131072 tokens; concurrency must be 1–32')
    path = Path(source).expanduser().resolve(strict=True)
    if path.is_file() and path.suffix.lower() == '.safetensors':
        path = path.parent
    metadata = {}
    if path.is_file() and path.suffix.lower() == '.gguf':
        metadata = _gguf_metadata(path)
        files = [path]
        kind = 'gguf'
        architecture = metadata.get('general.architecture', 'unknown')
        layers = metadata.get(f'{architecture}.block_count', 32)
        hidden = metadata.get(f'{architecture}.embedding_length', 4096)
        heads = metadata.get(f'{architecture}.attention.head_count', 32)
        kv_heads = metadata.get(f'{architecture}.attention.head_count_kv', heads)
    elif path.is_dir():
        config_path = path / 'config.json'
        if not config_path.is_file() or config_path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError('A Transformers package needs config.json, tokenizer files and safetensors weights')
        metadata = json.loads(config_path.read_text(encoding='utf-8'))
        if not isinstance(metadata, dict):
            raise ValueError('Transformers config.json must contain an object')
        if not (path / 'tokenizer.json').is_file() and not (path / 'tokenizer.model').is_file():
            raise ValueError('Tokenizer files are missing from this model package')
        files = sorted(path.rglob('*.safetensors'))
        if not files:
            raise ValueError('No safetensors weights found. Convert pickle weights or use an existing inference endpoint.')
        index = path / 'model.safetensors.index.json'
        if index.is_file():
            if index.stat().st_size > 8 * 1024 * 1024:
                raise ValueError('Safetensors shard index is too large')
            weight_map = json.loads(index.read_text(encoding='utf-8')).get('weight_map', {})
            if not weight_map or any(not isinstance(v, str) or not (path / v).resolve().is_relative_to(path)
                or not (path / v).is_file() or Path(v).suffix != '.safetensors' for v in weight_map.values()):
                raise ValueError('Safetensors model shards are missing or the index references external files')
        elif not (path / 'model.safetensors').is_file():
            raise ValueError('A complete Transformers package needs model.safetensors or a complete model.safetensors.index.json shard set')
        kind, architecture = 'transformers', metadata.get('model_type', 'unknown')
        layers, hidden = metadata.get('num_hidden_layers', 32), metadata.get('hidden_size', 4096)
        heads = metadata.get('num_attention_heads', 32)
        kv_heads = metadata.get('num_key_value_heads', heads)
        package_names = {'config.json', 'tokenizer.json', 'tokenizer_config.json', 'generation_config.json',
                         'special_tokens_map.json', 'added_tokens.json', 'model.safetensors.index.json',
                         'tokenizer.model', 'vocab.json', 'vocab.txt', 'merges.txt'}
        files += sorted(p for p in path.rglob('*') if p.is_file() and p.name in package_names)
    else:
        raise ValueError('Supported artifacts: GGUF or a complete Transformers safetensors folder. ONNX, GGML, PyTorch .pt/.bin and other formats require conversion or an inference endpoint.')
    if len(files) > 10000 or any(p.is_symlink() or (path.is_dir() and not p.resolve().is_relative_to(path)) for p in files):
        raise ValueError('Model package has too many files or external symbolic links')
    sizes = [(str(p.relative_to(path) if path.is_dir() else p.name), p.stat().st_size, p.stat().st_mtime_ns) for p in files]
    size = sum(item[1] for item in sizes)
    if size <= 0:
        raise ValueError('Model weights are empty')
    fingerprint = hashlib.sha256(json.dumps([str(path), sizes], sort_keys=True).encode()).hexdigest()
    kv_gib = 4 * max(1, int(layers)) * max(1, int(hidden)) * max(1, int(kv_heads)) / max(1, int(heads)) * context_length * concurrency / GIB
    weights = size / GIB
    # CPU Transformers often expand FP16 weights to FP32. Include this explicitly.
    ram = math.ceil(weights * (2.4 if kind == 'transformers' else 1.2) + kv_gib + 2)
    vram = math.ceil(weights * 1.15 + kv_gib + 1)
    return {'source': str(path), 'name': path.name, 'format': kind, 'architecture': architecture,
            'size_bytes': size, 'weights_gib': round(weights, 3), 'fingerprint': fingerprint,
            'context_length': context_length, 'concurrency': concurrency, 'file_count': len(files),
            'required_ram_gib': ram, 'recommended_vram_gib': vram,
            'kv_cache_gib': round(kv_gib, 2), 'files': [str(p) for p in files],
            'assumptions': ['Memory includes weights, estimated FP16 KV cache and runtime overhead.',
                'A capacity estimate is not a benchmark or a guarantee of model/runtime compatibility.']}


def artifact_digest(profile):
    """Content hash for scan→upload binding; metadata fingerprints only accelerate UI checks."""
    digest = hashlib.sha256()
    for filename in profile['files']:
        content = hashlib.sha256()
        with Path(filename).open('rb') as stream:
            while chunk := stream.read(4 * 1024 * 1024):
                content.update(chunk)
        digest.update(content.digest())
    return digest.hexdigest()


def capacity_check(profile, available_ram_bytes=None, available_vram_bytes=None):
    if available_ram_bytes is None:
        try:
            import psutil
            available_ram_bytes = psutil.virtual_memory().available
        except ImportError:
            return {'allowed': False, 'reason': 'RAM capacity could not be measured; install the hardware diagnostics dependency.'}
    available = available_ram_bytes / GIB
    required = profile['required_ram_gib']
    if available_vram_bytes is None:
        try:
            from core.local_model_server import detect_gpu
            gpu = detect_gpu()
            available_vram_bytes = gpu.get('vram_free_mb', 0) * 1024 ** 2
        except Exception:
            available_vram_bytes = 0
    if profile['format'] == 'gguf':
        required = max(math.ceil(profile['weights_gib'] + 2), required - int(available_vram_bytes / GIB * .8))
    return {'allowed': available >= required, 'available_ram_gib': round(available, 2),
            'required_ram_gib': required, 'recommended_vram_gib': profile['recommended_vram_gib'],
            'available_vram_gib': round(available_vram_bytes / GIB, 2),
            'reason': f'Estimated requirement with available GPU offload: {required} GiB system RAM; measured {available:.1f} GiB. CPU execution needs the full RAM estimate.'}
