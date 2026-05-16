import type { JobFilters } from '../../types/jobDiscovery'

export const DEFAULT_FILTERS: JobFilters = {
  location: '',
  salary_min: '',
  salary_max: '',
  keywords: '',
  source: '',
  match_score_min: '',
  sort: 'score_desc',
}
