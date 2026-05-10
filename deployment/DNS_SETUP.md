# Namecheap DNS Configuration for applyluma.com

## Prerequisites
- Vercel deployment successful
- Namecheap account access

## Step 1: Add Domain to Vercel
1. In Vercel project -> Settings -> Domains
2. Enter `applyluma.com`
3. Click "Add"
4. Vercel shows DNS records to configure

## Step 2: Configure Namecheap DNS
1. Log in to namecheap.com
2. Go to Domain List -> `applyluma.com` -> Manage
3. Navigate to the "Advanced DNS" tab
4. Delete any existing A/CNAME records for `@` and `www`

## Step 3: Add Vercel DNS Records
Add these records. Verify exact values in the Vercel dashboard before saving.

**Type: A Record**
- Host: `@`
- Value: `76.76.21.21`
- TTL: Automatic

**Type: CNAME Record**
- Host: `www`
- Value: `cname.vercel-dns.com`
- TTL: Automatic

## Step 4: Wait for Propagation
- DNS changes take 5 minutes to 24 hours
- Usually complete in about 30 minutes
- Check status: https://dnschecker.org

## Step 5: Verify SSL Certificate
1. In Vercel -> Domains
2. Wait for "Valid Configuration"
3. Vercel auto-issues the SSL certificate
4. Test `https://applyluma.com` and confirm the browser shows a padlock

## Step 6: Configure www Redirect
In Vercel -> Settings -> Domains:

- Set `www.applyluma.com` to redirect to `applyluma.com`
- Or set `applyluma.com` to redirect to `www.applyluma.com` if preferred

## Troubleshooting
- If SSL fails: wait 1 hour, then contact Vercel support
- If domain does not resolve: check Namecheap DNS propagation
- If mixed content errors appear: ensure `VITE_API_URL` uses `https://`

