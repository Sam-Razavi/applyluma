import type { VercelRequest, VercelResponse } from '@vercel/node'
import { createHmac } from 'crypto'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { token } = (req.body ?? {}) as { token?: unknown }
  if (!token || typeof token !== 'string') {
    return res.status(400).json({ error: 'Missing token' })
  }

  const turnstileSecret = process.env.TURNSTILE_SECRET_KEY
  const verifySecret = process.env.CONTACT_VERIFY_SECRET
  if (!turnstileSecret || !verifySecret) {
    return res.status(500).json({ error: 'Server misconfigured' })
  }

  // Verify the Turnstile token with Cloudflare (Vercel can reach Cloudflare)
  const cfResp = await fetch('https://challenges.cloudflare.com/turnstile/v1/siteverify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ secret: turnstileSecret, response: token }),
  })
  const cfData = (await cfResp.json()) as { success: boolean; 'error-codes'?: string[] }

  if (!cfData.success) {
    return res.status(400).json({ error: 'CAPTCHA verification failed' })
  }

  // Issue a short-lived signed token that Railway can verify without calling Cloudflare
  const payload = Buffer.from(JSON.stringify({ ts: Date.now() })).toString('base64url')
  const sig = createHmac('sha256', verifySecret).update(payload).digest('hex')

  return res.status(200).json({ verificationToken: `${payload}.${sig}` })
}
