import { useState } from 'react'
import type { FormEvent } from 'react'
import { EnvelopeIcon, PhoneIcon, TrashIcon, UserCircleIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { useApplicationsStore } from '../../stores/applications'
import type { ApplicationContact } from '../../types/application'

interface Props {
  applicationId: string
  contacts: ApplicationContact[]
}

export default function ContactsList({ applicationId, contacts }: Props) {
  const addContact = useApplicationsStore((state) => state.addContact)
  const deleteContact = useApplicationsStore((state) => state.deleteContact)
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!name.trim() && !email.trim() && !phone.trim()) {
      toast.error('Add at least a name, email, or phone')
      return
    }

    setSaving(true)
    try {
      await addContact(applicationId, {
        name: name.trim() || null,
        role: role.trim() || null,
        email: email.trim() || null,
        phone: phone.trim() || null,
      })
      setName('')
      setRole('')
      setEmail('')
      setPhone('')
      toast.success('Contact added')
    } catch {
      toast.error('Could not add contact')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(contactId: string) {
    try {
      await deleteContact(applicationId, contactId)
      toast.success('Contact removed')
    } catch {
      toast.error('Could not remove contact')
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        {contacts.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-200 p-4 text-sm text-gray-400">
            No contacts saved for this application.
          </div>
        ) : (
          contacts.map((contact) => (
            <div key={contact.id} className="rounded-xl border border-gray-200 p-3">
              <div className="flex items-start gap-3">
                <UserCircleIcon className="mt-0.5 h-5 w-5 flex-shrink-0 text-gray-400" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {contact.name || 'Unnamed contact'}
                  </p>
                  {contact.role && <p className="text-xs text-gray-500">{contact.role}</p>}
                  <div className="mt-2 space-y-1 text-xs text-gray-500">
                    {contact.email && (
                      <p className="flex items-center gap-1.5 truncate">
                        <EnvelopeIcon className="h-3.5 w-3.5" />
                        {contact.email}
                      </p>
                    )}
                    {contact.phone && (
                      <p className="flex items-center gap-1.5">
                        <PhoneIcon className="h-3.5 w-3.5" />
                        {contact.phone}
                      </p>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(contact.id)}
                  className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-gray-400 transition hover:bg-red-50 hover:text-red-600"
                  aria-label="Delete contact"
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <form onSubmit={handleAdd} className="rounded-xl border border-gray-200 bg-gray-50 p-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input"
            placeholder="Name"
          />
          <input
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="input"
            placeholder="Role"
          />
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input"
            placeholder="Email"
            type="email"
          />
          <input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="input"
            placeholder="Phone"
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="mt-3 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-brand-700 ring-1 ring-brand-200 transition hover:bg-brand-50 disabled:opacity-50"
        >
          {saving ? 'Adding...' : 'Add contact'}
        </button>
      </form>
    </div>
  )
}
