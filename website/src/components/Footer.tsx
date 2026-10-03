import styles from './Footer.module.css';

const PRODUCT_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Download', href: '/download' },
  { label: 'Changelog', href: '#' },
  { label: 'Roadmap', href: '#' },
];

const DEV_LINKS = [
  { label: 'Documentation', href: '#' },
  { label: 'GitHub', href: '#' },
  { label: 'Schema Reference', href: '#' },
  { label: 'Blog', href: '#' },
];

const LEGAL_LINKS = [
  { label: 'Privacy Policy', href: '#' },
  { label: 'Terms of Service', href: '#' },
  { label: 'Cookie Policy', href: '#' },
  { label: 'Contact', href: '#' },
];

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerInner}>
        <div className={styles.footerGrid}>
          <div className={styles.footerBrand}>
            <div className={styles.footerBrandName}>AI Sentry</div>
            <p className={styles.footerBrandDesc}>
              LLM Vulnerability Scanner and Pre-Deployment Security Platform. 
              Free and open source.
            </p>
          </div>

          <div>
            <div className={styles.footerColTitle}>Product</div>
            <div className={styles.footerLinks}>
              {PRODUCT_LINKS.map((l) => (
                <a key={l.label} href={l.href} className={styles.footerLink}>{l.label}</a>
              ))}
            </div>
          </div>

          <div>
            <div className={styles.footerColTitle}>Developers</div>
            <div className={styles.footerLinks}>
              {DEV_LINKS.map((l) => (
                <a key={l.label} href={l.href} className={styles.footerLink}>{l.label}</a>
              ))}
            </div>
          </div>

          <div>
            <div className={styles.footerColTitle}>Legal</div>
            <div className={styles.footerLinks}>
              {LEGAL_LINKS.map((l) => (
                <a key={l.label} href={l.href} className={styles.footerLink}>{l.label}</a>
              ))}
            </div>
          </div>
        </div>

        <div className={styles.footerBottom}>
          <div className={styles.footerCopy}>© 2026 AI-SENTRY. MIT Licensed.</div>
          <div className={styles.footerEngines}>Built on Garak · PyRIT · DeepTeam</div>
        </div>
      </div>
    </footer>
  );
}
