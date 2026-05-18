import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import {
  addApplicationContact,
  createApplication as createApplicationRequest,
  deleteApplication as deleteApplicationRequest,
  deleteApplicationContact,
  fetchApplications as fetchApplicationsRequest,
  fetchStats,
  updateApplication as updateApplicationRequest,
} from '../services/applicationsApi'
import type {
  Application,
  ApplicationContactCreate,
  ApplicationCreate,
  ApplicationStats,
  ApplicationStatus,
  ApplicationUpdate,
} from '../types/application'
import { APPLICATION_STATUSES } from '../types/application'

type ApplicationFilters = {
  status: ApplicationStatus | ''
  search: string
}

interface ApplicationsState {
  applications: Application[]
  stats: ApplicationStats
  selectedApplication: Application | null
  isLoading: boolean
  error: string | null
  filters: ApplicationFilters
  fetchApplications: () => Promise<void>
  createApplication: (data: ApplicationCreate) => Promise<Application>
  updateApplication: (id: string, data: ApplicationUpdate) => Promise<Application>
  deleteApplication: (id: string) => Promise<void>
  addContact: (applicationId: string, data: ApplicationContactCreate) => Promise<void>
  deleteContact: (applicationId: string, contactId: string) => Promise<void>
  setSelected: (application: Application | null) => void
  setFilters: (filters: Partial<ApplicationFilters>) => void
}

const emptyStats = APPLICATION_STATUSES.reduce(
  (stats, status) => ({ ...stats, [status]: 0 }),
  {} as ApplicationStats,
)

function countStats(applications: Application[]): ApplicationStats {
  return applications.reduce(
    (stats, application) => ({
      ...stats,
      [application.status]: stats[application.status] + 1,
    }),
    { ...emptyStats },
  )
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Application request failed'
}

export const useApplicationsStore = create<ApplicationsState>()(
  devtools(
    (set, get) => ({
      applications: [],
      stats: { ...emptyStats },
      selectedApplication: null,
      isLoading: false,
      error: null,
      filters: { status: '', search: '' },

      fetchApplications: async () => {
        set({ isLoading: true, error: null })
        try {
          const { status } = get().filters
          const [applications, stats] = await Promise.all([
            fetchApplicationsRequest(status || undefined),
            fetchStats(),
          ])
          set({ applications, stats, isLoading: false })
        } catch (error) {
          set({ error: getErrorMessage(error), isLoading: false })
        }
      },

      createApplication: async (data) => {
        const application = await createApplicationRequest(data)
        set((state) => ({
          applications: [application, ...state.applications],
          stats: countStats([application, ...state.applications]),
          selectedApplication: application,
        }))
        return application
      },

      updateApplication: async (id, data) => {
        const previous = get().applications
        const selected = get().selectedApplication
        const optimistic = previous.map((application) =>
          application.id === id ? { ...application, ...data } as Application : application,
        )

        set({
          applications: optimistic,
          stats: countStats(optimistic),
          selectedApplication:
            selected?.id === id ? ({ ...selected, ...data } as Application) : selected,
        })

        try {
          const updated = await updateApplicationRequest(id, data)
          set((state) => {
            const next = state.applications.map((application) =>
              application.id === id ? updated : application,
            )
            return {
              applications: next,
              stats: countStats(next),
              selectedApplication:
                state.selectedApplication?.id === id ? updated : state.selectedApplication,
            }
          })
          return updated
        } catch (error) {
          set({
            applications: previous,
            stats: countStats(previous),
            selectedApplication: selected,
            error: getErrorMessage(error),
          })
          throw error
        }
      },

      deleteApplication: async (id) => {
        await deleteApplicationRequest(id)
        set((state) => {
          const next = state.applications.filter((application) => application.id !== id)
          return {
            applications: next,
            stats: countStats(next),
            selectedApplication:
              state.selectedApplication?.id === id ? null : state.selectedApplication,
          }
        })
      },

      addContact: async (applicationId, data) => {
        const contact = await addApplicationContact(applicationId, data)
        set((state) => {
          const next = state.applications.map((application) =>
            application.id === applicationId
              ? { ...application, contacts: [contact, ...(application.contacts ?? [])] }
              : application,
          )
          const selected =
            state.selectedApplication?.id === applicationId
              ? {
                  ...state.selectedApplication,
                  contacts: [contact, ...(state.selectedApplication.contacts ?? [])],
                }
              : state.selectedApplication
          return { applications: next, selectedApplication: selected }
        })
      },

      deleteContact: async (applicationId, contactId) => {
        await deleteApplicationContact(applicationId, contactId)
        set((state) => {
          const removeContact = (application: Application) => ({
            ...application,
            contacts: (application.contacts ?? []).filter((contact) => contact.id !== contactId),
          })
          return {
            applications: state.applications.map((application) =>
              application.id === applicationId ? removeContact(application) : application,
            ),
            selectedApplication:
              state.selectedApplication?.id === applicationId
                ? removeContact(state.selectedApplication)
                : state.selectedApplication,
          }
        })
      },

      setSelected: (application) => set({ selectedApplication: application }),

      setFilters: (filters) => {
        set((state) => ({ filters: { ...state.filters, ...filters } }))
      },
    }),
    { name: 'ApplicationsStore' },
  ),
)
