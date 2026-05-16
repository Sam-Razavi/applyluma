import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import { XMarkIcon } from '@heroicons/react/24/outline'
import type { FormEvent, ReactNode } from 'react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { useApplicationsStore } from '../../stores/applications'
import type { ApplicationCreate, ApplicationStatus } from '../../types/application'
import { APPLICATION_STATUSES } from '../../types/application'
import { STATUS_META } from './statusMeta'

interface Props {
  open: boolean
  onClose: () => void
  initialData?: Partial<ApplicationCreate> | null
}

const sourceOptions = ['adzuna', 'linkedin', 'indeed', 'referral', 'company_site', 'other']
const remoteOptions = ['remote', 'hybrid', 'onsite']

const initialForm: ApplicationCreate = {
  company_name: '',
  job_title: '',
  job_url: '',
  status: 'wishlist',
  applied_date: null,
  source: '',
  salary_min: null,
  salary_max: null,
  location: '',
  remote_type: '',
  priority: 1,
  notes: '',
}

function buildInitialForm(initialData?: Partial<ApplicationCreate> | null): ApplicationCreate {
  return {
    ...initialForm,
    ...initialData,
    company_name: initialData?.company_name ?? '',
    job_title: initialData?.job_title ?? '',
    job_url: initialData?.job_url ?? '',
    status: initialData?.status ?? 'wishlist',
    priority: initialData?.priority ?? 1,
  }
}

function toNumber(value: FormDataEntryValue | null): number | null {
  const raw = String(value ?? '').trim()
  if (!raw) return null
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : null
}

export default function AddApplicationModal({ open, onClose, initialData }: Props) {
  const createApplication = useApplicationsStore((state) => state.createApplication)
  const [form, setForm] = useState<ApplicationCreate>(() => buildInitialForm(initialData))
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      setForm(buildInitialForm(initialData))
    }
  }, [initialData, open])

  function close() {
    if (submitting) return
    setForm(initialForm)
    onClose()
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const companyName = String(formData.get('company_name') ?? '').trim()
    const jobTitle = String(formData.get('job_title') ?? '').trim()

    if (!companyName || !jobTitle) {
      toast.error('Company name and job title are required')
      return
    }

    const payload: ApplicationCreate = {
      company_name: companyName,
      job_title: jobTitle,
      job_url: String(formData.get('job_url') || '') || null,
      status: String(formData.get('status')) as ApplicationStatus,
      applied_date: String(formData.get('applied_date') || '') || null,
      source: String(formData.get('source') || '') || null,
      salary_min: toNumber(formData.get('salary_min')),
      salary_max: toNumber(formData.get('salary_max')),
      location: String(formData.get('location') || '') || null,
      remote_type: String(formData.get('remote_type') || '') || null,
      priority: Number(formData.get('priority') || 1),
      notes: String(formData.get('notes') || '') || null,
    }

    setSubmitting(true)
    try {
      await createApplication(payload)
      toast.success('Application added')
      setForm(initialForm)
      onClose()
    } catch {
      toast.error('Could not create application')
    } finally {
      setSubmitting(false)
    }
  }

  function setField<K extends keyof ApplicationCreate>(field: K, value: ApplicationCreate[K]) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  return (
    <Dialog open={open} onClose={close} className="relative z-50">
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center sm:p-4">
        <DialogPanel className="flex h-full w-full flex-col rounded-none bg-white shadow-xl sm:h-auto sm:max-h-[90vh] sm:w-[600px] sm:rounded-lg">
          <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
            <DialogTitle className="text-base font-semibold text-gray-900">
              Add Application
            </DialogTitle>
            <button
              type="button"
              onClick={close}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 overflow-y-auto p-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Company name" required>
                <input
                  name="company_name"
                  value={form.company_name ?? ''}
                  onChange={(e) => setField('company_name', e.target.value)}
                  className="input"
                  placeholder="Spotify"
                />
              </Field>
              <Field label="Job title" required>
                <input
                  name="job_title"
                  value={form.job_title ?? ''}
                  onChange={(e) => setField('job_title', e.target.value)}
                  className="input"
                  placeholder="Backend Engineer"
                />
              </Field>
            </div>

            <Field label="Job URL">
              <input
                name="job_url"
                value={form.job_url ?? ''}
                onChange={(e) => setField('job_url', e.target.value)}
                className="input"
                placeholder="https://..."
              />
            </Field>

            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Status">
                <select
                  name="status"
                  value={form.status}
                  onChange={(e) => setField('status', e.target.value as ApplicationStatus)}
                  className="input"
                >
                  {APPLICATION_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {STATUS_META[status].label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Applied date">
                <input
                  name="applied_date"
                  type="date"
                  value={form.applied_date ?? ''}
                  onChange={(e) => setField('applied_date', e.target.value || null)}
                  className="input"
                />
              </Field>
              <Field label="Priority">
                <select
                  name="priority"
                  value={form.priority}
                  onChange={(e) => setField('priority', Number(e.target.value))}
                  className="input"
                >
                  <option value={1}>Low</option>
                  <option value={2}>Medium</option>
                  <option value={3}>High</option>
                </select>
              </Field>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Source">
                <select
                  name="source"
                  value={form.source ?? ''}
                  onChange={(e) => setField('source', e.target.value || null)}
                  className="input"
                >
                  <option value="">Choose...</option>
                  {sourceOptions.map((source) => (
                    <option key={source} value={source}>
                      {source.replace('_', ' ')}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Location">
                <input
                  name="location"
                  value={form.location ?? ''}
                  onChange={(e) => setField('location', e.target.value)}
                  className="input"
                  placeholder="Stockholm"
                />
              </Field>
              <Field label="Remote type">
                <select
                  name="remote_type"
                  value={form.remote_type ?? ''}
                  onChange={(e) => setField('remote_type', e.target.value || null)}
                  className="input"
                >
                  <option value="">Choose...</option>
                  {remoteOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </Field>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Salary min">
                <input
                  name="salary_min"
                  type="number"
                  min={0}
                  value={form.salary_min ?? ''}
                  onChange={(e) => setField('salary_min', e.target.value ? Number(e.target.value) : null)}
                  className="input"
                />
              </Field>
              <Field label="Salary max">
                <input
                  name="salary_max"
                  type="number"
                  min={0}
                  value={form.salary_max ?? ''}
                  onChange={(e) => setField('salary_max', e.target.value ? Number(e.target.value) : null)}
                  className="input"
                />
              </Field>
            </div>

            <Field label="Notes">
              <textarea
                name="notes"
                value={form.notes ?? ''}
                onChange={(e) => setField('notes', e.target.value)}
                rows={4}
                className="input resize-none"
                placeholder="Recruiter notes, next steps, or context."
              />
            </Field>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={close}
                disabled={submitting}
                className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-200 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
              >
                {submitting ? 'Saving...' : 'Save application'}
              </button>
            </div>
          </form>
        </DialogPanel>
      </div>
    </Dialog>
  )
}

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500"> *</span>}
      </span>
      {children}
    </label>
  )
}
