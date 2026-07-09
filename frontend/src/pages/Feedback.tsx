import type { FormEvent } from 'react'
import { useState } from 'react'
import { ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { feedbackApi } from '../services/api'

const CATEGORIES = [
  { value: 'bug', label: 'Bug report' },
  { value: 'feature', label: 'Feature request' },
  { value: 'question', label: 'Question' },
  { value: 'other', label: 'Other' },
]

export default function Feedback() {
  const [category, setCategory] = useState('bug')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (message.trim().length < 10) {
      toast.error('Please describe your feedback in at least 10 characters')
      return
    }
    setSubmitting(true)
    try {
      await feedbackApi.submit({ category, subject: subject.trim(), message: message.trim() })
      toast.success('Thanks! Your feedback has been sent.')
      setSubject('')
      setMessage('')
    } catch {
      toast.error('Could not send feedback — please try again')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-fg">
          <ChatBubbleLeftRightIcon className="h-6 w-6" />
          Send feedback
        </h1>
        <p className="mt-1 text-sm text-fg-subtle">
          Found a bug, missing a feature, or have a question? It goes straight to the admins.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-2xl border border-line bg-surface p-6"
      >
        <div>
          <label htmlFor="feedback-category" className="mb-1 block text-sm font-medium text-fg-muted">
            Category
          </label>
          <select
            id="feedback-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="input"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="feedback-subject" className="mb-1 block text-sm font-medium text-fg-muted">
            Subject <span className="text-fg-subtle">(optional)</span>
          </label>
          <input
            id="feedback-subject"
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            maxLength={200}
            placeholder="Short summary"
            className="input"
          />
        </div>

        <div>
          <label htmlFor="feedback-message" className="mb-1 block text-sm font-medium text-fg-muted">
            Message
          </label>
          <textarea
            id="feedback-message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={6}
            maxLength={5000}
            placeholder="Tell us what happened, what you expected, or what you'd like to see…"
            className="input"
            required
          />
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? 'Sending…' : 'Send feedback'}
          </button>
        </div>
      </form>
    </div>
  )
}
