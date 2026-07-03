import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import {
  ArrowTopRightOnSquareIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { useApplicationsStore } from '../../stores/applications'
import type { Application, ApplicationStatus, ApplicationUpdate } from '../../types/application'
import { APPLICATION_STATUSES } from '../../types/application'
import ConfirmDialog from '../ui/ConfirmDialog'
import ApplicationTimeline from './ApplicationTimeline'
import ContactsList from './ContactsList'
import { STATUS_META } from './statusMeta'

interface DrawerForm {
  company_name: string
  job_title: string
  job_url: string
  status: ApplicationStatus
  applied_date: string
  interview_date: string
  deadline: string
  source: string
  salary_min: string
  salary_max: string
  location: string
  remote_type: string
  priority: string
  notes: string
}

function toForm(application: Application): DrawerForm {
  return {
    company_name: application.company_name,
    job_title: application.job_title,
    job_url: application.job_url ?? '',
    status: application.status,
    applied_date: application.applied_date?.slice(0, 10) ?? '',
    interview_date: application.interview_date?.slice(0, 10) ?? '',
    deadline: application.deadline?.slice(0, 10) ?? '',
    source: application.source ?? '',
    salary_min: application.salary_min?.toString() ?? '',
    salary_max: application.salary_max?.toString() ?? '',
    location: application.location ?? '',
    remote_type: application.remote_type ?? '',
    priority: String(application.priority),
    notes: application.notes ?? '',
  }
}

function numberOrNull(value: string): number | null {
  const trimmed = value.trim()
  return trimmed ? Number(trimmed) : null
}

export default function ApplicationDrawer() {
  const application = useApplicationsStore((state) => state.selectedApplication)
  const setSelected = useApplicationsStore((state) => state.setSelected)
  const updateApplication = useApplicationsStore((state) => state.updateApplication)
  const deleteApplication = useApplicationsStore((state) => state.deleteApplication)
  const [form, setForm] = useState<DrawerForm | null>(application ? toForm(application) : null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)

  useEffect(() => {
    setForm(application ? toForm(application) : null)
  }, [application])

  if (!application || !form) return null

  function setField<K extends keyof DrawerForm>(field: K, value: DrawerForm[K]) {
    setForm((current) => (current ? { ...current, [field]: value } : current))
  }

  async function handleSave() {
    if (!application || !form) return
    const payload: ApplicationUpdate = {
      company_name: form.company_name.trim(),
      job_title: form.job_title.trim(),
      job_url: form.job_url.trim() || null,
      status: form.status,
      applied_date: form.applied_date || null,
      interview_date: form.interview_date || null,
      deadline: form.deadline || null,
      source: form.source || null,
      salary_min: numberOrNull(form.salary_min),
      salary_max: numberOrNull(form.salary_max),
      location: form.location.trim() || null,
      remote_type: form.remote_type || null,
      priority: Number(form.priority),
      notes: form.notes.trim() || null,
    }

    setSaving(true)
    try {
      await updateApplication(application.id, payload)
      toast.success('Application updated')
    } catch {
      toast.error('Could not update application')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!application) return
    setDeleting(true)
    try {
      await deleteApplication(application.id)
      toast.success('Application deleted')
      setDeleteConfirmOpen(false)
    } catch {
      toast.error('Could not delete application')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <>
      <Dialog open={!!application} onClose={() => setSelected(null)} className="relative z-50">
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-x-0 bottom-0 flex max-h-[92vh] sm:inset-x-auto sm:inset-y-0 sm:right-0 sm:max-h-none sm:max-w-full">
          <DialogPanel className="flex max-h-[92vh] w-full flex-col rounded-t-2xl bg-raised shadow-2xl sm:h-full sm:max-h-none sm:w-[480px] sm:rounded-none">
          <div className="flex items-start justify-between gap-4 border-b border-line px-6 py-5">
            <div className="min-w-0">
              <DialogTitle className="truncate text-lg font-semibold text-fg">
                {application.job_title}
              </DialogTitle>
              <p className="truncate text-sm text-fg-muted">{application.company_name}</p>
            </div>
            <button
              type="button"
              onClick={() => setSelected(null)}
              aria-label="Close"
              className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-lg text-fg-muted transition hover:bg-surface-strong hover:text-fg-muted"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 space-y-6 overflow-y-auto px-6 py-5">
            <section className="space-y-4">
              <SectionTitle>Details</SectionTitle>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Company">
                  <input
                    value={form.company_name}
                    onChange={(e) => setField('company_name', e.target.value)}
                    className="input"
                  />
                </Field>
                <Field label="Role">
                  <input
                    value={form.job_title}
                    onChange={(e) => setField('job_title', e.target.value)}
                    className="input"
                  />
                </Field>
              </div>

              <Field label="Job URL">
                <div className="flex gap-2">
                  <input
                    value={form.job_url}
                    onChange={(e) => setField('job_url', e.target.value)}
                    className="input"
                    placeholder="https://..."
                  />
                  {form.job_url && (
                    <a
                      href={form.job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-surface text-fg-muted transition hover:bg-surface-strong"
                    >
                      <ArrowTopRightOnSquareIcon className="h-4 w-4" />
                    </a>
                  )}
                </div>
              </Field>

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Status">
                  <select
                    value={form.status}
                    onChange={(e) => {
                      const next = e.target.value as ApplicationStatus
                      setField('status', next)
                      if (next === 'applied' && !form.applied_date) {
                        setField('applied_date', new Date().toISOString().slice(0, 10))
                      }
                      if (next === 'interview' && !form.interview_date) {
                        setField('interview_date', new Date().toISOString().slice(0, 10))
                      }
                    }}
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
                    type="date"
                    value={form.applied_date}
                    onChange={(e) => setField('applied_date', e.target.value)}
                    className="input"
                  />
                </Field>
                <Field label="Interview date">
                  <input
                    type="date"
                    value={form.interview_date}
                    onChange={(e) => setField('interview_date', e.target.value)}
                    className="input"
                  />
                </Field>
                <Field label="Application deadline">
                  <input
                    type="date"
                    value={form.deadline}
                    onChange={(e) => setField('deadline', e.target.value)}
                    className="input"
                  />
                </Field>
                <Field label="Source">
                  <input
                    value={form.source}
                    onChange={(e) => setField('source', e.target.value)}
                    className="input"
                    placeholder="linkedin"
                  />
                </Field>
                <Field label="Priority">
                  <select
                    value={form.priority}
                    onChange={(e) => setField('priority', e.target.value)}
                    className="input"
                  >
                    <option value="1">Low</option>
                    <option value="2">Medium</option>
                    <option value="3">High</option>
                  </select>
                </Field>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Location">
                  <input
                    value={form.location}
                    onChange={(e) => setField('location', e.target.value)}
                    className="input"
                  />
                </Field>
                <Field label="Remote type">
                  <select
                    value={form.remote_type}
                    onChange={(e) => setField('remote_type', e.target.value)}
                    className="input"
                  >
                    <option value="">Choose...</option>
                    <option value="remote">remote</option>
                    <option value="hybrid">hybrid</option>
                    <option value="onsite">onsite</option>
                  </select>
                </Field>
                <Field label="Salary min">
                  <input
                    type="number"
                    min={0}
                    value={form.salary_min}
                    onChange={(e) => setField('salary_min', e.target.value)}
                    className="input"
                  />
                </Field>
                <Field label="Salary max">
                  <input
                    type="number"
                    min={0}
                    value={form.salary_max}
                    onChange={(e) => setField('salary_max', e.target.value)}
                    className="input"
                  />
                </Field>
              </div>

              <Field label="Notes">
                <textarea
                  value={form.notes}
                  onChange={(e) => setField('notes', e.target.value)}
                  rows={4}
                  className="input resize-none"
                />
              </Field>
            </section>

            <section className="space-y-3">
              <SectionTitle>Timeline</SectionTitle>
              <ApplicationTimeline events={application.events ?? []} />
            </section>

            <section className="space-y-3">
              <SectionTitle>Contacts</SectionTitle>
              <ContactsList applicationId={application.id} contacts={application.contacts ?? []} />
            </section>
          </div>

          <div className="flex items-center justify-between gap-3 border-t border-line px-6 py-4">
            <button
              type="button"
              onClick={() => setDeleteConfirmOpen(true)}
              disabled={deleting}
              className="inline-flex items-center gap-2 rounded-lg bg-chip-danger px-3 py-3 text-sm font-semibold text-chip-danger-fg transition hover:bg-chip-danger disabled:opacity-50"
            >
              <TrashIcon className="h-4 w-4" />
              Delete
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="rounded-lg bg-brand-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save changes'}
            </button>
          </div>
          </DialogPanel>
        </div>
      </Dialog>
      <ConfirmDialog
        open={deleteConfirmOpen}
        title="Delete Application"
        message="Permanently delete 1 application? This cannot be undone."
        loading={deleting}
        onCancel={() => setDeleteConfirmOpen(false)}
        onConfirm={() => void handleDelete()}
      />
    </>
  )
}

function SectionTitle({ children }: { children: string }) {
  return <h3 className="text-sm font-semibold text-fg">{children}</h3>
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-fg-muted">{label}</span>
      {children}
    </label>
  )
}
