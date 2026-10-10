'use client';

import s from './landing.module.css';

/* ════════════════════════════════════════════════
   HERO SECTION
   ════════════════════════════════════════════════ */
export function HeroSection() {
  return (
    <section className={s.hero} id="hero">
      <div className={s.heroBg} aria-hidden="true" />
      <div className={s.heroGlow} aria-hidden="true" />
      <div className={s.heroInner}>
        <div className={s.heroContent}>
          <span className={s.heroTag}>Pre-Deployment Security Platform</span>
          <h1 className={s.heroTitle}>
            Validate your AI<br />
            <span className={s.heroAccent}>before it ships.</span>
          </h1>
          <p className={s.heroSub}>
            Sentryɸ runs multi-layer security analysis, adaptive vulnerability
            detection, and model behavior stress testing — in a single scan.
            One report. Every risk. Actionable fixes.
          </p>
          <div className={s.heroCtas}>
            <a href="/download" className={s.heroPrimary}>
              Get Started — Free
              <span className={s.heroArrow}>→</span>
            </a>
            <a href="#how-it-works" className={s.heroSecondary}>
              See How It Works
            </a>
          </div>
          <p className={s.heroMeta}>
            Free &amp; open source &nbsp;·&nbsp; Windows 10+ &nbsp;·&nbsp; Ubuntu 20.04+ &nbsp;·&nbsp; No account required
          </p>
        </div>

        {/* Hero visualization — Grid scanner */}
        <div className={s.heroViz} aria-hidden="true">
          <div className={s.vizGrid}>
            {/* Scanning grid */}
            {Array.from({ length: 64 }, (_, i) => (
              <div
                key={i}
                className={s.vizCell}
                style={{
                  animationDelay: `${(i % 8) * 120 + Math.floor(i / 8) * 80}ms`,
                }}
              />
            ))}
          </div>
          <div className={s.vizScanLine} />
          <div className={s.vizOverlay}>
            <div className={s.vizLabel}>SCANNING</div>
            <div className={s.vizMetric}>
              <span className={s.vizMetricValue}>24</span>
              <span className={s.vizMetricUnit}>vulnerabilities detected</span>
            </div>
            <div className={s.vizRisk}>
              <span className={s.vizRiskDot} />
              Risk Level: High
            </div>
          </div>
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
        <div className={s.trustItems}>
          <span className={s.trustItem}>
            <span className={s.trustDot} /> Multi-Layer Security Analysis
          </span>
          <span className={s.trustSep}>·</span>
          <span className={s.trustItem}>
            <span className={s.trustDot} /> Adaptive Vulnerability Detection
          </span>
          <span className={s.trustSep}>·</span>
          <span className={s.trustItem}>
            <span className={s.trustDot} /> Model Behavior Stress Testing
          </span>
          <span className={s.trustSep}>·</span>
          <span className={s.trustItem}>
            <span className={s.trustDot} /> Pre-Deployment Validation Pipeline
          </span>
        </div>
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
        <div className={`${s.psBlock} animate-left`}>
          <div className={s.psLabel}>The Problem</div>
          <h2 className={s.psTitle}>LLMs ship with<br />unknown risks.</h2>
          <p className={s.psBody}>
            Most teams deploy language models with no security validation.
            The ones that do run a single scanner — missing entire categories
            of vulnerabilities that only surface under different testing methodologies.
          </p>
          <div className={s.psCallouts}>
            <div className={s.psCalloutWarn}>
              <span className={s.psIcon}>!</span>
              Fragmented tooling with incompatible outputs
            </div>
            <div className={s.psCalloutWarn}>
              <span className={s.psIcon}>!</span>
              No unified scoring across analysis methods
            </div>
            <div className={s.psCalloutWarn}>
              <span className={s.psIcon}>!</span>
              Manual setup blocks adoption at every step
            </div>
          </div>
        </div>

        <div className={s.psDivider} />

        <div className={`${s.psBlock} animate-right`}>
          <div className={s.psSolveLabel}>The Solution</div>
          <h2 className={s.psTitle}>One platform.<br />Complete coverage.</h2>
          <p className={s.psBody}>
            Sentryɸ orchestrates multiple security analysis layers into a single,
            automated pipeline. Input your model endpoint. Get a unified, scored,
            and actionable security report — in minutes, not days.
          </p>
          <div className={s.psCallouts}>
            <div className={s.psCalloutOk}>
              <span className={s.psCheckIcon}>✓</span>
              Normalized vulnerability schema with evidence
            </div>
            <div className={s.psCalloutOk}>
              <span className={s.psCheckIcon}>✓</span>
              Dual-axis scoring: severity + confidence
            </div>
            <div className={s.psCalloutOk}>
              <span className={s.psCheckIcon}>✓</span>
              Three levels of remediation per finding
            </div>
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
    title: 'Multi-Layer Scanning',
    body: 'Multiple security analysis engines run in parallel. No duplicate setup. No format translation. Full cross-method finding corroboration.',
    tag: 'OWASP LLM TOP 10',
  },
  {
    icon: '⊞',
    title: 'Explainable Scoring',
    body: 'Severity and confidence are scored independently — with a plain-English rationale for every number. No black-box risk ratings.',
    tag: 'DUAL-AXIS SCORING',
  },
  {
    icon: '⬡',
    title: 'Secure Deployment',
    body: 'The Deployment Advisor reads your risk profile and configures guardrails, IAM policies, and monitoring alarms. One click to apply.',
    tag: 'CLOUD DEPLOYMENT',
  },
  {
    icon: '⟐',
    title: 'Actionable Remediation',
    body: 'Every finding includes fixes at model level, system level, and deployment level. A vulnerability report that tells you how to fix it.',
    tag: 'THREE-LAYER FIX',
  },
  {
    icon: '⊡',
    title: 'Multi-Format Reports',
    body: 'PDF for stakeholders and compliance. HTML for sharing. JSON for CI/CD pipelines. Every format includes the OWASP coverage map.',
    tag: 'PDF · HTML · JSON',
  },
  {
    icon: '⊘',
    title: 'Privacy by Architecture',
    body: 'API keys in OS keychain only. Probe content encrypted at rest. Local model scans are fully air-gapped. Zero telemetry by default.',
    tag: 'ZERO TRUST',
  },
];

