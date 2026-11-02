# AI-SENTRY — Third-Party Licenses

**Location:** `app/backend/THIRD_PARTY_LICENSES.md`
**Last Updated:** 2026-11-02
**Scope:** All direct runtime + engine dependencies of the Python backend.
Transitive dependencies pulled in by the packages below are listed in the
"PyRIT Transitive Dependencies" section.

---

## Scanning Engines

### garak 0.17.0
- **License:** Apache 2.0
- **Copyright:** NVIDIA Corporation and contributors
- **Source:** https://github.com/leondz/garak
- **PyPI:** https://pypi.org/project/garak/
- **Used for:** Primary LLM red-teaming probe engine (subprocess / CLI mode)
- **Decision ref:** D-002, D-018

### pyrit 1.1.0
- **License:** MIT
- **Copyright:** Copyright (c) Microsoft Corporation.
- **License text (extracted from package `licenses/LICENSE`):**

  ```
  MIT License

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
  ```

- **Source:** https://github.com/Azure/PyRIT
- **PyPI:** https://pypi.org/project/pyrit/
- **Used for:** Secondary LLM red-teaming engine (Python SDK, offline scorers only)
- **Decision ref:** D-008, D-019, D-020, D-021

---

## HTTP Client

### httpx 0.28.1
- **License:** BSD 3-Clause
- **Copyright:** Tom Christie and contributors
- **Source:** https://github.com/encode/httpx
- **PyPI:** https://pypi.org/project/httpx/
- **Used for:** HTTP client for endpoint validation and test requests

---

## Reports (optional — `pip install -e ".[reports]"`)

### weasyprint >=61.0,<62.0
- **License:** BSD License
- **Copyright:** Simon Sapin and contributors
- **Source:** https://github.com/Kozea/WeasyPrint
- **PyPI:** https://pypi.org/project/weasyprint/
- **Used for:** PDF report generation (Phase 6+)
- **Note:** Not installed in base dev environment. Decision ref: D-019.

---

## AWS Deployment (optional — `pip install -e ".[aws]"`)

### boto3 >=1.34,<2.0
- **License:** Apache 2.0
- **Copyright:** Amazon.com, Inc. or its affiliates
- **Source:** https://github.com/boto/boto3
- **PyPI:** https://pypi.org/project/boto3/
- **Used for:** AWS deployment engine (CloudFormation, SageMaker, IAM)
- **Decision ref:** D-006

---

## Dev / Test

| Package | Version | License |
|---|---|---|
| pytest | >=7.0 | MIT |
| pytest-cov | >=4.0 | MIT |
| ruff | >=0.4 | MIT |
| mypy | >=1.0 | MIT |
| respx | >=0.20 | BSD |

---

## PyRIT 1.1.0 — Direct Dependencies

The following packages are pulled in directly by `pyrit==1.1.0` (base install,
no optional extras). Listed for audit / licence-awareness purposes.

| Package | Constraint | Known License |
|---|---|---|
| PyJWT[crypto] | >=2.8.0 | MIT |
| SQLAlchemy | >=2.0.41 | MIT |
| aiofiles | >=24,<26 | Apache 2.0 |
| alembic | >=1.16.0 | MIT |
| appdirs | >=1.4.0 | MIT |
| art | >=6.5.0 | MIT |
| av | >=14.0.0 | BSD |
| azure-ai-contentsafety | >=1.0.0 | MIT |
| azure-core | >=1.38.0 | MIT |
| azure-identity | >=1.19.0 | MIT |
| azure-keyvault-secrets | >=4.9.0 | MIT |
| azure-storage-blob | >=12.19.0 | MIT |
| base2048 | >=0.1.3 | MIT |
| colorama | >=0.4.6 | BSD |
| confusable-homoglyphs | >=3.3.1 | **GPL-3.0** ⚠️ |
| confusables | >=1.2.0 | MIT |
| datasets | >=4.8.0 | Apache 2.0 |
| ecoji | >=0.1.1 | Apache 2.0 |
| fastapi | >=0.133.0 | MIT |
| httpx[http2] | >=0.27.2 | BSD |
| jinja2 | >=3.1.6 | BSD |
| numpy | >=1.26.0 | BSD |
| openai | >=2.2.0 | Apache 2.0 |
| openpyxl | >=3.1.5 | MIT |
| pillow | >=12.2.0 | HPND (PIL Historical) |
| pydantic | >=2.11.5 | MIT |
| pyodbc | >=5.1.0 | MIT-0 |
| pypdf | >=6.10.2 | BSD |
| python-docx | >=1.1.0 | MIT |
| python-dotenv | >=1.2.2 | BSD |
| reportlab | >=4.4.4 | BSD |
| scipy | >=1.15.3 | BSD |
| segno | >=1.6.6 | BSD |
| starlette | >=1.0.1 | BSD |
| tenacity | >=9.1.2 | Apache 2.0 |
| termcolor | >=2.4.0 | MIT |
| tinytag | >=2.2.1 | MIT |
| tqdm | >=4.67.1 | MPL-2.0 / MIT |
| transformers | >=5.0.0rc3 | Apache 2.0 |
| treelib | >=1.7.1 | Apache 2.0 |
| uvicorn[standard] | >=0.32.0 | BSD |
| websockets | >=14.0 | BSD |

> **GPL-3.0 note (`confusable-homoglyphs`):** AI-SENTRY distributes as a
> Python package (pip-installable). Under the standard interpretation of GPL
> for Python packages that are dynamically imported (not statically linked),
> this does not trigger copyleft for AI-SENTRY application code. If AI-SENTRY
> is ever bundled as a binary distribution (PyInstaller / cx_Freeze), a
> formal legal review of GPL-3.0 implications is required before release.

> **`datasets` version conflict:** `pyrit==1.1.0` requires `datasets>=4.8.0`.
> `garak==0.17.0` requires `datasets<4.0`. Both can coexist because Garak
> runs as a subprocess (CLI mode), not as an imported Python module inside the
> same process. The installed `datasets` version satisfies PyRIT; Garak never
> imports it from the same interpreter. See D-022 for the formal decision.

---

*Maintained manually. Update whenever a direct dependency is added, removed,
or version-pinned in `pyproject.toml`.*
