import type { VercelRequest, VercelResponse } from '@vercel/node'

// Not currently used — Cloudflare's siteverify endpoint returns 403 from
// all cloud provider IP ranges (Railway, Vercel). Kept for future use if
// Cloudflare resolves the restriction or if migrated to a dedicated egress IP.
export default function handler(_req: VercelRequest, res: VercelResponse) {
  return res.status(503).json({ error: 'Service not available' })
}