export function FeaturesSection() {
  return (
    <section className={s.features} id="features">
      <div className={s.featuresInner}>
        <div className={`${s.sectionHeader} animate-in`}>
          <span className={s.sectionLabel}>Capabilities</span>
          <h2 className={s.sectionTitle}>Everything you need to validate an LLM.</h2>
          <p className={s.sectionSub}>
            Not a single scanner. A complete pre-deployment security platform.
          </p>
        </div>
        <div className={`${s.featuresGrid} stagger`}>
          {FEATURES.map((f) => (
            <div key={f.title} className={`${s.featureCard} animate-scale`}>
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
    num: '01',
    title: 'Connect',
    body: 'Paste your API endpoint and key — or drop a local model file. Sentryɸ validates the connection and estimates cost before anything runs.',
  },
  {
    num: '02',
    title: 'Configure',
    body: 'Choose Quick, Standard, or Deep scan depth. Review estimated cost, duration, and test categories. Nothing executes without your explicit approval.',
  },
  {
    num: '03',
    title: 'Scan',
    body: 'Multiple analysis layers run in parallel. Findings appear in real-time. The rate limiter protects your API budget. Pause or cancel anytime.',
  },
  {
    num: '04',
    title: 'Ship',
    body: 'Your unified report is scored, explained, and actionable. Every finding has remediation. Deploy with confidence using generated cloud configurations.',
  },
];

export function HowItWorksSection() {
  return (
    <section className={s.howItWorks} id="how-it-works">
      <div className={s.hiwInner}>
        <div className={`${s.sectionHeader} animate-in`}>
          <span className={s.sectionLabel}>Workflow</span>
          <h2 className={s.sectionTitle}>From model to secure deployment.</h2>
          <p className={s.sectionSub}>
            Four steps. No setup. No terminal. No guesswork.
          </p>
        </div>
        <div className={`${s.hiwSteps} stagger`}>
          {STEPS.map((step, i) => (
            <div key={step.num} className={`${s.hiwStep} animate-in`}>
              <div className={s.hiwNum}>{step.num}</div>
              <div className={s.hiwConnector} aria-hidden="true">
                {i < STEPS.length - 1 && <div className={s.hiwLine} />}
              </div>
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
   CAPABILITIES (SECURITY ANALYSIS LAYERS)
   ════════════════════════════════════════════════ */
const LAYERS = [
  {
    name: 'Probe-Based Analysis',
    label: 'LAYER 1',
    desc: 'Systematic, reproducible probing with 100+ test patterns. OWASP-mapped. Deterministic results across runs.',
    finds: 'Detects: prompt injection, jailbreak bypasses, refusal failures',
  },
  {
    name: 'Adversarial Simulation',
    label: 'LAYER 2',
    desc: 'Multi-turn adversarial dialogue simulation. Tests conversation-dependent vulnerabilities that only surface across extended interactions.',
    finds: 'Detects: session escalation, context manipulation, persona drift',
  },
  {
    name: 'Behavioral Evaluation',
    label: 'LAYER 3',
    desc: 'Metric-driven evaluation framework. Quantitative thresholds for bias, hallucination, toxicity, and factual consistency.',
    finds: 'Detects: systematic bias, factual drift, toxicity patterns',
  },
];

export function CapabilitiesSection() {
  return (
    <section className={s.capabilities} id="capabilities">
      <div className={s.capInner}>
        <div className={`${s.sectionHeader} animate-in`}>
          <span className={s.sectionLabel}>Security Layers</span>
          <h2 className={s.sectionTitle}>Three analysis layers.<br />One unified report.</h2>
          <p className={s.sectionSub}>
            Each layer tests a different failure mode. Running only one gives you partial coverage.
          </p>
        </div>
        <div className={`${s.capGrid} stagger`}>
          {LAYERS.map((l) => (
            <div key={l.name} className={`${s.capCard} animate-in`}>
              <div className={s.capLabel}>{l.label}</div>
              <h3 className={s.capName}>{l.name}</h3>
              <p className={s.capDesc}>{l.desc}</p>
              <span className={s.capFinds}>{l.finds}</span>
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
        <div className={`${s.sectionHeader} animate-in`}>
          <span className={s.sectionLabel}>Deployment</span>
          <h2 className={s.sectionTitle}>From report to secure infrastructure.</h2>
          <p className={s.sectionSub}>
            The Deployment Advisor reads your risk profile and generates
            production-ready cloud configurations. For AWS: one-click execution.
          </p>
        </div>
        <div className={`${s.cloudTableWrap} animate-in`}>
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
                <td className={s.cloudHighlight}>$142/mo</td>
                <td>$167/mo</td>
                <td>$139/mo</td>
              </tr>
              <tr>
                <td>Native guardrails</td>
                <td><span className={s.cloudCheck}>✓ Bedrock</span></td>
                <td className={s.cloudMuted}>Manual</td>
                <td className={s.cloudMuted}>—</td>
              </tr>
              <tr>
                <td>One-click deploy</td>
                <td><span className={s.cloudCheck}>✓</span></td>
                <td className={s.cloudMuted}>—</td>
                <td className={s.cloudMuted}>—</td>
              </tr>
              <tr>
                <td>IAM auto-configuration</td>
                <td><span className={s.cloudCheck}>✓</span></td>
                <td className={s.cloudMuted}>—</td>
                <td className={s.cloudMuted}>—</td>
              </tr>
              <tr>
                <td>Monitoring alarms</td>
                <td><span className={s.cloudCheck}>✓ CloudWatch</span></td>
                <td className={s.cloudMuted}>Manual</td>
                <td className={s.cloudMuted}>Manual</td>
              </tr>
            </tbody>
          </table>
        </div>
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
        <div className={`${s.sectionHeader} animate-in`}>
          <span className={s.sectionLabel}>Product</span>
          <h2 className={s.sectionTitle}>See it in action.</h2>
          <p className={s.sectionSub}>
            Real-time scan progress with category tracking and live finding detection.
          </p>
        </div>

        <div className={`${s.ppWindow} animate-scale`}>
          <div className={s.ppTitlebar}>
            <div className={s.ppDots}>
              <span className={s.ppDot} />
              <span className={s.ppDot} />
              <span className={s.ppDot} />
            </div>
            <span className={s.ppWindowTitle}>Sentryɸ — Security Scan</span>
            <div />
          </div>

          {/* Sidebar + Main */}
          <div className={s.ppLayout}>
            <div className={s.ppSidebar}>
              <div className={s.ppSidebarItem}>
                <span className={s.ppSidebarDot} style={{ background: 'var(--sev-low)' }} />
                Input
              </div>
              <div className={s.ppSidebarItem}>
                <span className={s.ppSidebarDot} style={{ background: 'var(--sev-low)' }} />
                Config
              </div>
              <div className={`${s.ppSidebarItem} ${s.ppSidebarActive}`}>
                <span className={s.ppSidebarDot} style={{ background: 'var(--accent)' }} />
                Scanning
              </div>
              <div className={s.ppSidebarItem}>
                <span className={s.ppSidebarDot} style={{ background: 'var(--text-muted)' }} />
                Results
              </div>
            </div>

            <div className={s.ppMain}>
              <div className={s.ppEndpoint}>
                <span className={s.ppEndpointLabel}>Target</span>
                <span className={s.ppEndpointValue}>https://api.example.com/v1/chat</span>
              </div>

              <div className={s.ppProgress}>
                <div className={s.ppProgressHeader}>
                  <span>Executing security probes</span>
                  <span className={s.ppProgressPercent}>73%</span>
                </div>
                <div className={s.ppProgressBar}>
                  <div className={s.ppProgressFill} />
                </div>
                <div className={s.ppProgressMeta}>
                  <span>73 / 100 probes</span>
                  <span>Elapsed: 47s</span>
                </div>
              </div>

              <div className={s.ppCategories}>
                <div className={s.ppCatHeader}>Category Progress</div>
                <div className={s.ppCatRow}>
                  <span>Prompt Injection</span>
                  <span className={s.ppBadgeComplete}>Complete</span>
                </div>
                <div className={s.ppCatRow}>
                  <span>Jailbreak Resistance</span>
                  <span className={s.ppBadgeComplete}>Complete</span>
                </div>
                <div className={s.ppCatRow}>
                  <span>Data Leakage Detection</span>
                  <span className={s.ppBadgeActive}>Active</span>
                </div>
                <div className={s.ppCatRow}>
                  <span>Behavioral Analysis</span>
                  <span className={s.ppBadgeQueued}>Queued</span>
                </div>
              </div>

              <div className={s.ppFindings}>
                <div className={s.ppCatHeader}>Live Findings</div>
                <div className={s.ppFinding}>
                  <span className={s.ppFindingDot} style={{ background: 'var(--sev-critical)' }} />
                  <span className={s.ppFindingText}>System prompt extraction via multi-turn dialogue</span>
                  <span className={s.ppFindingSev}>Critical</span>
                </div>
                <div className={s.ppFinding}>
                  <span className={s.ppFindingDot} style={{ background: 'var(--sev-high)' }} />
                  <span className={s.ppFindingText}>Jailbreak via role-play instruction injection</span>
                  <span className={s.ppFindingSev}>High</span>
                </div>
                <div className={s.ppFinding}>
                  <span className={s.ppFindingDot} style={{ background: 'var(--sev-medium)' }} />
                  <span className={s.ppFindingText}>Inconsistent refusal boundary for medical queries</span>
                  <span className={s.ppFindingSev}>Medium</span>
                </div>
              </div>
            </div>
          </div>
        </div>
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
        <div className={`${s.sectionHeader} animate-in`}>
          <span className={s.sectionLabel}>Coverage</span>
          <h2 className={s.sectionTitle}>OWASP LLM Top 10 coverage.</h2>
          <p className={s.sectionSub}>
            We show what we cover — and what we do not.
          </p>
        </div>
        <div className={`${s.owaspGrid} stagger`}>
          {OWASP_ITEMS.map((item) => (
            <div key={item.id} className={`${s.owaspItem} animate-in`}>
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
      'Multi-layer security analysis orchestration',
      'Unified VulnerabilityFinding schema v1.0',
      'Explainable dual-axis confidence scoring',
      'AWS one-click deployment with guardrail configuration',
      'Report export: PDF, HTML, JSON',
    ],
  },
  {
    version: 'v1.5 — Developer Workflow',
    date: 'Target: Q1 2027',
    items: [
      'CLI interface for terminal-first developers',
      'GitHub Actions integration for CI/CD pipelines',
      'Azure + GCP one-click deployment',
      'Scan comparison and regression detection',
    ],
  },
  {
    version: 'v2.0 — Platform',
    date: 'Target: Q3 2027',
    items: [
      'Team collaboration and shared dashboards',
      'Native GitHub App for automated scanning',
      'Model version tracking and regression history',
      'Multi-modal scanning for vision-language models',
    ],
  },
];

export function FutureSection() {
  return (
    <section className={s.future} id="roadmap">
      <div className={s.futureInner}>
        <div className={`${s.sectionHeader} animate-in`}>
          <span className={s.sectionLabel}>Roadmap</span>
          <h2 className={s.sectionTitle}>What comes next.</h2>
          <p className={s.sectionSub}>
            Active development. Public roadmap. No guessing.
          </p>
        </div>
        <div className={`${s.futureTimeline} stagger`}>
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
      <div className={s.ctaGlow} aria-hidden="true" />
      <div className={s.ctaInner}>
        <h2 className={s.ctaTitle}>Stop guessing.<br />Start scanning.</h2>
        <p className={s.ctaSub}>
          Free. Open source. No account required. No server.<br />
          Download and run your first scan today.
        </p>
        <div className={s.ctaButtons}>
          <a href="/download" className={s.heroPrimary}>
            Get Started — Free
            <span className={s.heroArrow}>→</span>
          </a>
          <a href="#" className={s.heroSecondary}>
            View on GitHub
          </a>
        </div>
        <p className={s.ctaMeta}>
          v1.0.0 &nbsp;·&nbsp; Windows &nbsp;·&nbsp; Linux &nbsp;·&nbsp; MIT License
        </p>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   STATS / METRICS — Social Proof
   ════════════════════════════════════════════════ */
const STAT_ITEMS = [
  { value: '100+', label: 'Security Probes', sub: 'Across all analysis layers' },
  { value: '10', label: 'OWASP Categories', sub: 'LLM Top 10 coverage mapped' },
  { value: '3', label: 'Analysis Layers', sub: 'Probing · Adversarial · Behavioral' },
  { value: '<5min', label: 'Quick Scan', sub: 'From install to first report' },
  { value: '0', label: 'Data Collected', sub: 'Zero telemetry, zero tracking' },
  { value: '∞', label: 'Models Supported', sub: 'Any OpenAI-compatible API' },
];

export function StatsSection() {
  return (
    <section className={s.stats} id="stats">
      <div className={s.statsInner}>
        <div className={`${s.sectionHeader} animate-in`}>
          <span className={s.sectionLabel}>By The Numbers</span>
          <h2 className={s.sectionTitle}>Built for thoroughness.</h2>
        </div>
        <div className={`${s.statsGrid} stagger`}>
          {STAT_ITEMS.map((stat) => (
            <div key={stat.label} className={`${s.statCard} animate-in`}>
              <div className={s.statValue}>{stat.value}</div>
              <div className={s.statLabel}>{stat.label}</div>
              <div className={s.statSub}>{stat.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ════════════════════════════════════════════════
   FAQ — SEO-rich content for "People Also Ask"
   ════════════════════════════════════════════════ */
const FAQ_ITEMS = [
  {
    q: 'What is Sentryɸ?',
    a: 'Sentryɸ is a free, open-source pre-deployment security platform for large language models (LLMs). It runs multi-layer vulnerability scans — including prompt injection detection, jailbreak resistance testing, data leakage assessment, and behavioral evaluation — and produces a unified risk report with actionable remediation.',
  },
  {
    q: 'How is Sentryɸ different from running a single security scanner?',
    a: 'A single scanner tests one failure mode. Sentryɸ orchestrates three independent analysis layers — probe-based testing, adversarial dialogue simulation, and metric-driven behavioral evaluation — then cross-correlates findings to produce higher-confidence results with fewer false positives.',
  },
  {
    q: 'Does Sentryɸ work with any LLM?',
    a: 'Yes. Sentryɸ works with any model accessible via an OpenAI-compatible API endpoint (including OpenAI, Anthropic via proxy, Azure OpenAI, and self-hosted models). It also supports local GGUF models via built-in llama.cpp integration.',
  },
  {
    q: 'Is Sentryɸ free to use?',
    a: 'Sentryɸ is 100% free and open source under the MIT license. The only cost is API usage when scanning remote models — Sentryɸ estimates this cost before you approve any scan.',
  },
  {
    q: 'Does Sentryɸ collect any data or telemetry?',
    a: 'No. Sentryɸ collects zero telemetry, requires no account registration, and stores all scan data locally on your machine. API keys are stored in your operating system\'s native secure keychain.',
  },
  {
    q: 'What vulnerabilities does Sentryɸ detect?',
    a: 'Sentryɸ covers the OWASP LLM Top 10 including: prompt injection (LLM01), insecure output handling (LLM02), training data poisoning indicators (LLM03), denial of service vectors (LLM04), sensitive information disclosure (LLM06), excessive agency (LLM08), and overreliance patterns (LLM09).',
  },
  {
    q: 'What operating systems are supported?',
    a: 'Sentryɸ is available for Windows 10+ and Ubuntu 20.04+. The application is packaged as a standalone installer with all dependencies included — no Python, Node.js, or terminal setup required.',
  },
  {
    q: 'Can I use Sentryɸ in my CI/CD pipeline?',
    a: 'The v1.0 release includes a CLI interface (sentryphi scan) and JSON report export, which can be integrated into CI/CD pipelines. Native GitHub Actions integration is planned for v1.5.',
  },
];

export function FAQSection() {
  return (
    <section className={s.faq} id="faq">
      <div className={s.faqInner}>
        <div className={`${s.sectionHeader} animate-in`}>
          <span className={s.sectionLabel}>FAQ</span>
          <h2 className={s.sectionTitle}>Frequently asked questions.</h2>
          <p className={s.sectionSub}>
            Everything you need to know about Sentryɸ.
          </p>
        </div>
        <div className={`${s.faqList} stagger`}>
          {FAQ_ITEMS.map((item) => (
            <details key={item.q} className={`${s.faqItem} animate-in`}>
              <summary className={s.faqQuestion}>
                {item.q}
                <span className={s.faqChevron}>+</span>
              </summary>
              <p className={s.faqAnswer}>{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

