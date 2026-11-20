// Shared job extraction for every site script. Loaded after url.js and before
// the site script (see manifest.json), in the same isolated world, so it
// shares these globals.
//
// Two things make extraction reliable:
// 1. The popup asks the tab to extract *when it opens* (EXTRACT_JOB message),
//    so it reads the page as it is now rather than a snapshot taken 0.8 s after
//    load, before the job details had rendered.
// 2. Missing fields fall back to the schema.org JobPosting data most job sites
//    embed for search engines, which survives their frequent class renames.

(function () {
  'use strict';
  if (globalThis.ApplyLuma) return;

  function clean(text) {
    return (text || '')
      .replace(/ /g, ' ')
      .replace(/[ \t]+\n/g, '\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  // innerText keeps the line breaks a reader sees; textContent runs it all together.
  function textOf(el) {
    return clean(el.innerText || el.textContent || '');
  }

  function firstText(selectors, root = document) {
    for (const sel of selectors || []) {
      const el = root.querySelector(sel);
      if (el) {
        const text = textOf(el);
        if (text) return text;
      }
    }
    return '';
  }

  function stripTags(html) {
    const withBreaks = String(html).replace(/<\s*(br|\/p|\/li|\/h\d|\/div)\s*\/?>/gi, '\n');
    const doc = new DOMParser().parseFromString(withBreaks, 'text/html');
    return doc.body ? doc.body.textContent : '';
  }

  // Some sites (LinkedIn) entity-escape the HTML inside JSON-LD, so one pass
  // turns "&lt;p&gt;" into a literal "<p>"; a second pass removes those.
  function htmlToText(html) {
    if (!html) return '';
    let text = stripTags(html);
    if (/<\/?[a-z][^>]*>/i.test(text)) text = stripTags(text);
    return clean(text);
  }

  function findJobPosting(node) {
    if (!node || typeof node !== 'object') return null;
    if (Array.isArray(node)) {
      for (const item of node) {
        const found = findJobPosting(item);
        if (found) return found;
      }
      return null;
    }
    const type = node['@type'];
    if (type === 'JobPosting' || (Array.isArray(type) && type.includes('JobPosting'))) return node;
    return findJobPosting(node['@graph']);
  }

  // schema.org JobPosting embedded as JSON-LD, if the page has one.
  function jsonLdJob(root = document) {
    for (const script of root.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const job = findJobPosting(JSON.parse(script.textContent));
        if (!job) continue;
        const org = job.hiringOrganization;
        return {
          title: clean(job.title),
          company: clean(typeof org === 'string' ? org : org && org.name),
          description: htmlToText(job.description),
        };
      } catch {
        // Malformed JSON-LD on the page: ignore it and keep looking.
      }
    }
    return null;
  }

  function pick(...values) {
    for (const value of values) if (value) return value;
    return '';
  }

  /**
   * site = {
   *   isJobPage(): boolean,
   *   canonicalUrl?(): string,   // stable job URL (e.g. LinkedIn /jobs/view/<id>/)
   *   title, company, description: CSS selector lists,
   *   fromDocumentTitle?(): { title, company } | null,
   *   preferStructured?: boolean, // JSON-LD before the selectors (unknown layouts)
   *   maxDescription?: number,    // cut a description read from a whole page
   *   fetchJobPage?(): Promise<{ doc?: Document, extra?: {title, company, description} } | null>,
   *   fetched?: { title, company, description }, // selectors for the fetched page
   * }
   */
  function extract(site) {
    if (!site.isJobPage()) return null;
    const ld = jsonLdJob() || {};
    const fromTitle = (site.fromDocumentTitle && site.fromDocumentTitle()) || {};
    const field = (name) => {
      const fromPage = firstText(site[name]);
      return site.preferStructured
        ? pick(ld[name], fromPage, fromTitle[name])
        : pick(fromPage, ld[name], fromTitle[name]);
    };
    const description = field('description');
    return {
      // A heading can carry a second line (a location under the job title).
      title: field('title').split('\n')[0].trim(),
      company: field('company'),
      url: site.canonicalUrl ? site.canonicalUrl() : ApplyLumaUrl.cleanUrl(window.location.href),
      description: site.maxDescription ? description.slice(0, site.maxDescription) : description,
      extractedAt: Date.now(),
    };
  }

  // A job's own page fetched from the same site, read for the fields the open
  // page did not give. Signed-in LinkedIn and Indeed render the job with markup
  // that changes often; the job's standalone page is far more stable. Only the
  // job the user is looking at is fetched, and only when something is missing.
  async function fillFromJobPage(site, job) {
    if (!site.fetchJobPage || (job.title && job.company && job.description)) return job;
    let fetched;
    try {
      fetched = await site.fetchJobPage();
    } catch {
      return job; // offline, blocked or changed: keep what the open page gave
    }
    if (!fetched) return job;
    const { doc, extra = {} } = fetched;
    const ld = (doc && jsonLdJob(doc)) || {};
    const fromDoc = (name) => (doc ? firstText((site.fetched || {})[name] || site[name], doc) : '');
    const fill = (name) => job[name] || pick(fromDoc(name), ld[name], extra[name]);
    const description = fill('description');
    return {
      ...job,
      title: fill('title').split('\n')[0].trim(),
      company: fill('company'),
      description: site.maxDescription ? description.slice(0, site.maxDescription) : description,
    };
  }

  async function extractComplete(site) {
    const job = extract(site);
    return job ? fillFromJobPage(site, job) : null;
  }

  // Background snapshot, used by the keyboard shortcut and as a fallback.
  function storeSnapshot(site) {
    chrome.storage.local.set({ linkedinJob: extract(site) });
  }

  function answerExtractRequests(site) {
    chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
      if (msg && msg.type === 'EXTRACT_JOB') {
        extractComplete(site).then((job) => {
          if (job) chrome.storage.local.set({ linkedinJob: job });
          sendResponse({ job });
        });
        return true; // the answer comes after the job page is fetched
      }
      return false;
    });
  }

  globalThis.ApplyLuma = { clean, firstText, jsonLdJob, htmlToText, extract, extractComplete, storeSnapshot, answerExtractRequests };
})();
