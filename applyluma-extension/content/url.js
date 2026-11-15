// How a job's address is compared and stored. One file, loaded everywhere the
// extension compares addresses (page scripts, popup, background), so a job
// saved from one view of a site is recognised in every other.

(function () {
  'use strict';
  if (globalThis.ApplyLumaUrl) return;

  // Parameters that follow a visitor around and say nothing about the page.
  const TRACKING_PARAM = /^(utm_.*|fbclid|gclid|msclkid|trk|trackingId|refId|ref|src|source|from|mc_[a-z]+)$/i;

  // One key per job, however its link is written.
  function jobUrlKey(url) {
    let u;
    try {
      u = new URL(url);
    } catch {
      return url;
    }
    if (/(^|\.)indeed\.com$/.test(u.hostname)) {
      // /viewjob?jk=, /rc/clk?jk=, /pagead/clk?...&jk= and the search pane's
      // ?vjk= all name the job by its key and nothing else.
      const key = u.searchParams.get('jk') || u.searchParams.get('vjk');
      if (key) return `${u.origin}/viewjob?jk=${key}`;
    }
    if (/(^|\.)linkedin\.com$/.test(u.hostname)) {
      // /jobs/view/123, /jobs/view/title-at-company-123 and ?currentJobId=123.
      const inPath = u.pathname.match(/\/jobs\/view\/(?:[^/]*-)?(\d+)\/?$/);
      const id = inPath ? inPath[1] : u.searchParams.get('currentJobId');
      if (id) return `https://www.linkedin.com/jobs/view/${id}`;
    }
    // Elsewhere any parameter may be the one that names the job ("gh_jid",
    // "rmjob", "id"...), so all are kept except tracking, in a fixed order.
    const kept = [...u.searchParams.entries()]
      .filter(([name]) => !TRACKING_PARAM.test(name))
      .map(([name, value]) => `${name}=${value}`)
      .sort();
    return u.origin + u.pathname.replace(/\/$/, '') + (kept.length ? `?${kept.join('&')}` : '');
  }

  // The address to store for a page: as it is, minus tracking and the fragment.
  function cleanUrl(url) {
    try {
      const u = new URL(url);
      for (const name of [...u.searchParams.keys()]) {
        if (TRACKING_PARAM.test(name)) u.searchParams.delete(name);
      }
      u.hash = '';
      return u.toString();
    } catch {
      return url;
    }
  }

  globalThis.ApplyLumaUrl = { jobUrlKey, cleanUrl };
})();
