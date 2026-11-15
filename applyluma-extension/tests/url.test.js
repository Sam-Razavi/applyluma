// Run with: node --test tests/*.test.js
const test = require('node:test');
const assert = require('node:assert');

require('../content/url.js');
const { jobUrlKey, cleanUrl } = globalThis.ApplyLumaUrl;

test('two Indeed jobs are not the same job', () => {
  const a = jobUrlKey('https://se.indeed.com/viewjob?jk=aaa111');
  const b = jobUrlKey('https://se.indeed.com/viewjob?jk=bbb222');
  assert.notStrictEqual(a, b);
});

test('every way Indeed links to a job gives one key', () => {
  const key = 'https://se.indeed.com/viewjob?jk=aaa111';
  for (const url of [
    'https://se.indeed.com/viewjob?jk=aaa111&from=serp&vjs=3',
    'https://se.indeed.com/rc/clk?jk=aaa111&bb=xyz',
    'https://se.indeed.com/jobs?q=python&l=Stockholm&vjk=aaa111',
    'https://se.indeed.com/pagead/clk?mo=r&ad=-6NYlbfk&jk=aaa111',
  ]) assert.strictEqual(jobUrlKey(url), key, url);
});

test('every way LinkedIn links to a job gives one key', () => {
  const key = 'https://www.linkedin.com/jobs/view/4012345678';
  for (const url of [
    'https://www.linkedin.com/jobs/view/4012345678/',
    'https://www.linkedin.com/jobs/view/4012345678/?trackingId=abc&refId=def',
    'https://www.linkedin.com/jobs/view/backend-developer-at-acme-4012345678',
    'https://www.linkedin.com/jobs/search/?currentJobId=4012345678&keywords=python',
    'https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4012345678',
  ]) assert.strictEqual(jobUrlKey(url), key, url);
});

test('a path names the job on most sites; tracking is ignored', () => {
  assert.strictEqual(
    jobUrlKey('https://arbetsformedlingen.se/platsbanken/annonser/29876543?utm_source=x'),
    'https://arbetsformedlingen.se/platsbanken/annonser/29876543',
  );
  assert.strictEqual(
    jobUrlKey('https://careers.acme.com/jobs/123/'),
    jobUrlKey('https://careers.acme.com/jobs/123?ref=newsletter#apply'),
  );
});

test('a job named only by a query parameter keeps it', () => {
  const a = jobUrlKey('https://acme.com/careers?gh_jid=111&utm_campaign=x');
  const b = jobUrlKey('https://acme.com/careers?gh_jid=222');
  assert.strictEqual(a, 'https://acme.com/careers?gh_jid=111');
  assert.notStrictEqual(a, b);
});

test('an unfamiliar parameter can be what names the job', () => {
  const base = 'https://web103.reachmee.com/ext/I005/333/main?site=2&lang=SE&rmpage=job';
  assert.notStrictEqual(jobUrlKey(`${base}&rmjob=51119`), jobUrlKey(`${base}&rmjob=51120`));
  assert.strictEqual(
    jobUrlKey(`${base}&rmjob=51119&utm_source=jobtip`),
    jobUrlKey(`https://web103.reachmee.com/ext/I005/333/main?rmjob=51119&rmpage=job&lang=SE&site=2`),
  );
});

test('text that is not an address is returned unchanged', () => {
  assert.strictEqual(jobUrlKey('not a url'), 'not a url');
  assert.strictEqual(cleanUrl('not a url'), 'not a url');
});

test('the stored address drops tracking and the fragment, nothing else', () => {
  assert.strictEqual(
    cleanUrl('https://acme.com/careers?gh_jid=111&utm_source=li&fbclid=zzz&lang=sv#apply'),
    'https://acme.com/careers?gh_jid=111&lang=sv',
  );
});
