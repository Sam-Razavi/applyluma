import { useEffect, useState } from 'react'
import { ClipboardDocumentCheckIcon, ClipboardDocumentIcon, PuzzlePieceIcon } from '@heroicons/react/24/outline'
import { useAuthStore } from '../stores'

export default function ExtensionAuth() {
  const { token, refreshToken } = useAuthStore()
  const [copied, setCopied] = useState(false)

  function copyTokens() {
    if (!token) return
    const payload = JSON.stringify({ access_token: token, refresh_token: refreshToken ?? '' })
    void navigator.clipboard.writeText(payload).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 3000)
    })
  }

  useEffect(() => {
    document.title = 'Connect Extension | ApplyLuma'
    copyTokens()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-900">
      <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600">
            <PuzzlePieceIcon className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white">Connect Extension</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">ApplyLuma Browser Extension</p>
          </div>
        </div>

        {copied ? (
          <div className="mb-6 flex items-center gap-2 rounded-xl bg-green-50 px-4 py-3 text-sm font-medium text-green-700 dark:bg-green-900/20 dark:text-green-400">
            <ClipboardDocumentCheckIcon className="h-5 w-5 flex-shrink-0" />
            Token copied! Return to the extension popup and paste it.
          </div>
        ) : (
          <div className="mb-6 rounded-xl bg-indigo-50 px-4 py-3 text-sm text-indigo-700 dark:bg-indigo-900/20 dark:text-indigo-400">
            Copying your token…
          </div>
        )}

        <ol className="mb-6 space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <li className="flex gap-2">
            <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-brand-600 text-[10px] font-bold text-white">1</span>
            Your token has been copied to the clipboard.
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
          onClick={copyTokens}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
        >
          <ClipboardDocumentIcon className="h-4 w-4" />
          Copy token again
        </button>

        <p className="mt-4 text-center text-xs text-gray-400 dark:text-gray-500">
          This token rotates on re-login. Visit this page again if the extension disconnects.
        </p>
      </div>
    </div>
  )
}
