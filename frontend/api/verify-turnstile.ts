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

  try {
    // Use form-encoded body — official Cloudflare Turnstile siteverify format
    const params = new URLSearchParams()
    params.set('secret', turnstileSecret)
    params.set('response', token)

    const cfResp = await fetch('https://challenges.cloudflare.com/turnstile/v1/siteverify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params.toString(),
    })

    const cfText = await cfResp.text()
    let cfData: { success: boolean; 'error-codes'?: string[] }
    try {
      cfData = JSON.parse(cfText) as { success: boolean; 'error-codes'?: string[] }
    } catch {
      console.error('Cloudflare non-JSON response (status %d): %s', cfResp.status, cfText.slice(0, 300))
      return res.status(500).json({ error: 'Verification service unavailable' })
    }

    if (!cfData.success) {
      console.error('Turnstile rejected token, error-codes:', cfData['error-codes'])
      return res.status(400).json({ error: 'CAPTCHA verification failed' })
    }

    const payload = Buffer.from(JSON.stringify({ ts: Date.now() })).toString('base64url')
    const sig = createHmac('sha256', verifySecret).update(payload).digest('hex')

    return res.status(200).json({ verificationToken: `${payload}.${sig}` })
  } catch (err) {
    console.error('verify-turnstile unhandled error:', err)
    return res.status(500).json({ error: 'Verification failed' })
  }
}
