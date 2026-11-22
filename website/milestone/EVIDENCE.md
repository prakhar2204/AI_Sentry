# Milestone II website evidence

Evidence date 22 November 2026 in India. The before crawl used HTTPS on the public site. The after crawl inspected the extracted HTML produced by the local release build. Search Console, Google Analytics and the production CDN require separate observations after publication.

| Report section | Available evidence | Still needed for submission |
|---|---|---|
| 1. Technical & On-Page SEO | Nine distinct titles and descriptions, one H1 per page, readable paths, nine canonical URLs in sitemap, social tags and image, Organization schema, page-specific breadcrumbs and Article markup. Both articles are reachable from the blog. | Google's Rich Results output and agreement on the native SEO implementation in place of Rank Math or Yoast. |
| 2. Performance & Security | Removed a render-blocking remote font import, added immutable caching for hashed assets, compressed the social card to WebP and kept the shield as a vector. Export includes Cloudflare response headers. | Matching public after tests, and current Cloudflare SSL mode. |
| 3. Keyword-Based Content | Measured pages and Milestone I keyword mapping below. | Verify the public URLs after upload. |
| 4. Outbound Links in the Blog Article | Both HTTPS targets returned 200. Both anchors are in body paragraphs, with no rel attribute. The source excerpt shows both together. | Verify the published article and retain the source screenshot. |
| 5. Google Search Console & GA4 Setup | GA4 ID `G-4Q49R83KDD` is configured in the website source. A consent-controlled Google tag and installer event passed browser checks using a mock ID. | Verified Search Console property, submitted sitemap status, indexing counts, real-time user and event evidence. |
| 6. Performance Reporting & Ranking Analysis | Milestone I supplies the keyword list for classifying real queries. | Exact GSC date range and totals, up to five available queries and the team's 80–120 word interpretation. |
| 7. SEO Audit & Issue Identification | Dated nine-page crawl, live mobile measurements and public release asset check. | See issue table below. |
| 8. Corrective Actions & Impact | Repeated the crawl on the export, checked 27 page/width combinations and verified both article citations. | Recheck production after upload, especially the www redirect and CDN caching. |
| 9. UpdraftPlus Backup | A tested source-and-static-export recovery ZIP is available. Its archive inventory, byte size and SHA-256 are recorded. | Facilitator acceptance or the required WordPress backup, public Drive link, signed-out access and retention. |
| 10. Reflection | The crawl supplies a concrete example of a site whose pages could open while every canonical named the wrong domain. | Team's own 100–150 words on impact, what they would change and what they learned. |
| 11. AI Use Disclosure & Declaration | Codex assisted with the audit, website edits, OWASP article draft, evidence collection, tests and release packaging. | Disclose other tools used, review the content and data, and sign the declaration yourselves. |

## Keyword evidence

Counts use rendered main content or the article, including headings, excluding navigation outside main, scripts, styles, SVG text and aria-hidden content. Internal links below are destinations in the page content. A same-page fragment is listed separately from links to other pages.

| Page | Milestone I primary keyword | Words | Internal destinations | External content links |
|---|---|---:|---|---|
| `/` | AI red teaming tool | 1,152 | Download, OWASP article and the How It Works fragment | Project GitHub repository |
| `/about/` | SentryPhi security team | 222 | OWASP article | Project GitHub repository |
| `/blog/owasp-llm-top-10-guide/` | AI red teaming risks based on OWASP GenAI Top 10 | 777 | LLM scanning guide, documentation | OWASP GenAI Top 10 and Seona Labs |

The article answers an informational query. It walks through each risk in the 2025 OWASP taxonomy, identifies evidence a reviewer can collect and explains which questions require an application or data review. The established article URL is preserved. The release includes a Cloudflare path redirect from the slug proposed in Milestone I.

| Body anchor | Destination | Words | rel |
|---|---|---:|---|
| OWASP GenAI Top 10 | https://genai.owasp.org/llm-top-10/ | 4 | Absent |
| Seona Labs | https://seonalabs.com | 2 | Absent |

## Audit and fixes

