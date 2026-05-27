export default function PrivacyPolicy() {
  return (
    <div className="max-w-3xl mx-auto py-12 px-4">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
      <p className="text-sm text-gray-400 mb-10">Last updated: May 2026</p>

      <div className="prose prose-gray max-w-none space-y-8 text-gray-700">

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">1. Who We Are</h2>
          <p>
            ApplyLuma ("we", "us") operates the applyluma.com platform. We are the data
            controller for personal data processed through the Service. You can reach us at{' '}
            <a href="mailto:support@applyluma.com" className="text-indigo-600 hover:underline">
              support@applyluma.com
            </a>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">2. Data We Collect</h2>
          <ul className="list-disc list-inside space-y-2">
            <li><strong>Account data:</strong> email address, full name, hashed password</li>
            <li><strong>CV and job data:</strong> resumes you upload, job descriptions you add, cover letters you generate</li>
            <li><strong>Usage data:</strong> pages visited, features used, timestamps</li>
            <li><strong>Billing data:</strong> subscription status (payment details are handled by Stripe and never stored by us)</li>
            <li><strong>Communications:</strong> emails we send you (verification, alerts, support)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">3. How We Use Your Data</h2>
          <ul className="list-disc list-inside space-y-2">
            <li>To provide and improve the Service (legal basis: contract performance)</li>
            <li>To send transactional emails such as email verification and password reset (legal basis: contract performance)</li>
            <li>To send job alert emails, if you enable them (legal basis: consent)</li>
            <li>To process AI features — your CV and job descriptions are sent to OpenAI's API for analysis (legal basis: contract performance)</li>
            <li>To process payments through Stripe (legal basis: contract performance)</li>
            <li>To monitor platform health and prevent abuse (legal basis: legitimate interests)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">4. Third-Party Services</h2>
          <p>We share data with the following processors to operate the Service:</p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li><strong>OpenAI</strong> — CV tailoring, cover letter generation, job match scoring</li>
            <li><strong>Stripe</strong> — subscription billing and payment processing</li>
            <li><strong>SendGrid (Twilio)</strong> — transactional email delivery</li>
            <li><strong>Railway</strong> — backend hosting and database</li>
            <li><strong>Vercel</strong> — frontend hosting</li>
          </ul>
          <p className="mt-3">
            We do not sell your personal data to third parties.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">5. Data Retention</h2>
          <p>
            We retain your data for as long as your account is active. If you delete your
            account, your personal data is deleted within 30 days, except where we are
            required to retain it for legal or billing purposes.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">6. Your Rights (GDPR)</h2>
          <p>If you are in the EU/EEA, you have the right to:</p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li><strong>Access</strong> — request a copy of the data we hold about you</li>
            <li><strong>Correction</strong> — ask us to correct inaccurate data</li>
            <li><strong>Deletion</strong> — request deletion of your personal data</li>
            <li><strong>Portability</strong> — receive your data in a machine-readable format</li>
            <li><strong>Restriction</strong> — ask us to limit how we process your data</li>
            <li><strong>Objection</strong> — object to processing based on legitimate interests</li>
            <li><strong>Withdraw consent</strong> — at any time, for processing based on consent (e.g. job alert emails)</li>
          </ul>
          <p className="mt-3">
            To exercise any of these rights, email{' '}
            <a href="mailto:support@applyluma.com" className="text-indigo-600 hover:underline">
              support@applyluma.com
            </a>. We will respond within 30 days.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">7. Cookies</h2>
          <p>
            ApplyLuma uses only essential cookies and local storage (JWT tokens for
            authentication, theme preference). We do not use advertising or tracking cookies.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">8. Security</h2>
          <p>
            We use industry-standard security measures including HTTPS, hashed passwords,
            JWT authentication, and role-based access control. No method of transmission over
            the internet is 100% secure, and we cannot guarantee absolute security.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">9. Changes to This Policy</h2>
          <p>
            We may update this Privacy Policy from time to time. Material changes will be
            communicated by email or via an in-app notice.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-3">10. Contact</h2>
          <p>
            For privacy questions or to exercise your rights, contact us at{' '}
            <a href="mailto:support@applyluma.com" className="text-indigo-600 hover:underline">
              support@applyluma.com
            </a>.
          </p>
        </section>

      </div>
    </div>
  )
}
