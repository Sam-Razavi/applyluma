import { useEffect } from 'react'

export default function TermsOfService() {
  useEffect(() => {
    document.title = 'Terms of Service — ApplyLuma'
  }, [])

  return (
    <div className="max-w-3xl mx-auto py-12 px-4">
      <h1 className="text-3xl font-bold text-fg mb-2">Terms of Service</h1>
      <p className="text-sm text-fg-subtle mb-10">Last updated: May 2026</p>

      <div className="prose prose-gray max-w-none space-y-8 text-fg-muted">

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">1. Acceptance of Terms</h2>
          <p>
            By creating an account or using ApplyLuma ("the Service"), you agree to be bound by
            these Terms of Service. If you do not agree, please do not use the Service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">2. Description of Service</h2>
          <p>
            ApplyLuma is an AI-powered job search and resume optimization platform. The Service
            includes job discovery, CV tailoring, cover letter generation, application tracking,
            and related features. The Service is provided in beta and features may change without
            notice.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">3. Account Registration</h2>
          <p>
            You must provide accurate information when registering. You are responsible for
            maintaining the security of your account and for all activity that occurs under it.
            You must be at least 16 years old to use the Service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">4. AI-Generated Content</h2>
          <p>
            The Service uses artificial intelligence to generate CV tailoring suggestions, cover
            letters, job match scores, and other content. This content is provided as-is for
            informational purposes. You are responsible for reviewing and editing any
            AI-generated content before using it. ApplyLuma makes no guarantees about the
            accuracy, suitability, or fitness of AI-generated content for any particular purpose.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">5. Subscriptions and Billing</h2>
          <p>
            Free accounts are subject to usage limits (e.g. CV tailoring and cover letter
            generation quotas). Premium subscriptions are billed through Stripe. Subscriptions
            renew automatically unless cancelled before the renewal date. Refunds are handled
            on a case-by-case basis — contact us at{' '}
            <a href="mailto:support@applyluma.com" className="text-accent-text hover:underline">
              support@applyluma.com
            </a>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">6. Acceptable Use</h2>
          <p>You agree not to:</p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>Use the Service for any unlawful purpose</li>
            <li>Upload malicious files or attempt to compromise the platform</li>
            <li>Resell or redistribute the Service without permission</li>
            <li>Scrape or harvest data from the Service by automated means</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">7. Intellectual Property</h2>
          <p>
            You retain ownership of all content you upload (CVs, job descriptions, etc.).
            By uploading content you grant ApplyLuma a limited licence to process it in order
            to provide the Service. ApplyLuma retains all rights in the platform, its design,
            and its proprietary technology.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">8. Limitation of Liability</h2>
          <p>
            The Service is provided "as is" without warranties of any kind. ApplyLuma shall not
            be liable for any indirect, incidental, or consequential damages arising from your
            use of the Service. Our total liability to you shall not exceed the amount you paid
            us in the 12 months preceding the claim.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">9. Termination</h2>
          <p>
            You may delete your account at any time from the Settings page. We reserve the right
            to suspend or terminate accounts that violate these Terms. Upon termination, your data
            will be deleted in accordance with our Privacy Policy.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">10. Changes to Terms</h2>
          <p>
            We may update these Terms from time to time. We will notify you of material changes
            by email or via an in-app notice. Continued use of the Service after changes
            constitutes acceptance of the updated Terms.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">11. Governing Law</h2>
          <p>
            These Terms are governed by the laws of Sweden. Any disputes shall be subject to
            the exclusive jurisdiction of the Swedish courts.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-fg mb-3">12. Contact</h2>
          <p>
            Questions about these Terms? Reach us at{' '}
            <a href="mailto:support@applyluma.com" className="text-accent-text hover:underline">
              support@applyluma.com
            </a>.
          </p>
        </section>

      </div>
    </div>
  )
}
