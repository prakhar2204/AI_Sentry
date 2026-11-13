"""Fix ScanPage.tsx to use local_model_path from state instead of state.target."""
import re

with open(r"d:\AI_Sentry\app\frontend\src\pages\ScanPage.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace the local_model_path block
idx = content.find("local_model_path = state.target")
if idx < 0:
    print("FAIL: local_model_path = state.target not found")
else:
    # Find the start of this block
    block_start = content.rfind("// Attach engine", 0, idx)
    block_end = content.find("\n\n", idx) + 2
    old_block = content[block_start:block_end]
    print("OLD BLOCK:")
    print(repr(old_block))
    
    new_block = """    // Attach engine from state so Python backend uses the right engine
    (config as any).engine = state.engine || "mock";

    // For local mode with a .gguf file: pass local_model_path to backend.
    // The Python backend auto-launches llama.cpp server with CUDA GPU acceleration.
    // local_model_path is the REAL full disk path from the Electron native file picker.
    const localModelPath = (state as any).local_model_path as string | null;
    if (state.mode === "local" && localModelPath && !localModelPath.startsWith("http")) {
      (config as any).local_model_path = localModelPath;
      config.target = "http://127.0.0.1:11500/v1/chat/completions";
    }

"""
    content = content[:block_start] + new_block + content[block_end:]
    with open(r"d:\AI_Sentry\app\frontend\src\pages\ScanPage.tsx", "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: ScanPage.tsx patched")
