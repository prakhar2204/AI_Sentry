'use client';

import { useEffect } from 'react';

/**
 * IntersectionObserver hook for scroll-triggered animations.
 * Adds 'visible' class to elements with 'animate-in' class
 * when they enter the viewport.
 * 
 * Uses requestAnimationFrame + MutationObserver to handle
 * elements that mount after initial render (Next.js hydration).
 */
export function useScrollReveal() {
  useEffect(() => {
    const observed = new WeakSet<Element>();

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -20px 0px' }
    );

    function observeAll() {
      const elements = document.querySelectorAll(
        '.animate-in, .animate-scale, .animate-left, .animate-right'
      );
      elements.forEach((el) => {
        if (!observed.has(el)) {
          observed.add(el);
          observer.observe(el);
        }
      });

      // Stagger parents: add 'visible' to children when parent is in view
      document.querySelectorAll('.stagger').forEach((parent) => {
        if (!observed.has(parent)) {
          observed.add(parent);
          const staggerObserver = new IntersectionObserver(
            (entries) => {
              entries.forEach((entry) => {
                if (entry.isIntersecting) {
                  entry.target.querySelectorAll(
                    '.animate-in, .animate-scale, .animate-left, .animate-right'
                  ).forEach((child) => child.classList.add('visible'));
                  staggerObserver.unobserve(entry.target);
                }
              });
            },
            { threshold: 0.05, rootMargin: '0px 0px -20px 0px' }
          );
          staggerObserver.observe(parent);
        }
      });
    }

    // Initial observation (deferred to ensure DOM is ready after hydration)
    requestAnimationFrame(() => {
      observeAll();
    });

    // Watch for dynamically added elements
    const mutationObserver = new MutationObserver(() => {
      observeAll();
    });

    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
    });

    return () => {
      observer.disconnect();
      mutationObserver.disconnect();
    };
  }, []);
}
