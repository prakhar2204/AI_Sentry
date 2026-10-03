import React from 'react';
import styles from './Button.module.css';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  href?: string;
  arrow?: boolean;
  downloadArrow?: boolean;
}

const variantMap: Record<ButtonVariant, string> = {
  primary: styles.btnPrimary,
  secondary: styles.btnSecondary,
  ghost: styles.btnGhost,
};

const sizeMap: Record<ButtonSize, string> = {
  sm: styles.btnSm,
  md: '',
  lg: styles.btnLg,
};

export function Button({
  variant = 'primary',
  size = 'md',
  href,
  arrow,
  downloadArrow,
  children,
  className = '',
  ...props
}: ButtonProps) {
  const classes = `${variantMap[variant]} ${sizeMap[size]} ${className}`.trim();

  if (href) {
    return (
      <a href={href} className={classes}>
        {downloadArrow && <span className={styles.btnDownloadArrow}>↓</span>}
        {children}
        {arrow && <span className={styles.btnArrow}>→</span>}
      </a>
    );
  }

  return (
    <button className={classes} {...props}>
      {downloadArrow && <span className={styles.btnDownloadArrow}>↓</span>}
      {children}
      {arrow && <span className={styles.btnArrow}>→</span>}
    </button>
  );
}
