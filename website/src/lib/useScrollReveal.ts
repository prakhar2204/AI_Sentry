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
      const elements = document.querySelectorAll('.animate-in');
      elements.forEach((el) => {
        if (!observed.has(el)) {
          observed.add(el);
          observer.observe(el);
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
