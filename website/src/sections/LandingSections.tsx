'use client';

import s from './landing.module.css';
import btnStyles from '../components/Button.module.css';

/* ════════════════════════════════════════════════
   HERO SECTION
   ════════════════════════════════════════════════ */
export function HeroSection() {
  return (
    <section className={s.hero} id="hero">
      <div className={s.heroBg} aria-hidden="true" />
      <div className={s.heroInner}>
        <div className={s.heroContent}>
          <span className={s.heroTag}>LLM Vulnerability Scanner</span>
          <h1 className={s.heroTitle}>
            Scan Your AI Before<br />You Ship Your AI.
          </h1>
          <p className={s.heroSub}>
            AI-SENTRY runs Garak, PyRIT, and DeepTeam simultaneously,
            normalizes the results, and tells you exactly what is wrong
            and how to fix it. Before your model reaches production.
          </p>
          <div className={s.heroCtas}>
            <a href="/download" className={`${btnStyles.btnPrimary} ${btnStyles.btnLg}`}>
              <span className={btnStyles.btnDownloadArrow}>↓</span>
              Download for Windows
            </a>
            <a href="/download" className={`${btnStyles.btnSecondary} ${btnStyles.btnLg}`}>
              <span className={btnStyles.btnDownloadArrow}>↓</span>
              Download for Linux
            </a>
          </div>
          <p className={s.heroMeta}>
            v1.0.0 — Free &amp; Open Source &nbsp;·&nbsp; Windows 10+ &nbsp;·&nbsp; Ubuntu 20.04+
          </p>
        </div>

        {/* Hero visualization — scan animation */}
        <div className={s.heroViz} aria-hidden="true">
          <svg className={s.vizSvg} viewBox="0 0 480 480" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Central LLM node */}
            <g>
              <polygon points="240,160 300,200 300,280 240,320 180,280 180,200"
                stroke="#363B47" strokeWidth="1.5" fill="none" opacity="0.6">
                <animate attributeName="opacity" values="0.4;0.8;0.4" dur="4s" repeatCount="indefinite" />
              </polygon>
              <text x="240" y="248" textAnchor="middle" fill="#5C6070" fontSize="13"
                fontFamily="Inter, sans-serif" fontWeight="500">LLM</text>
            </g>

            {/* Engine 1 — Garak */}
            <g>
              <circle cx="80" cy="100" r="6" fill="#3D7EFF" opacity="0.7">
                <animate attributeName="opacity" values="0.5;1;0.5" dur="3s" repeatCount="indefinite" />
              </circle>
              <text x="80" y="88" textAnchor="middle" fill="#5C6070" fontSize="10"
                fontFamily="Inter, sans-serif">GARAK</text>
              <line x1="86" y1="100" x2="180" y2="210" stroke="#3D7EFF" strokeWidth="1" opacity="0.3">
                <animate attributeName="opacity" values="0;0.6;0" dur="6s" repeatCount="indefinite" begin="0s" />
              </line>
            </g>

            {/* Engine 2 — PyRIT */}
            <g>
              <circle cx="400" cy="100" r="6" fill="#3D7EFF" opacity="0.7">
                <animate attributeName="opacity" values="0.5;1;0.5" dur="3s" repeatCount="indefinite" begin="1s" />
              </circle>
              <text x="400" y="88" textAnchor="middle" fill="#5C6070" fontSize="10"
                fontFamily="Inter, sans-serif">PYRIT</text>
              <line x1="394" y1="100" x2="300" y2="210" stroke="#3D7EFF" strokeWidth="1" opacity="0.3">
                <animate attributeName="opacity" values="0;0.6;0" dur="6s" repeatCount="indefinite" begin="1s" />
              </line>
            </g>

            {/* Engine 3 — DeepTeam */}
            <g>
              <circle cx="240" cy="420" r="6" fill="#3D7EFF" opacity="0.7">
                <animate attributeName="opacity" values="0.5;1;0.5" dur="3s" repeatCount="indefinite" begin="2s" />
              </circle>
              <text x="240" y="450" textAnchor="middle" fill="#5C6070" fontSize="10"
                fontFamily="Inter, sans-serif">DEEPTEAM</text>
              <line x1="240" y1="414" x2="240" y2="320" stroke="#3D7EFF" strokeWidth="1" opacity="0.3">
                <animate attributeName="opacity" values="0;0.6;0" dur="6s" repeatCount="indefinite" begin="2s" />
              </line>
            </g>

            {/* Vulnerability dots — appear when beams hit */}
            <circle cx="210" cy="220" r="4" fill="#FF4040" opacity="0">
              <animate attributeName="opacity" values="0;0.8;0" dur="6s" repeatCount="indefinite" begin="1.5s" />
            </circle>
            <circle cx="260" cy="200" r="4" fill="#FF8C00" opacity="0">
              <animate attributeName="opacity" values="0;0.8;0" dur="6s" repeatCount="indefinite" begin="2.5s" />
            </circle>
            <circle cx="270" cy="270" r="4" fill="#FFD700" opacity="0">
              <animate attributeName="opacity" values="0;0.8;0" dur="6s" repeatCount="indefinite" begin="3.5s" />
            </circle>
            <circle cx="200" cy="260" r="4" fill="#3DFF9A" opacity="0">
              <animate attributeName="opacity" values="0;0.8;0" dur="6s" repeatCount="indefinite" begin="4s" />
            </circle>
          </svg>
        </div>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   TRUST BAR
   ════════════════════════════════════════════════ */
export function TrustBar() {
  return (
    <div className={s.trustBar}>
      <div className={s.trustInner}>
        <div className={s.trustEngines}>
          <span className={s.trustEngine}>
            <span className={s.trustEngineDot} /> Garak — NVIDIA Research
          </span>
          <span className={s.trustEngine}>
            <span className={s.trustEngineDot} /> PyRIT — Microsoft
          </span>
          <span className={s.trustEngine}>
            <span className={s.trustEngineDot} /> DeepTeam — Confident AI
          </span>
        </div>
        <p className={s.trustSub}>
          Built on the same scanning engines used by AI security researchers worldwide.
        </p>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════
   PROBLEM / SOLUTION
   ════════════════════════════════════════════════ */
export function ProblemSolution() {
  return (
    <section className={s.problemSolution} id="problem">
      <div className={s.psInner}>
        <div className={`${s.psBlock} animate-in`}>
          <h2 className={s.psTitle}>The Security Gap<br />No One Talks About</h2>
          <p className={s.psBody}>
            Three world-class LLM security tools exist.
            Each has a different interface, different output,
            and different setup process. Most teams run none.
            Some run one — and miss the other two.
          </p>
          <div className={s.psCallouts}>
            <div className={s.psCalloutWarn}>⚠ Garak output: raw JSONL probing logs</div>
            <div className={s.psCalloutWarn}>⚠ PyRIT output: multi-turn conversation traces</div>
            <div className={s.psCalloutWarn}>⚠ DeepTeam output: metric evaluation scores</div>
          </div>
        </div>

        <div className={s.psDivider} />

        <div className={`${s.psBlock} animate-in`}>
          <h2 className={s.psTitle}>One Tool. Three Engines.<br />One Report.</h2>
          <p className={s.psBody}>
            AI-SENTRY wraps Garak, PyRIT, and DeepTeam into a single
            workflow. Input your model endpoint or GGUF file.
            Get a unified, scored, and actionable security report — 
            in under two hours. Then deploy securely.
          </p>
          <div className={s.psCallouts}>
            <div className={s.psCalloutOk}>✓ Normalized VulnerabilityFinding schema</div>
            <div className={s.psCalloutOk}>✓ Severity + Confidence scored separately</div>
            <div className={s.psCalloutOk}>✓ Three levels of remediation per finding</div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   FEATURE HIGHLIGHTS
   ════════════════════════════════════════════════ */
const FEATURES = [
  {
    icon: '◎',
    title: 'All Three Engines. One Scan.',
    body: 'Garak, PyRIT, and DeepTeam run in parallel. No duplicate setup. No format translation. Full cross-engine finding corroboration.',
    tag: 'OWASP LLM TOP 10',
  },
  {
    icon: '⊞',
    title: 'Scores That Show Their Work.',
    body: 'Severity and confidence are not the same metric. AI-SENTRY shows both — with a plain-English rationale for every number it produces.',
    tag: 'DUAL-AXIS SCORING',
  },
  {
    icon: '⬡',
    title: 'From Report to AWS in Minutes.',
    body: 'The Deployment Advisor reads your risk profile and configures Bedrock Guardrails, IAM roles, and CloudWatch alarms. One click to apply.',
    tag: 'AWS DEPLOYMENT',
  },
  {
    icon: '⟐',
    title: 'Three Levels of Fix.',
    body: 'Every finding includes remediation at model level, system level, and deployment level. A vulnerability report that tells you how to fix it.',
    tag: 'REMEDIATION ENGINE',
  },
  {
    icon: '⊡',
    title: 'Reports for Every Audience.',
    body: 'PDF for stakeholders and compliance. HTML for sharing. JSON for CI/CD pipelines. Every format includes the OWASP coverage map.',
    tag: 'PDF · HTML · JSON',
  },
  {
    icon: '⊘',
    title: 'Privacy by Architecture.',
    body: 'API keys in OS keychain only. Probe content encrypted at rest. Local GGUF scans are fully air-gapped. No telemetry by default.',
    tag: 'ZERO TRUST',
  },
];

export function FeaturesSection() {
  return (
    <section className={s.features} id="features">
      <div className={s.featuresInner}>
        <div className={s.sectionHeader}>
          <span className={s.sectionLabel}>Features</span>
          <h2 className={s.sectionTitle}>Everything You Need to Validate an LLM</h2>
          <p className={s.sectionSub}>
            Not a single scanner. An orchestration platform.
          </p>
        </div>
        <div className={`${s.featuresGrid} stagger`}>
          {FEATURES.map((f) => (
            <div key={f.title} className={`${s.featureCard} animate-in`}>
              <div className={s.featureIcon}>{f.icon}</div>
              <h3 className={s.featureTitle}>{f.title}</h3>
              <p className={s.featureBody}>{f.body}</p>
              <span className={s.featureTag}>{f.tag}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   HOW IT WORKS
   ════════════════════════════════════════════════ */
const STEPS = [
  {
    num: '1',
    title: 'Connect Your Model',
    body: 'Paste your API endpoint and key — or drop a GGUF model file. AI-SENTRY validates the connection and estimates cost before anything runs.',
  },
  {
    num: '2',
    title: 'Configure the Scan',
    body: 'Choose Quick, Standard, or Deep scan depth. Review estimated cost, duration, and probe categories. Nothing runs without your approval.',
  },
  {
    num: '3',
    title: 'Watch It Scan',
    body: 'All three engines run in parallel. Findings appear in real-time. The rate limiter protects your API budget. Pause or cancel anytime.',
  },
  {
    num: '4',
    title: 'Report & Deploy',
    body: 'Your unified report is scored, explained, and actionable. Every finding has remediation. The Deployment Advisor configures secure AWS infrastructure.',
  },
];

export function HowItWorksSection() {
  return (
    <section className={s.howItWorks} id="how-it-works">
      <div className={s.hiwInner}>
        <div className={s.sectionHeader}>
          <span className={s.sectionLabel}>How It Works</span>
          <h2 className={s.sectionTitle}>From Model to Secure Deployment</h2>
          <p className={s.sectionSub}>
            Four steps. No setup. No terminal. No guesswork.
          </p>
        </div>
        <div className={`${s.hiwSteps} stagger`}>
          {STEPS.map((step) => (
            <div key={step.num} className={`${s.hiwStep} animate-in`}>
              <div className={s.hiwNum}>{step.num}</div>
              <h3 className={s.hiwTitle}>{step.title}</h3>
              <p className={s.hiwBody}>{step.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   CAPABILITIES (ENGINE DEEP DIVE)
   ════════════════════════════════════════════════ */
const ENGINES = [
  {
    name: 'Garak',
    org: 'NVIDIA Research',
    desc: 'Systematic probe-based scanning. 100+ probe types. OWASP-mapped. Reproducible and deterministic by seed.',
    finds: 'Finds: injection, jailbreak, refusal failures',
  },
  {
    name: 'PyRIT',
    org: 'Microsoft',
    desc: 'Multi-turn adversarial simulation. Dialogue-dependent vulnerabilities. Red team conversation orchestration.',
    finds: 'Finds: session escalation, context manipulation',
  },
  {
    name: 'DeepTeam',
    org: 'Confident AI',
    desc: 'Metric-driven evaluation framework. Bias, hallucination, toxicity scoring with quantitative thresholds.',
    finds: 'Finds: systematic bias, factual drift, toxicity',
  },
];

export function CapabilitiesSection() {
  return (
    <section className={s.capabilities} id="capabilities">
      <div className={s.capInner}>
        <div className={s.sectionHeader}>
          <span className={s.sectionLabel}>Three Engines</span>
          <h2 className={s.sectionTitle}>Each Engine Tests a Different Failure Mode</h2>
          <p className={s.sectionSub}>
            Running only one gives you partial coverage in a format only that engine understands.
          </p>
        </div>
        <div className={`${s.capGrid} stagger`}>
          {ENGINES.map((e) => (
            <div key={e.name} className={`${s.capCard} animate-in`}>
              <div className={s.capOrg}>{e.org}</div>
              <h3 className={s.capName}>{e.name}</h3>
              <p className={s.capDesc}>{e.desc}</p>
              <span className={s.capFinds}>{e.finds}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   CLOUD DEPLOYMENT
   ════════════════════════════════════════════════ */
export function CloudSection() {
  return (
    <section className={s.cloud} id="cloud">
      <div className={s.cloudInner}>
        <div className={s.sectionHeader}>
          <span className={s.sectionLabel}>Deployment</span>
          <h2 className={s.sectionTitle}>From Report to Secure Deployment</h2>
          <p className={s.sectionSub}>
            The Deployment Advisor reads your risk profile and generates a secure cloud configuration.
            For AWS: one-click execution. No Terraform. No console.
          </p>
        </div>
        <table className={s.cloudTable}>
          <thead>
            <tr>
              <th>Capability</th>
              <th>AWS</th>
              <th>Azure</th>
              <th>GCP</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Estimated monthly cost</td>
              <td>$142/mo</td>
              <td>$167/mo</td>
              <td>$139/mo</td>
            </tr>
            <tr>
              <td>Native Guardrails</td>
              <td><span className={s.cloudCheck}>✓ Bedrock</span></td>
              <td>Manual</td>
              <td><span className={s.cloudCross}>—</span></td>
            </tr>
            <tr>
              <td>One-click deploy</td>
              <td><span className={s.cloudCheck}>✓</span></td>
              <td><span className={s.cloudCross}>—</span></td>
              <td><span className={s.cloudCross}>—</span></td>
            </tr>
            <tr>
              <td>IAM auto-config</td>
              <td><span className={s.cloudCheck}>✓</span></td>
              <td><span className={s.cloudCross}>—</span></td>
              <td><span className={s.cloudCross}>—</span></td>
            </tr>
            <tr>
              <td>Monitoring alarms</td>
              <td><span className={s.cloudCheck}>✓ CloudWatch</span></td>
              <td>Manual</td>
              <td>Manual</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   PRODUCT PREVIEW
   ════════════════════════════════════════════════ */
export function ProductPreview() {
  return (
    <section className={s.productPreview} id="product-preview">
      <div className={s.ppInner}>
        <div className={s.sectionHeader}>
          <span className={s.sectionLabel}>Product</span>
          <h2 className={s.sectionTitle}>See It In Action</h2>
          <p className={s.sectionSub}>
            Live scan progress across all three engines with real-time finding detection.
          </p>
        </div>

        <div className={`${s.ppWindow} animate-in`}>
          <div className={s.ppTitlebar}>
            <span className={s.ppDot} />
            <span className={s.ppDot} />
            <span className={s.ppDot} />
          </div>
          <div className={s.ppContent}>
            <div>
              <div className={s.ppLabel}>Security Scan — https://api.example.com/v1/chat</div>
            </div>

            <div className={s.ppProgress}>
              <div className={s.ppProgressLabel}>
                <span>Executing security probes</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>73%</span>
              </div>
              <div className={s.ppProgressBar}>
                <div className={s.ppProgressFill} />
              </div>
              <div className={s.ppProgressLabel}>
                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>73 / 100 probes</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Elapsed: 47s</span>
              </div>
            </div>

            <div className={s.ppCategories}>
              <div className={s.ppLabel}>Category Progress</div>
              <div className={s.ppCatRow}>
                <span className={s.ppCatName}>Prompt Injection</span>
                <span className={s.ppBadgeComplete}>Complete</span>
              </div>
              <div className={s.ppCatRow}>
                <span className={s.ppCatName}>Jailbreak Resistance</span>
                <span className={s.ppBadgeComplete}>Complete</span>
              </div>
              <div className={s.ppCatRow}>
                <span className={s.ppCatName}>Data Leakage Detection</span>
                <span className={s.ppBadgeActive}>Active</span>
              </div>
              <div className={s.ppCatRow}>
                <span className={s.ppCatName}>Harmful Output Analysis</span>
                <span className={s.ppBadgeQueued}>Queued</span>
              </div>
            </div>
          </div>
        </div>

        <p className={s.ppCaption}>
          Live scan progress with category tracking and real-time activity feed.
        </p>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   OWASP COVERAGE
   ════════════════════════════════════════════════ */
const OWASP_ITEMS = [
  { id: 'LLM01', name: 'Prompt Injection', status: 'Full', level: 'full' },
  { id: 'LLM02', name: 'Insecure Output', status: 'Full', level: 'full' },
  { id: 'LLM03', name: 'Training Data Poison', status: 'Partial', level: 'partial' },
  { id: 'LLM04', name: 'Denial of Service', status: 'Partial', level: 'partial' },
  { id: 'LLM05', name: 'Supply Chain', status: 'Advisory', level: 'none' },
  { id: 'LLM06', name: 'Sensitive Information', status: 'Full', level: 'full' },
  { id: 'LLM07', name: 'Insecure Plugin Design', status: 'N/A', level: 'none' },
  { id: 'LLM08', name: 'Excessive Agency', status: 'Partial', level: 'partial' },
  { id: 'LLM09', name: 'Overreliance', status: 'Full', level: 'full' },
  { id: 'LLM10', name: 'Model Theft', status: 'Not in scope', level: 'none' },
];

export function OwaspSection() {
  return (
    <section className={s.owasp}>
      <div className={s.owaspInner}>
        <div className={s.sectionHeader}>
          <span className={s.sectionLabel}>Coverage</span>
          <h2 className={s.sectionTitle}>OWASP LLM Top 10 Coverage</h2>
          <p className={s.sectionSub}>
            We show what we cover — and what we do not.
          </p>
        </div>
        <div className={s.owaspGrid}>
          {OWASP_ITEMS.map((item) => (
            <div key={item.id} className={s.owaspItem}>
              <div className={`${s.owaspDot} ${
                item.level === 'full' ? s.owaspFull :
                item.level === 'partial' ? s.owaspPartial :
                s.owaspNone
              }`} />
              <span className={s.owaspId}>{item.id}</span>
              <span className={s.owaspName}>{item.name}</span>
              <span className={s.owaspStatus}>{item.status}</span>
            </div>
          ))}
        </div>
        <p className={s.owaspNote}>
          Incomplete coverage maps are a red flag — we don&apos;t hide ours.
        </p>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   FUTURE SCOPE
   ════════════════════════════════════════════════ */
const ROADMAP = [
  {
    version: 'v1.0 — Foundation',
    date: 'Released October 2026',
    items: [
      'Multi-engine orchestration (Garak + PyRIT + DeepTeam)',
      'Unified VulnerabilityFinding schema v1.0',
      'Explainable dual-axis confidence scoring',
      'AWS one-click deployment with Bedrock Guardrails',
      'Report export: PDF, HTML, JSON',
    ],
  },
  {
    version: 'v1.5 — Developer Workflow',
    date: 'Target: Q1 2027',
    items: [
      'CLI interface for terminal-first developers',
      'GitHub Actions integration (scan in CI/CD pipeline)',
      'Azure + GCP one-click deployment',
      'Scan comparison: regression detection across runs',
    ],
  },
  {
    version: 'v2.0 — Platform',
    date: 'Target: Q3 2027',
    items: [
      'SaaS offering with team collaboration',
      'Native GitHub App for CI/CD integration',
      'Model version tracking and regression history',
      'Multi-modal scanning (vision-language models)',
    ],
  },
];

export function FutureSection() {
  return (
    <section className={s.future} id="roadmap">
      <div className={s.futureInner}>
        <div className={s.sectionHeader}>
          <span className={s.sectionLabel}>Roadmap</span>
          <h2 className={s.sectionTitle}>What Comes Next</h2>
          <p className={s.sectionSub}>
            Active development. Public roadmap. No guessing.
          </p>
        </div>
        <div className={s.futureTimeline}>
          {ROADMAP.map((phase) => (
            <div key={phase.version} className={`${s.futureItem} animate-in`}>
              <h3 className={s.futureVersion}>{phase.version}</h3>
              <div className={s.futureDate}>{phase.date}</div>
              <div className={s.futureList}>
                {phase.items.map((item) => (
                  <div key={item} className={s.futureListItem}>{item}</div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   FINAL CTA
   ════════════════════════════════════════════════ */
export function FinalCTA() {
  return (
    <section className={s.finalCta} id="download-cta">
      <div className={s.ctaInner}>
        <h2 className={s.ctaTitle}>Stop guessing. Start scanning.</h2>
        <p className={s.ctaSub}>
          Free. Open source. No setup required. No server.
          Download and run your first scan today.
        </p>
        <div className={s.ctaButtons}>
          <a href="/download" className={`${btnStyles.btnPrimary} ${btnStyles.btnLg}`}>
            <span className={btnStyles.btnDownloadArrow}>↓</span>
            Download for Windows
          </a>
          <a href="/download" className={`${btnStyles.btnSecondary} ${btnStyles.btnLg}`}>
            <span className={btnStyles.btnDownloadArrow}>↓</span>
            Download for Linux
          </a>
        </div>
        <p className={s.ctaMeta}>
          v1.0.0 &nbsp;·&nbsp; Windows 10+ &nbsp;·&nbsp; Ubuntu 20.04+
        </p>
      </div>
    </section>
  );
}
