"""
AI-SENTRY Visual Test Runner
Runs all test scenarios, captures output, writes JSON results.
Run from: d:\AI_Sentry\app\backend\
"""
import subprocess, sys, json, os, time

PYTHON = sys.executable
MAIN   = os.path.join(os.path.dirname(__file__), "__main__.py")

def run(args, stdin_text=""):
    """Run the CLI with given args and optional stdin."""
    t0 = time.monotonic()
    result = subprocess.run(
        [PYTHON, MAIN] + args,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=20,
        cwd=os.path.dirname(MAIN),
    )
    elapsed = int((time.monotonic() - t0) * 1000)
    combined = (result.stdout + result.stderr).strip()
    return {
        "exit_code": result.returncode,
        "output": combined,
        "ms": elapsed,
    }

def run_pytest():
    t0 = time.monotonic()
    result = subprocess.run(
        [PYTHON, "-m", "pytest", "tests/", "-v", "--tb=short", "--no-header"],
        capture_output=True, text=True, timeout=60,
        cwd=os.path.dirname(MAIN),
    )
    elapsed = int((time.monotonic() - t0) * 1000)
    return {
        "exit_code": result.returncode,
        "output": (result.stdout + result.stderr).strip(),
        "ms": elapsed,
    }

print("Running AI-SENTRY visual tests...")

scenarios = [
    {
        "id": "T01",
        "name": "Help / Usage",
        "cmd": "--help",
        "stdin": "",
        "expect_exit": 0,
        "category": "CLI",
    },
    {
        "id": "T02",
        "name": "Version Flag",
        "cmd": "version",
        "stdin": "",
        "expect_exit": 0,
        "category": "CLI",
    },
    {
        "id": "T03",
        "name": "Scan Help",
        "cmd": "scan --help",
        "stdin": "",
        "expect_exit": 0,
        "category": "CLI",
    },
    {
        "id": "T04",
        "name": "Consent: User Agrees (yes)",
        "cmd": "scan --target https://httpbin.org/post",
        "stdin": "yes\n",
        "expect_exit": 0,
        "category": "Consent Gate",
    },
    {
        "id": "T05",
        "name": "Consent: User Declines (no)",
        "cmd": "scan --target https://httpbin.org/post",
        "stdin": "no\n",
        "expect_exit": 0,
        "category": "Consent Gate",
    },
    {
        "id": "T06",
        "name": "Consent: Invalid then Yes",
        "cmd": "scan --target https://httpbin.org/post",
        "stdin": "maybe\nyes\n",
        "expect_exit": 0,
        "category": "Consent Gate",
    },
    {
        "id": "T07",
        "name": "Consent: Three Invalids - Auto Exit",
        "cmd": "scan --target https://httpbin.org/post",
        "stdin": "blah\nblah\nblah\n",
        "expect_exit": 0,
        "category": "Consent Gate",
    },
    {
        "id": "T08",
        "name": "Validation: Empty Target",
        "cmd": "scan --target \"\"",
        "stdin": "yes\n",
        "expect_exit": 1,
        "category": "Endpoint Validation",
    },
    {
        "id": "T09",
        "name": "Validation: No HTTP Scheme",
        "cmd": "scan --target api.openai.com",
        "stdin": "yes\n",
        "expect_exit": 1,
        "category": "Endpoint Validation",
    },
    {
        "id": "T10",
        "name": "Validation: FTP Scheme Rejected",
        "cmd": "scan --target ftp://files.example.com",
        "stdin": "yes\n",
        "expect_exit": 1,
        "category": "Endpoint Validation",
    },
    {
        "id": "T11",
        "name": "Validation: Local GGUF Rejected (Phase 2)",
        "cmd": "scan --target model.gguf",
        "stdin": "yes\n",
        "expect_exit": 1,
        "category": "Endpoint Validation",
    },
    {
        "id": "T12",
        "name": "Validation: Windows Path Rejected",
        "cmd": "scan --target C:\\models\\llama.gguf",
        "stdin": "yes\n",
        "expect_exit": 1,
        "category": "Endpoint Validation",
    },
    {
        "id": "T13",
        "name": "Live Probe: httpbin.org (Public Test API)",
        "cmd": "scan --target https://httpbin.org/post",
        "stdin": "yes\n",
        "expect_exit": 0,
        "category": "Live Probe",
        "note": "httpbin.org echoes POST body — not an LLM, so response won't be OpenAI format. Tests network reachability.",
    },
    {
        "id": "T14",
        "name": "Live Probe: Unreachable Host",
        "cmd": "scan --target https://this-host-does-not-exist-aisentry.io/v1",
        "stdin": "yes\n",
        "expect_exit": 1,
        "category": "Live Probe",
    },
    {
        "id": "T15",
        "name": "Healthcheck Command",
        "cmd": "healthcheck",
        "stdin": "",
        "expect_exit": 0,
        "category": "CLI",
    },
    {
        "id": "T16",
        "name": "Missing --target Flag",
        "cmd": "scan",
        "stdin": "",
        "expect_exit": 2,
        "category": "CLI",
    },
]

results = []

for s in scenarios:
    print(f"  {s['id']}: {s['name']}...")
    args = s["cmd"].split()
    r = run(args, stdin_text=s["stdin"])
    passed = (r["exit_code"] == s["expect_exit"])
    results.append({
        **s,
        **r,
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
    })

# Run unit tests
print("  UNIT: Running pytest...")
unit = run_pytest()
unit_passed = unit["exit_code"] == 0

output = {
    "scenarios": results,
    "unit_tests": {**unit, "passed": unit_passed, "status": "PASS" if unit_passed else "FAIL"},
    "summary": {
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
    }
}

with open("visual_test_results.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

p = output["summary"]["passed"]
t = output["summary"]["total"]
print(f"\nDone. {p}/{t} scenarios passed. Results in visual_test_results.json")
