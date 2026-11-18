# Workflow alignment — 2026-11-16

The user's latest specification supersedes the earlier AWS-first/stub staging. The intended product is: agreement → model source and optional manifest → selected checks or complete scan → capacity gate → real engine orchestration → per-category evidence/confidence → optional report export → model-specific editable deployment recommendations and cost comparison → official CLI sign-in → verified identity/confirmation → upload/build/deploy the scanned model.

## Audit before this implementation

| Step | Existing behavior | Gap |
| --- | --- | --- |
| Agreement | First screen; acceptance gate tested | Preserve |
| Model input | GGUF path or HTTP endpoint; file extensions accepted more broadly than executable support | Modern Electron dropped-file path resolution; package inspection; distinguish model download URLs from inference APIs; enforce honest format support |
| Manifest/requirements | Optional JSON manifest and category checkboxes | Explicit Complete scan; preserve only selected categories |
| Capacity | Engine probe counts and NVIDIA utilization | No model-aware RAM requirement or hard capacity gate |
| Scan | Garak works locally; Auto picks one engine | Category-aware multi-engine scheduling and explicit coverage; missing PyRIT cannot silently become full coverage |
| Confidence | Finding confidence/risk scores | Per-category assessment evidence including no-findings/untested distinction; never call a heuristic percentage probability of safety |
| Reports | Optional JSON/HTML/TXT export | Direct deployment path without downloading; native PDF remains separately unverified |
| Recommendations | Mostly risk rules and fixed price ranges | Carry scanned model identity/size/runtime into every recommendation and editable estimate |
| Cloud flow | Separate planning/live wizards; AWS CLI login only | One continuous model-driven selection; Azure/GCP official CLI adapters and account/project selection |
| Deployment | AWS advanced templates require manually prepared artifacts | Upload/package/build the actual scanned model; managed-serving readiness and recovery |
| Distribution | Source launcher works; installed release old | Fresh packaged-release validation remains required |

No live cloud login, upload, billable provisioning or deployment is authorized for agent testing. All provider command tests must be mocked until explicit approval. The application itself must require the user's reviewed account, region, artifact and resource confirmation before mutations.

Resource estimates are bounds based on model size/context/runtime, not promised exact watts or GPU utilization. Cloud prices must carry source, date, region, usage assumptions and excluded charges. “Complete scan” means every implemented category/probe, not proof against every possible vulnerability. Unsupported formats must fail with actionable conversion/runtime guidance rather than being accepted and failing later.
