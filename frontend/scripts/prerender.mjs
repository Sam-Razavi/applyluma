import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath, pathToFileURL } from 'url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const DIST = resolve(ROOT, 'dist')
const DIST_SSR = resolve(ROOT, 'dist-ssr')

// Routes whose raw HTML should contain real page content (not just meta tags).
const SSR_ROUTES = new Set(['/', '/terms', '/privacy', '/contact'])

const PAGES = [
  {
    path: '/',
    title: 'ApplyLuma — AI-powered job search & CV tailoring',
    description: 'ApplyLuma helps you land your next job faster. AI-powered CV tailoring, cover letter generation, Swedish job discovery, and application tracking — all in one place.',
    canonical: 'https://applyluma.com/',
    lastmod: '2026-07-16',
    changefreq: 'weekly',
    priority: '1.0',
  },
  {
    path: '/login',
    title: 'Log in — ApplyLuma',
    description: 'Sign in to your ApplyLuma account to tailor your CV, discover jobs, and track applications.',
    canonical: 'https://applyluma.com/login',
    lastmod: '2026-06-28',
    changefreq: 'monthly',
    priority: '0.5',
  },
  {
    path: '/register',
    title: 'Create account — ApplyLuma',
    description: 'Join ApplyLuma for free. AI-powered CV tailoring, Swedish job discovery, and application tracking — start in seconds.',
    canonical: 'https://applyluma.com/register',
    lastmod: '2026-06-28',
    changefreq: 'monthly',
    priority: '0.8',
  },
  {
    path: '/terms',
    title: 'Terms of Service — ApplyLuma',
    description: 'Read the ApplyLuma Terms of Service governing use of our AI-powered job search and CV tailoring platform.',
    canonical: 'https://applyluma.com/terms',
    lastmod: '2026-06-28',
    changefreq: 'monthly',
    priority: '0.3',
  },
  {
    path: '/privacy',
    title: 'Privacy Policy — ApplyLuma',
    description: 'Learn how ApplyLuma collects, uses, and protects your personal data. GDPR-compliant data handling.',
    canonical: 'https://applyluma.com/privacy',
    lastmod: '2026-06-28',
    changefreq: 'monthly',
    priority: '0.3',
  },
  {
    path: '/contact',
    title: 'Contact — ApplyLuma',
    description: 'Get in touch with the ApplyLuma team. Questions, feedback, or support — we are here to help.',
    canonical: 'https://applyluma.com/contact',
    lastmod: '2026-06-28',
    changefreq: 'monthly',
    priority: '0.5',
  },
]

const template = readFileSync(resolve(DIST, 'index.html'), 'utf-8')

const { render } = await import(pathToFileURL(resolve(DIST_SSR, 'prerender-entry.js')).href)

for (const page of PAGES) {
  let html = template
    .replace(
      /<title>[^<]*<\/title>/,
      `<title>${page.title}</title>`,
    )
    .replace(
      /<meta name="description" content="[^"]*" \/>/,
      `<meta name="description" content="${page.description}" />`,
    )
    .replace(
      /<link rel="canonical" href="[^"]*" \/>/,
      `<link rel="canonical" href="${page.canonical}" />`,
    )
    .replace(
      /<meta property="og:url" content="[^"]*" \/>/,
      `<meta property="og:url" content="${page.canonical}" />`,
    )
    .replace(
      /<meta property="og:title" content="[^"]*" \/>/,
      `<meta property="og:title" content="${page.title}" />`,
    )
    .replace(
      /<meta property="og:description" content="[^"]*" \/>/,
      `<meta property="og:description" content="${page.description}" />`,
    )
    .replace(
      /<meta name="twitter:title" content="[^"]*" \/>/,
      `<meta name="twitter:title" content="${page.title}" />`,
    )
    .replace(
      /<meta name="twitter:description" content="[^"]*" \/>/,
      `<meta name="twitter:description" content="${page.description}" />`,
    )

  if (SSR_ROUTES.has(page.path)) {
    try {
      const markup = render(page.path)
      if (!markup.includes('<h1')) {
        throw new Error(`rendered markup for ${page.path} does not contain an <h1>`)
      }
      html = html.replace('<div id="root"></div>', `<div id="root">${markup}</div>`)
    } catch (err) {
      console.error(`  failed to pre-render body HTML for ${page.path}`)
      console.error(err)
      process.exit(1)
    }
  }

  // page.path.slice(1) is '' for '/', which resolves to DIST itself — so
  // this also rewrites dist/index.html for the root route.
  const dir = resolve(DIST, page.path.slice(1))
  mkdirSync(dir, { recursive: true })
  writeFileSync(resolve(dir, 'index.html'), html)
  console.log(`  pre-rendered ${page.path}`)
}

rmSync(DIST_SSR, { recursive: true, force: true })

console.log(`\n  ${PAGES.length} pages pre-rendered.`)

const sitemap = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ...PAGES.map((page) => [
    '  <url>',
    `    <loc>${page.canonical}</loc>`,
    `    <lastmod>${page.lastmod}</lastmod>`,
    `    <changefreq>${page.changefreq}</changefreq>`,
    `    <priority>${page.priority}</priority>`,
    '  </url>',
  ].join('\n')),
  '</urlset>',
  '',
].join('\n')

const sitemapPath = resolve(DIST, 'sitemap.xml')
writeFileSync(sitemapPath, sitemap)

const writtenSitemap = readFileSync(sitemapPath, 'utf-8')
const missingUrls = PAGES.filter((page) => !writtenSitemap.includes(`<loc>${page.canonical}</loc>`))
if (missingUrls.length > 0) {
  console.error(`  sitemap.xml is missing URLs: ${missingUrls.map((p) => p.canonical).join(', ')}`)
  process.exit(1)
}

console.log(`  sitemap.xml written with ${PAGES.length} URLs.`)
