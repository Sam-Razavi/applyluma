import { useCallback, useEffect, useState } from 'react'
import { ClipboardDocumentCheckIcon, ClipboardDocumentIcon, PuzzlePieceIcon } from '@heroicons/react/24/outline'
import { authApi } from '../services/api'

export default function ExtensionAuth() {
  const [tokens, setTokens] = useState<{ access_token: string; refresh_token: string } | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(false)

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
    authApi
      .extensionToken()
      .then((pair) => {
        setTokens(pair)
        copyTokens(pair)
      })
      .catch(() => setError(true))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center bg-white/[0.03] px-4 ">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white/[0.04] p-8 shadow-sm ">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600">
            <PuzzlePieceIcon className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white/90 ">Connect Extension</h1>
            <p className="text-xs text-white/30 ">ApplyLuma Browser Extension</p>
          </div>
        </div>

        {error ? (
          <div className="mb-6 rounded-xl bg-[rgba(229,72,77,0.12)] px-4 py-3 text-sm font-medium text-red-300 ">
            Could not generate a token. Make sure you are signed in, then reload this page.
          </div>
        ) : copied ? (
          <div className="mb-6 flex items-center gap-2 rounded-xl bg-[rgba(52,195,143,0.14)] px-4 py-3 text-sm font-medium text-emerald-300 ">
            <ClipboardDocumentCheckIcon className="h-5 w-5 flex-shrink-0" />
            Token copied! Return to the extension popup and paste it.
          </div>
        ) : (
          <div className="mb-6 rounded-xl bg-[rgba(8,145,178,0.15)] px-4 py-3 text-sm text-cyan-300 ">
            {tokens ? 'Click the button below to copy your token.' : 'Generating your token…'}
          </div>
        )}

        <ol className="mb-6 space-y-2 text-sm text-white/55 ">
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

        <p className="mt-4 text-center text-xs text-white/30 ">
          This token is for the extension only. Visit this page again if the extension disconnects.
        </p>
      </div>
    </div>
  )
}
