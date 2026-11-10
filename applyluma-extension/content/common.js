// Shared job extraction for every site script. Loaded before the site script
// (see manifest.json), in the same isolated world, so it shares this global.
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

  function firstText(selectors) {
    for (const sel of selectors || []) {
      const el = document.querySelector(sel);
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
  function jsonLdJob() {
    for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
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
   * }
   */
  function extract(site) {
    if (!site.isJobPage()) return null;
    const ld = jsonLdJob() || {};
    const fromTitle = (site.fromDocumentTitle && site.fromDocumentTitle()) || {};
    return {
      title: pick(firstText(site.title), ld.title, fromTitle.title),
      company: pick(firstText(site.company), ld.company, fromTitle.company),
      url: site.canonicalUrl ? site.canonicalUrl() : window.location.href,
      description: pick(firstText(site.description), ld.description),
      extractedAt: Date.now(),
    };
  }

  // Background snapshot, used by the keyboard shortcut and as a fallback.
  function storeSnapshot(site) {
    chrome.storage.local.set({ linkedinJob: extract(site) });
  }

  function answerExtractRequests(site) {
    chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
      if (msg && msg.type === 'EXTRACT_JOB') {
        const job = extract(site);
        if (job) chrome.storage.local.set({ linkedinJob: job });
        sendResponse({ job });
      }
      return false;
    });
  }

  globalThis.ApplyLuma = { clean, firstText, jsonLdJob, extract, storeSnapshot, answerExtractRequests };
})();
