import { LegalPageShell } from "../components/LegalPageShell";

export default function Privacy() {
  return (
    <LegalPageShell title="Privacy Policy" lastUpdated="July 14, 2026">
      <p>
        ServiceTracks ("ServiceTracks", "we", "us") is a service, operated by an individual, that
        synchronizes worship service plans from Planning Center Online to streaming music playlists
        on Spotify and YouTube Music. This Privacy Policy explains what information we collect, how we
        use it, and the choices you have. It applies to the ServiceTracks web application at
        service-tracks.com.
      </p>

      <h2>Information we collect</h2>
      <ul>
        <li>
          <strong>Account information.</strong> The email address and password you use to create an
          account, and the name of your church or organization. Passwords are stored only as a salted
          hash — we never store them in plain text.
        </li>
        <li>
          <strong>Planning Center data.</strong> When you connect your Planning Center Online
          account, we access your service plans and the songs on them (including titles, arrangements,
          and keys) so we can build corresponding playlists. We access this data using the permission
          you grant through Planning Center and only for the church you administer.
        </li>
        <li>
          <strong>Streaming account data.</strong> When you connect Spotify or YouTube Music, we
          receive and store OAuth access and refresh tokens and an account identifier for the
          connected account. These tokens are encrypted at rest. We use them only to create and update
          playlists on your behalf; we do not read your listening history or personal profile beyond
          what is required to manage those playlists.
        </li>
        <li>
          <strong>Usage and diagnostic data.</strong> Basic server logs and error diagnostics
          generated as the service runs, used to operate, secure, and debug the application.
        </li>
      </ul>

      <h2>How we use information</h2>
      <ul>
        <li>To operate the core service — reading your service plans and creating or updating your streaming playlists.</li>
        <li>To authenticate you and keep your account secure.</li>
        <li>To send transactional email such as address verification and password resets.</li>
        <li>To monitor, troubleshoot, and improve the reliability of the service.</li>
      </ul>
      <p>We do not sell your personal information, and we do not use it for advertising.</p>

      <h2>How we share information</h2>
      <p>
        We share information only with the service providers ("subprocessors") we rely on to run
        ServiceTracks:
      </p>
      <ul>
        <li>
          <strong>Planning Center Online</strong> — the source of your service plan and song data.
        </li>
        <li>
          <strong>Spotify</strong> and <strong>Google / YouTube Music</strong> — the streaming
          platforms where your playlists are created and updated. ServiceTracks uses YouTube API
          Services. By connecting YouTube Music you agree to the{" "}
          <a href="https://www.youtube.com/t/terms" target="_blank" rel="noreferrer">
            YouTube Terms of Service
          </a>
          . Your use of these platforms is also governed by their own privacy policies, including the{" "}
          <a href="https://policies.google.com/privacy" target="_blank" rel="noreferrer">
            Google Privacy Policy
          </a>{" "}
          and the{" "}
          <a href="https://www.spotify.com/legal/privacy-policy/" target="_blank" rel="noreferrer">
            Spotify Privacy Policy
          </a>
          .
        </li>
        <li>
          <strong>Resend</strong> — delivery of transactional email.
        </li>
        <li>
          <strong>Sentry</strong> — application error monitoring.
        </li>
        <li>
          <strong>Fly.io</strong> — application hosting and database infrastructure.
        </li>
      </ul>
      <p>
        We may also disclose information if required by law or to protect the rights, safety, and
        security of ServiceTracks and its users.
      </p>

      <h2>How we store and protect information</h2>
      <p>
        ServiceTracks is hosted on Fly.io in the United States. Streaming OAuth tokens are encrypted
        at rest, account passwords are hashed, and all traffic to the application is served over
        encrypted (HTTPS) connections. No method of storage or transmission is perfectly secure, but
        we take reasonable measures to protect your information.
      </p>

      <h2>Data retention</h2>
      <p>
        We keep your information for as long as your account is active. You may disconnect a streaming
        or Planning Center connection at any time from within the app, which removes the stored tokens
        for that connection. You can also revoke ServiceTracks' access to your Google account at any
        time from your{" "}
        <a href="https://myaccount.google.com/permissions" target="_blank" rel="noreferrer">
          Google account permissions page
        </a>
        . To delete your account and associated data, contact us at the address below.
      </p>

      <h2>Your rights</h2>
      <p>
        You may request access to, correction of, export of, or deletion of your personal
        information. To make a request, email <a href="mailto:privacy@service-tracks.com">privacy@service-tracks.com</a>.
      </p>

      <h2>Cookies</h2>
      <p>
        ServiceTracks uses two first-party cookies that are strictly necessary for the app to
        function: a session cookie that keeps you signed in, and a CSRF-protection cookie that guards
        against cross-site request forgery. We do not use third-party advertising or tracking cookies.
      </p>

      <h2>Children's privacy</h2>
      <p>
        ServiceTracks is intended for use by adult worship and music leaders administering a church
        account. It is not directed to children, and we do not knowingly collect personal information
        from children.
      </p>

      <h2>Changes to this policy</h2>
      <p>
        We may update this Privacy Policy from time to time. When we do, we will revise the "Last
        updated" date at the top of this page. Material changes will be communicated through the
        service where appropriate.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this Privacy Policy or your data can be sent to{" "}
        <a href="mailto:privacy@service-tracks.com">privacy@service-tracks.com</a>.
      </p>
    </LegalPageShell>
  );
}
