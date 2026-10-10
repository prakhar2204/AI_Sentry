import { Logo, BrandTitle } from './Logo';
import styles from './Footer.module.css';

const PRODUCT_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Download', href: '/download' },
  { label: 'Changelog', href: '#' },
  { label: 'Roadmap', href: '#roadmap' },
];

const DEV_LINKS = [
  { label: 'Documentation', href: '/docs' },
  { label: 'GitHub', href: '#' },
  { label: 'Blog', href: '/blog' },
  { label: 'About', href: '/about' },
];

const LEGAL_LINKS = [
  { label: 'Privacy Policy', href: '/privacy' },
  { label: 'Terms of Service', href: '/terms' },
  { label: 'Contact', href: '#' },
];

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerInner}>
        <div className={styles.footerGrid}>
          <div className={styles.footerBrand}>
            <div className={styles.footerBrandName}>
              <Logo size={24} />
              <BrandTitle size="sm" />
            </div>
            <p className={styles.footerBrandDesc}>
              Pre-deployment security platform for LLMs.
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
          <div className={styles.footerCopy}>© 2026 Sentryɸ. MIT Licensed.</div>
        </div>
      </div>
    </footer>
  );
}
