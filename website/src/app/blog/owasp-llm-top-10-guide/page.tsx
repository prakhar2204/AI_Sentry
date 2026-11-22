import { pageMetadata } from '@/lib/metadata';
import s from '@/styles/pages.module.css';

export const metadata = pageMetadata(
  '/blog/owasp-llm-top-10-guide/',
  "AI Red Teaming Risks Based on OWASP GenAI Top 10",
  "Use the OWASP GenAI risk categories to plan an LLM security review, choose the evidence to collect and explain the limits of a model scan.",
  true,
);

const title = 'AI red teaming risks based on OWASP GenAI Top 10';
const url = 'https://sentryphi.me/blog/owasp-llm-top-10-guide/';
const article = {
  '@context': 'https://schema.org', '@type': 'Article', headline: title,
  mainEntityOfPage: url, image: 'https://sentryphi.me/social-card.webp',
  datePublished: '2026-11-12', dateModified: '2026-11-22',
  author: { '@type': 'Organization', name: 'SentryPhi security team', url: 'https://sentryphi.me/about/' },
};

// The numbering below follows OWASP's 2025 edition.
const categories = [
  ['Prompt injection', 'A support assistant reads a customer attachment as well as staff instructions. Review which of those sources can influence a decision. Keep permissions in application code and use a harmless fixture to document whether the assistant stays within the intended task.'],
  ['Sensitive information disclosure', 'A summary may include details meant for another reader. Use fictional customer records for the review. Check the retrieval permissions and compare the answer with the records the signed-in user is entitled to see. Save only the minimum evidence needed for a reviewer.'],
  ['Supply chain', 'A model download, an adapter and a serving library each have a different origin. Record the version and source of every component you actually deploy. Ask whether another engineer could reconstruct that release and identify the owner responsible for approving a replacement.'],
  ['Data and model poisoning', 'Changes to a training dataset can alter behavior in ways that appear only on particular topics. Keep a record of dataset provenance and approvals. Compare the candidate release with a trusted baseline on the same review set and investigate differences before promotion.'],
  ['Improper output handling', 'A model response can become input to a web page, a database or another service. Inspect that handoff. For a field intended to display plain text, verify that the application renders punctuation and markup as text. Keep this evidence with the downstream component that enforces the rule.'],
  ['Excessive agency', 'An assistant that drafts a message and one that sends a message need different permissions. Review the tools granted to each role. Confirm that a person can review consequential actions and that the service checks authorization again when it carries them out.'],
  ['System prompt leakage', 'System instructions can reveal internal workflow details. Inventory sensitive values and move credentials into an appropriate secret store. An application that relies on a hidden instruction to enforce access needs a separate authorization check that works even if a user learns the instruction.'],
  ['Vector and embedding weaknesses', 'Two teams may share a search index while having different document permissions. Trace a retrieved passage back to its source, owner and access rules. Review what happens when the owner revokes access or replaces an outdated document. A correct answer can still have an unauthorized source.'],
  ['Misinformation', 'A fluent explanation can cite a policy that was retired last year. Give the reviewer dated reference material and ask them to check individual claims and citations. Record unsupported statements separately from answers where the assistant correctly says it lacks enough evidence.'],
  ['Unbounded consumption', 'A long-running request can occupy capacity intended for other users. Review configured timeouts, token limits and cancellation behavior. Confirm that an ordinary cancelled request releases resources, and identify who receives the alert when usage approaches the agreed budget.'],
];

export default function BlogPostOwaspLLM() {
  return <main className={s.blogPost}>
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(article) }} />
    <article className={s.blogArticle}>
      <header className={s.blogHeader}>
        <span className={s.blogCategory}>OWASP</span>
        <h1 className={s.blogTitle}>{title}</h1>
        <p className={s.blogMeta}>SentryPhi security team · Updated November 22, 2026 · 4 min read</p>
      </header>
      <div className={s.blogBody}>
        <p className={s.blogLead}>Before releasing a language model application, decide what evidence would change your release decision. The <a href="https://genai.owasp.org/llm-top-10/">OWASP GenAI Top 10</a> lists ten distinct risk categories in its 2025 edition. Some concern model behavior. Others require the reviewer to examine the surrounding software, data and permissions.</p>
        <p>Consider a search assistant that answers questions about your product. Someone working on search visibility might visit <a href="https://seonalabs.com">Seona Labs</a> to explore SEO. Someone reviewing the assistant has a different question about the same public content. Can a reader trace the answer back to the right source, and can the assistant distinguish that source from instructions about what it may do?</p>
        <h2>Choose the boundary of your review</h2>
        <p>Write down the model revision, the user role, the connected tools and the data a user can access. A review of an isolated model has a narrower scope than a review of a support assistant connected to a knowledge base. Make that distinction explicit before comparing two scan reports. For a walkthrough of selecting a scope, read our <a href="/blog/scan-llm-security-vulnerabilities/">LLM scanning guide</a>.</p>
        {categories.map(([name, detail], i) => <section key={name} className={s.owaspCategory}>
          <h2><span className={s.owaspId}>LLM{String(i + 1).padStart(2, '0')}</span> {name}</h2>
          <p>{detail}</p>
        </section>)}
        <h2>Turn the review into a release decision</h2>
        <p>For each category, record the observation, who owns the relevant control and which evidence is still missing. A scan can document how the model answered a particular question. A repository review can document where an access check is enforced. Neither observation, by itself, establishes that every path in the deployed application is covered.</p>
        <p>Keep the model revision and test conditions with the finding. After a fix, repeat the same check, record the result and note any remaining limitations. That gives the next reviewer a basis for deciding whether the change addressed the original risk. Our <a href="/docs/">project documentation</a> is a starting point for setting up a review.</p>
      </div>
    </article>
  </main>;
}
