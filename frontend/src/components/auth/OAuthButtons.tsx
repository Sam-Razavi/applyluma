import config from '../../config/environment'
import type { AuthProviders } from '../../services/authApi'

function GoogleIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  )
}

function LinkedInIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.55C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.72C24 .77 23.2 0 22.22 0z"
        fill="#0A66C2"
      />
    </svg>
  )
}

function GitHubIcon() {
  return (
    <svg className="h-5 w-5 fill-fg" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 .3a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.03c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.33-1.76-1.33-1.76-1.09-.74.08-.73.08-.73 1.2.09 1.84 1.24 1.84 1.24 1.07 1.83 2.8 1.3 3.49 1 .1-.78.42-1.31.76-1.61-2.66-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.13-.3-.54-1.52.11-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6.01 0c2.29-1.55 3.29-1.23 3.29-1.23.66 1.66.25 2.88.12 3.18.77.84 1.24 1.91 1.24 3.22 0 4.61-2.81 5.63-5.49 5.92.43.37.81 1.1.81 2.23v3.3c0 .32.22.7.83.58A12 12 0 0 0 12 .3z" />
    </svg>
  )
}

const PROVIDER_META: { key: keyof AuthProviders; slug: string; label: string; Icon: () => JSX.Element }[] = [
  { key: 'google', slug: 'google', label: 'Continue with Google', Icon: GoogleIcon },
  { key: 'linkedin', slug: 'linkedin', label: 'Continue with LinkedIn', Icon: LinkedInIcon },
  { key: 'github', slug: 'github', label: 'Continue with GitHub', Icon: GitHubIcon },
]

interface Props {
  providers: AuthProviders
}

export default function OAuthButtons({ providers }: Props) {
  const enabled = PROVIDER_META.filter((p) => providers[p.key])
  if (enabled.length === 0) return null

  return (
    <div className="space-y-3">
      {enabled.map(({ slug, label, Icon }) => (
        <button
          key={slug}
          type="button"
          onClick={() => {
            window.location.href = `${config.apiUrl}/api/v1/auth/${slug}/login`
          }}
          className="w-full flex items-center justify-center gap-3 py-2.5 px-4 border border-line-strong rounded-lg text-sm font-medium text-fg hover:bg-surface-strong transition-colors"
        >
          <Icon />
          {label}
        </button>
      ))}
    </div>
  )
}
