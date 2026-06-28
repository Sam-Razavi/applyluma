import { readFileSync, writeFileSync, mkdirSync } from 'fs'
import { resolve, dirname } from 'path'

const DIST = resolve(dirname(new URL(import.meta.url).pathname), '..', 'dist')

const PAGES = [
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

  const dir = resolve(DIST, page.path.slice(1))
  mkdirSync(dir, { recursive: true })
  writeFileSync(resolve(dir, 'index.html'), html)
  console.log(`  pre-rendered ${page.path}`)
}

console.log(`\n  ${PAGES.length} pages pre-rendered.`)
