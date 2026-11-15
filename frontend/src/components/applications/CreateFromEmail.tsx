import { useState, type FormEvent } from 'react'
import { PlusIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { createApplicationFromEmail, type ForwardedEmail } from '../../services/emailForwardingApi'

interface Props {
  email: ForwardedEmail
  onCreated: (application: { id: string; company_name: string; job_title: string }) => void
}

/**
 * For an email that belongs to no application yet: start tracking one from it.
 * Company and job title are guessed from the email and can be corrected; the
 * status and date are taken from the email itself.
 */
export default function CreateFromEmail({ email, onCreated }: Props) {
  const [open, setOpen] = useState(false)
  const [company, setCompany] = useState(email.guessed_company ?? '')
  const [title, setTitle] = useState(email.guessed_title ?? '')
  const [saving, setSaving] = useState(false)

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex min-h-[40px] items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700"
      >
        <PlusIcon className="h-4 w-4" />
        Create application from this email
      </button>
    )
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!company.trim() || !title.trim()) return
    setSaving(true)
    try {
      const application = await createApplicationFromEmail(email.id, {
        company_name: company.trim(),
        job_title: title.trim(),
      })
      toast.success(`Now tracking ${application.company_name}`)
      onCreated(application)
    } catch {
      toast.error('Could not create the application')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-line bg-raised p-3">
      <p className="text-sm text-fg-muted">
        Check the details. The date and status come from the email.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm font-medium text-fg">
          Company
          <input
            className="input mt-1 w-full"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            maxLength={255}
            required
            autoFocus
          />
        </label>
        <label className="block text-sm font-medium text-fg">
          Job title
          <input
            className="input mt-1 w-full"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={255}
            required
          />
        </label>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          disabled={saving || !company.trim() || !title.trim()}
          className="min-h-[40px] rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {saving ? 'Creating…' : 'Create application'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="min-h-[40px] rounded-lg px-3 py-1.5 text-sm font-medium text-fg-muted hover:bg-surface-strong"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
