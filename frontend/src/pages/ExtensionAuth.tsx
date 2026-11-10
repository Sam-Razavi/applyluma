import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AxiosError } from 'axios'
import { ClipboardDocumentCheckIcon, ClipboardDocumentIcon, PuzzlePieceIcon } from '@heroicons/react/24/outline'
import { authApi } from '../services/api'
import { useAuthStore } from '../stores'

/**
 * The extension opens this page in a new tab. A new tab has no access token in
 * memory, and a cookie-only POST cannot pass the CSRF check from this origin
 * (the csrf_token cookie belongs to the API's domain, so this page cannot read
 * it). So first trade the httpOnly refresh cookie for an access token, then
 * mint the extension's tokens with it.
 */
async function mintExtensionTokens() {
  if (!useAuthStore.getState().token) {
    const { access_token } = await authApi.refresh()
    useAuthStore.getState().setToken(access_token)
  }
  return authApi.extensionToken()
}

export default function ExtensionAuth() {
  const [tokens, setTokens] = useState<{ access_token: string; refresh_token: string } | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(false)
  const [signedOut, setSignedOut] = useState(false)

  const copyTokens = useCallback(
    (payloadTokens?: { access_token: string; refresh_token: string }) => {
      const t = payloadTokens ?? tokens
      if (!t) return
      const payload = JSON.stringify({ access_token: t.access_token, refresh_token: t.refresh_token })
      void navigator.clipboard.writeText(payload).then(
        () => {
          setCopied(true)
          setTimeout(() => setCopied(false), 3000)
        },
        () => {
          /* clipboard blocked without a gesture — the manual button still works */
        },
      )
    },
    [tokens],
  )

  useEffect(() => {
    document.title = 'Connect Extension | ApplyLuma'
    // The web app authenticates via httpOnly cookies, so we mint a dedicated
    // bearer token pair for the extension to store and send.
    mintExtensionTokens()
      .then((pair) => {
        setTokens(pair)
        copyTokens(pair)
      })
      .catch((err: unknown) => {
        if (err instanceof AxiosError && err.response?.status === 401) setSignedOut(true)
        else setError(true)
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4 ">
      <div className="w-full max-w-md rounded-2xl border border-line bg-surface p-8 shadow-sm ">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600">
            <PuzzlePieceIcon className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-fg ">Connect Extension</h1>
            <p className="text-xs text-fg-subtle ">ApplyLuma Browser Extension</p>
          </div>
        </div>

        {signedOut ? (
          <div className="mb-6 rounded-xl bg-chip-warn px-4 py-3 text-sm text-chip-warn-fg">
            <p className="font-medium">Sign in to ApplyLuma first.</p>
            <p className="mt-1 text-fg-muted">You will come straight back here afterwards.</p>
            <Link
              to="/login?next=/extension-auth"
              className="mt-3 inline-flex rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
            >
              Sign in
            </Link>
          </div>
        ) : error ? (
          <div className="mb-6 rounded-xl bg-chip-danger px-4 py-3 text-sm font-medium text-chip-danger-fg ">
            Could not generate a token. Make sure you are signed in, then reload this page.
          </div>
        ) : copied ? (
          <div className="mb-6 flex items-center gap-2 rounded-xl bg-chip-success px-4 py-3 text-sm font-medium text-chip-success-fg ">
            <ClipboardDocumentCheckIcon className="h-5 w-5 flex-shrink-0" />
            Token copied! Return to the extension popup and paste it.
          </div>
        ) : (
          <div className="mb-6 rounded-xl bg-chip-accent px-4 py-3 text-sm text-accent-text ">
            {tokens ? 'Click the button below to copy your token.' : 'Generating your token…'}
          </div>
        )}

        <ol className="mb-6 space-y-2 text-sm text-fg-muted ">
          <li className="flex gap-2">
            <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-brand-600 text-[10px] font-bold text-white">1</span>
            Copy your token using the button below.
          </li>
          <li className="flex gap-2">
            <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-brand-600 text-[10px] font-bold text-white">2</span>
            Click the ApplyLuma icon in your browser toolbar.
          </li>
          <li className="flex gap-2">
            <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-brand-600 text-[10px] font-bold text-white">3</span>
            Paste the token and click <strong>Connect</strong>.
          </li>
        </ol>

        <button
          type="button"
          onClick={() => copyTokens()}
          disabled={!tokens}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          <ClipboardDocumentIcon className="h-4 w-4" />
          Copy token
        </button>

        <p className="mt-4 text-center text-xs text-fg-subtle ">
          This token is for the extension only. Visit this page again if the extension disconnects.
        </p>
      </div>
    </div>
  )
}
