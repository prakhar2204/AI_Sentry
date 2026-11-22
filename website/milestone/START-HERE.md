# SentryPhi · Milestone II website release

Team SEO195 · Team Phi · Bennett University · 22 November 2026

## Before you replace the current site

1. The public PageSpeed mobile and desktop baselines and a Seattle Chrome GTmetrix run have been recorded. The mobile GTmetrix baseline is also complete: Galaxy S23/S24/S25, Seattle, 4G. Repeat the same settings after Cloudflare publishes the update. See [the baseline table](EVIDENCE.md#performance-measurements).
2. The website source contains the public Analytics measurement ID `G-4Q49R83KDD` in `website/public/analytics-id.txt`. Each page loads the Google tag when the visitor allows analytics. If Cloudflare defines `NEXT_PUBLIC_GA4_MEASUREMENT_ID`, its build-time value takes precedence.
3. In [Search Console](https://search.google.com/search-console/), use the property selector. Select the existing verified domain or **Add property → Domain** and enter `sentryphi.me`. Complete the Cloudflare authorization prompt if offered. For manual verification, copy Google's TXT record, open the domain in Cloudflare, choose **DNS → Records → Add record**, choose **TXT**, set **Name** to `@`, paste the value and save. Return to Google and select **Verify**. Retain the TXT record. [Google ownership guide](https://support.google.com/webmasters/answer/9008080)
4. Ask Dr. Saumitra Gangwar whether Team SEO195 may demonstrate Next.js metadata and a tested static-site backup for the two WordPress-specific requirements. The template allows a static move *after* the demonstration and WordPress backup. Milestone I records an existing static deployment. Written acceptance resolves whether the alternative can earn credit.

## Publish through the existing GitHub connection

Commit the changed and new website source files, then push to the GitHub branch configured for production in Cloudflare Pages. Check the deployment for that commit in Cloudflare. The release ZIP is an optional copy of the built site. The second ZIP contains source and built files for recovery and the course backup discussion.

Open the homepage, article and sitemap on the public domain. In Cloudflare, check the zone's **SSL/TLS → Overview** setting and save the displayed mode for the report. The submitted Milestone I address used `www`. A direct request to `https://www.sentryphi.me/docs/` returned HTTP 404 during this audit. In the domain's **Rules → Redirect Rules**, use the **Redirect from WWW to root** template, preserving path and query string. Ensure the www DNS record is proxied. Verify that the same URL now lands on `https://sentryphi.me/docs/`. Host-level redirects are managed at the zone level. [Cloudflare redirect capabilities](https://developers.cloudflare.com/pages/configuration/redirects/)

## Finish the live evidence

- In Search Console, choose **Sitemaps** and submit `https://sentryphi.me/sitemap.xml`. Capture the status. Open **Indexing → Pages** and record the indexed and unindexed counts with the date shown. Nine exported pages does not establish how many Google indexes.
- In a fresh browser session, open the public download page, choose **Allow analytics** at the bottom and click the Windows installer. In GA4, open **Reports → Realtime** and capture the active user and the `download_click` event once received. The event measures an installer link click. The browser tests used a mock endpoint and did not send data to Google.
- Test the published OWASP guide in [Google's Rich Results Test](https://search.google.com/test/rich-results). Capture the detected types, warnings and errors exactly as shown. The anonymous attempt on the old site prompted for login. The local release contains Article, Organization and BreadcrumbList JSON-LD.
- Repeat mobile PageSpeed Insights and GTmetrix using the baseline settings. Record performance score, LCP in seconds, TBT or INP in milliseconds, CLS, GTmetrix grade and total page size in MB. Save the report links. Open **Search Console → Performance → Search results**, choose exact dates and export total impressions, clicks, CTR, average position and up to five available queries. Use real low-volume or empty results when applicable.
- If your facilitator accepts the static backup, save the release-matching backup in Drive, set **Anyone with the link → Viewer**, and test its download in a signed-out private window. Keep the site and backup reachable through **31 December 2026**. A change to the published Analytics ID calls for an updated backup. If the facilitator requires WordPress, ask what demonstration is acceptable before changing the production architecture.
- Use the [rubric evidence notes](EVIDENCE.md) to fill the report. Supply the team's actual enrolment numbers, contributions, shares and reflection. The team leader exports the final Word or Google Docs report as `CSET489_M2_SEO195.pdf`. Keep the template's headings, 8–12 page limit excluding the appendix and numbered figures immediately after the tables they support.
