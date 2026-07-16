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
  },
  {
    path: '/login',
    title: 'Log in — ApplyLuma',
    description: 'Sign in to your ApplyLuma account to tailor your CV, discover jobs, and track applications.',
    canonical: 'https://applyluma.com/login',
  },
  {
    path: '/register',
    title: 'Create account — ApplyLuma',
    description: 'Join ApplyLuma for free. AI-powered CV tailoring, Swedish job discovery, and application tracking — start in seconds.',
    canonical: 'https://applyluma.com/register',
  },
  {
    path: '/terms',
    title: 'Terms of Service — ApplyLuma',
    description: 'Read the ApplyLuma Terms of Service governing use of our AI-powered job search and CV tailoring platform.',
    canonical: 'https://applyluma.com/terms',
  },
  {
    path: '/privacy',
    title: 'Privacy Policy — ApplyLuma',
    description: 'Learn how ApplyLuma collects, uses, and protects your personal data. GDPR-compliant data handling.',
    canonical: 'https://applyluma.com/privacy',
  },
  {
    path: '/contact',
    title: 'Contact — ApplyLuma',
    description: 'Get in touch with the ApplyLuma team. Questions, feedback, or support — we are here to help.',
    canonical: 'https://applyluma.com/contact',
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