| # | Category and severity | Before, public site | After, local release |
|---|---|---|---|
| 1 | Technical · High | All nine page canonicals used sentryphi.dev. The sitemap and robots sitemap directive pointed to that domain. Download identified the homepage as its canonical. | Every page, Open Graph URL and sitemap entry uses its own sentryphi.me URL. The crawler can fetch rendering assets. |
| 2 | Links · High | All nine pages had unresolved internal links. Docs linked to twelve absent guide anchors. The public GitHub release contained only the Windows installer. | Zero unresolved internal destinations across nine pages. Docs link to real sections or files. Linux links to release availability. |
| 3 | On-page · Medium | Eight distinct page titles and descriptions for nine pages. Homepage schema and breadcrumbs appeared on other pages. Referenced social card and logo were missing. | Nine unique titles and descriptions. Eight inner pages have route-specific breadcrumbs. Social image and organization logo exist in the archive. |
| 4 | Content · Medium | Selected article lacked the two required contextual links and used an older OWASP numbering scheme without a clear edition. | Article names the 2025 edition, cites OWASP, includes the required SEO link and distinguishes model from application review. |
| 5 | Mobile · Medium | At 320 CSS pixels the Docs and Blog documents occupied 344 and 384 pixels. On a 390-pixel screen the homepage occupied 398. | All nine routes fit at viewport widths 320, 390 and 1280 in Chrome. |
| 6 | Performance · Medium | Homepage requested a remote font stylesheet. | System font fallbacks avoid the external request. A production rerun must establish the effect on mobile performance. |
| 7 | Host routing · Medium | The www hostname used in Milestone I returned 404 for /docs/. | Pending Cloudflare zone redirect. A Pages path redirect cannot correct an incoming hostname. |

The www address is a partial fix for the report discussion. The release now names the correct apex domain consistently, but the original www link still depends on a Cloudflare zone rule. Retest that public address before marking the issue resolved.

### Performance measurements

Public homepage, 22 November 2026. PageSpeed Insights Mobile ran at 17:08 IST with an emulated Moto G Power and Slow 4G. The separate GTmetrix PDF shows a desktop layout and identifies Chrome 154 in Seattle. It does not name a mobile device or connection profile.

| Tool and metric | Before | After publication |
|---|---:|---|
| PageSpeed Mobile performance | 92/100 | Pending |
| Largest Contentful Paint | 1.8 s | Pending |
| Total Blocking Time | 250 ms | Pending |
| Cumulative Layout Shift | 0 | Pending |
| GTmetrix Seattle Chrome grade | A | Pending |
| GTmetrix Seattle Chrome total page size | 356 KB (about 0.36 MB) | Pending |

PageSpeed Desktop scored 100/100 for performance. Mobile accessibility scored 96, best practices 100 and SEO 100. GTmetrix reported 99% performance, 95% structure, 21 requests and 161 KB of fonts. The exported CSS no longer requests the external Google Fonts stylesheet. Rerun each tool with its original settings to measure the effect. The subsequent mobile GTmetrix baseline used Galaxy S23/S24/S25, Seattle, 4G (9/5 Mbps, 125 ms). Performance was 90%, structure 94%, page size 323 KB, LCP 1.4 s, TBT 0 ms and CLS 0. Search Console showed 8 indexed URLs and 9 excluded under three reasons. Five excluded examples are slashless redirect URLs. Keep the original Seattle Chrome run labeled separately.

The earlier Lighthouse CLI runs are supplemental measurements. The local preview and public site used different serving conditions.

### Evidence files

- [Live crawl](evidence/before-live.json) and [release crawl](evidence/after-export.json)
- [Live mobile widths](evidence/mobile-before.json) and [release browser checks](evidence/browser-checks.json)
- [Article preview](evidence/article-release.png) and [article HTML source excerpt](evidence/article-source.png)
- [Live Lighthouse](evidence/lighthouse-before.json) and [local Lighthouse](evidence/lighthouse-after.json)
- [Archive checks and exact sizes](evidence/archive-check.json). The static backup is 577,684 bytes. The site has no WordPress database, plugins, themes or uploads.

Suggested figure order for the final report is schema validation, matching mobile before/after tests, article source, Search Console verification and indexing, GA4 Realtime and event, GSC queries, audit comparison and finally signed-out backup access. Number figures after inserting the actual screenshots.
