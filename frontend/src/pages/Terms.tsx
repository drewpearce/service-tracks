import { LegalPageShell } from "../components/LegalPageShell";

export default function Terms() {
  return (
    <LegalPageShell title="Terms of Service" lastUpdated="July 14, 2026">
      <p>
        These Terms of Service ("Terms") govern your access to and use of ServiceTracks
        ("ServiceTracks", "we", "us"), a service operated by an individual that synchronizes worship
        service plans from Planning Center Online to streaming music playlists on Spotify and YouTube
        Music. By creating an account or using the service, you agree to these Terms. If you do not
        agree, do not use ServiceTracks.
      </p>

      <h2>The service</h2>
      <p>
        ServiceTracks reads the service plans and songs in your connected Planning Center Online
        account and creates or updates corresponding playlists in your connected streaming accounts.
        The service depends on third-party platforms, and its availability and behavior may change as
        those platforms change.
      </p>

      <h2>Accounts and eligibility</h2>
      <ul>
        <li>You must provide accurate account information and keep your credentials secure.</li>
        <li>
          You are responsible for activity under your account and for ensuring you are authorized to
          connect the Planning Center and streaming accounts you link to ServiceTracks.
        </li>
        <li>You must be old enough to form a binding contract in your jurisdiction.</li>
      </ul>

      <h2>Acceptable use</h2>
      <p>You agree not to:</p>
      <ul>
        <li>Use the service in any way that violates applicable law or the terms of a connected third-party platform.</li>
        <li>Attempt to gain unauthorized access to the service, other accounts, or its underlying systems.</li>
        <li>Interfere with or disrupt the integrity or performance of the service.</li>
      </ul>

      <h2>Third-party services</h2>
      <p>
        ServiceTracks integrates with Planning Center Online, Spotify, and Google / YouTube Music.
        These are independent services governed by their own terms and privacy policies. We are not
        responsible for third-party services, and your use of them through ServiceTracks must comply
        with their terms. Access provided by those platforms may be changed or revoked at any time.
      </p>

      <h2>Intellectual property</h2>
      <p>
        ServiceTracks and its software, design, and content are owned by us and protected by
        applicable law. You retain all rights to your own data, including your Planning Center and
        streaming content. You grant us the limited permission necessary to process that data to
        provide the service.
      </p>

      <h2>Disclaimers</h2>
      <p>
        The service is provided "as is" and "as available," without warranties of any kind, whether
        express or implied. We do not warrant that the service will be uninterrupted, error-free, or
        that playlists will always synchronize accurately, particularly where third-party platforms
        experience outages, rate limits, or changes to their interfaces.
      </p>

      <h2>Limitation of liability</h2>
      <p>
        To the fullest extent permitted by law, ServiceTracks and its operator will not be liable for
        any indirect, incidental, special, consequential, or punitive damages, or for any loss of data
        or content, arising out of or relating to your use of the service.
      </p>

      <h2>Termination</h2>
      <p>
        You may stop using the service and delete your account at any time. We may suspend or terminate
        access if you violate these Terms or if necessary to protect the service or its users.
      </p>

      <h2>Changes to these Terms</h2>
      <p>
        We may update these Terms from time to time. When we do, we will revise the "Last updated" date
        at the top of this page. Your continued use of the service after changes take effect
        constitutes acceptance of the revised Terms.
      </p>

      <h2>Governing law</h2>
      <p>
        These Terms are governed by the laws of the State of Georgia, United States, without regard to
        its conflict-of-laws principles.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about these Terms can be sent to{" "}
        <a href="mailto:support@service-tracks.com">support@service-tracks.com</a>.
      </p>
    </LegalPageShell>
  );
}
