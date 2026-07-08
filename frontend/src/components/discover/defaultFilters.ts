import type { JobFilters } from '../../types/jobDiscovery'

export const DEFAULT_FILTERS: JobFilters = {
  search: '',
  location: '',
  salary_min: '',
  salary_max: '',
  keywords: '',
  source: '',
  remote_only: false,
  hide_applied: false,
  match_score_min: '',
  sort: 'score_desc',
}
