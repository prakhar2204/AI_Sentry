"""Memory accounting for the desktop float32 CPU runtime."""
import json
import struct

from core.model_profile import inspect_scan_model


def test_only_loaded_weights_contribute_to_the_cpu_budget(tmp_path):
    config = {"num_hidden_layers": 32, "hidden_size": 4096, "num_attention_heads": 32}
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "tokenizer.json").write_text("{}")
    header = json.dumps({"w": {"dtype": "F16", "shape": [1048576],
                               "data_offsets": [0, 2097152]}}).encode()
    with (tmp_path / "model.safetensors").open("wb") as model:
        model.write(struct.pack("<Q", len(header)) + header)
        model.truncate(model.tell() + 2097152)
    (tmp_path / "other.safetensors").write_bytes(b"unrelated weights")
    profile = inspect_scan_model(str(tmp_path))
    assert profile["weights_gib"] == .002
    assert profile["runtime_weights_gib"] == .004
    assert profile["kv_cache_gib"] == 4
    assert profile["recommended_vram_gib"] == 0
