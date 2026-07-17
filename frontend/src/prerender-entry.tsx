import { renderToStaticMarkup } from 'react-dom/server'
import { StaticRouter } from 'react-router-dom/server'
import Home from './pages/Home'
import TermsOfService from './pages/TermsOfService'
import PrivacyPolicy from './pages/PrivacyPolicy'
import Contact from './pages/Contact'

const PAGES: Record<string, () => JSX.Element> = {
  '/': Home,
  '/terms': TermsOfService,
  '/privacy': PrivacyPolicy,
  '/contact': Contact,
}

export function render(path: string): string {
  const Page = PAGES[path]
  if (!Page) {
    throw new Error(`prerender-entry: no page mapped for path "${path}"`)
  }

  return renderToStaticMarkup(
    <StaticRouter location={path}>
      <Page />
    </StaticRouter>,
  )
}
