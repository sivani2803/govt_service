# CivicPulse

**Turning civic signals into action.**

CivicPulse is an existing Streamlit civic service request portal. Citizens can submit and track reports; department staff can review the queue, record status changes, assign an officer, and attach resolution evidence. The local priority model and saved routing map are used by the report flow.

## Run locally

Use the verified Python 3.13 runtime, install the pinned dependencies, then start Streamlit:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On a fresh installation, the access screen opens on **Register**. Create a citizen account with your name, email, and a passphrase of at least 12 characters. After an account exists, the screen opens on **Sign in** for email and password. Accounts are stored in `government_service_request_app/civicpulse_accounts.sqlite3`; the database stores salted password hashes, not plain-text passwords.

The app expects the supplied model artifacts under `government_service_request_model/` and prepared data under `government_service_request_app/`. New requests, notices, and evidence are written to local CSV files and `government_service_request_app/uploads/`.

## Authentication and roles

The app provides local email/password registration and sign-in. Self-registration always creates a citizen account. Sign-in attempts are temporarily throttled after repeated failures. Local credential sessions expire after eight hours. Password reset by email is not configured.

Agency access is created by an operator on the same machine or shared filesystem that owns the local account database. The command prompts for the new password without displaying it:

```powershell
python -m src.auth_admin --email officer@city.gov --name "Agency Officer" --role officer
python -m src.auth_admin --email admin@city.gov --name "Agency Admin" --role administrator
```

For users authenticated by an external identity provider, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, register an OIDC client, and replace every example value. Set administrator and officer email allowlists in `[roles]`. Allowlisted agency privileges require the provider to return a verified email claim; other authenticated users receive citizen access. The secrets file is ignored by Git. For a hosted service, configure the matching callback URL and store these values in that host's secrets manager. When OIDC is configured, the screen also offers the provider sign-in option.

Citizens can report and track requests and view coarse public map hotspots. Officers and administrators can access agency operations, analytics, and system health. Local accounts use a shared SQLite account database and are intended for a single-host installation; use OIDC and a managed identity provider for public or multi-instance deployments. It does not yet provide department-scoped permissions.

## Civic imagery and maps

Category visuals use the provider order `google,unsplash,local` by default. Google Programmable Search is selected when both Google credentials are present; otherwise the existing Unsplash API is tried, then CivicPulse's original Pillow illustration. Set `CIVICPULSE_IMAGE_PROVIDERS` to reorder/disable providers, for example `unsplash,local` or `local`.

### Configure optional image providers

Copy `.env.example` as a reference, then set values in the process environment or in `.streamlit/secrets.toml` under `[media]`. The example contains placeholders only and is not automatically loaded as a `.env` file. In PowerShell, set credentials for the current terminal session like this:

```powershell
$env:GOOGLE_API_KEY = "your-google-api-key"
$env:GOOGLE_CSE_ID = "your-programmable-search-engine-id"
$env:UNSPLASH_ACCESS_KEY = "your-unsplash-access-key"
python -m streamlit run app.py
```

Google image search requires a Google API key and a Programmable Search Engine ID with image search enabled. The query uses SafeSearch, photo type, landscape filtering, and Google's `cc_publicdomain` usage-rights filter. Google and Unsplash results are downloaded server-side, checked for HTTPS, content type, size, and valid image data, resized/re-encoded, and rendered from cached bytes. Google search credits link to the result's source page and state that its public-domain filter was applied; verify the original source's terms before reusing an image. Unsplash visuals include photographer and source attribution. Local illustrations are labeled as generated artwork. Every category image is decorative and explicitly distinguished from evidence for an individual request. Resident-uploaded evidence stays in the existing request storage flow and is never sent to either image provider.

`CIVICPULSE_IMAGE_DAILY_BUDGET` sets a shared local cap (default `20`) across remote category searches. CivicPulse reserves at most one remote provider search per category per day; failed searches, invalid images, and quota errors use the local illustration for that category for the rest of the day. Unconfigured providers are skipped in the configured order. `CIVICPULSE_IMAGE_TIMEOUT_SECONDS` accepts a value from 3 to 5 seconds (default `4`). Successful images and provider failures are cached for 24 hours with `st.cache_data` and a small daily JSON cache under `government_service_request_app/` by default; the cache files are git-ignored. The API credential values are never included in UI errors or application logs.

Google's Custom Search JSON API pricing/availability is changing: Google's documentation says it is not available to new customers and is scheduled for discontinuation on **January 1, 2027**. Its published pricing for existing customers is 100 queries/day free, then $5 per 1,000 additional queries, up to 10,000/day. CivicPulse's default cap is lower; Google images require an API search query, while image downloading is a separate web request. See Google's [API overview, pricing, and availability](https://developers.google.com/custom-search/v1/overview) and [image-search parameters](https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list). If Google credentials cannot be obtained, use Unsplash or the offline illustration fallback.

The category cards and citizen dashboard use contextual image headers with a teal overlay, readable labels, and attribution. The report form and request summaries use the same image service. Floating quick actions are real keyboard-focusable links that pass a short `nav` query parameter; the app validates the action against the signed-in role's allowed-page set before routing. Citizens see Report, Track, and Help; officers/admins see Inbox, Map, and Notifications with the unread count. The Help page is a new informational screen. On small screens the layout stacks and the content reserves space above the fixed action control.

Maps use CARTO Dark Matter tiles when `[maps].carto_basemap_key` (or `CARTO_BASEMAP_API_KEY`) is configured. Without a key, local development uses OpenStreetMap tiles with a dark tile treatment so the map remains usable. External map tiles require browser network access. Citizen map coordinates are grouped into approximate 0.1° cells; request IDs, addresses, and exact coordinates are hidden from that view.

## Current product capabilities

- Citizen report form with service selection, location confirmation and map pin, multiple JPG/JPEG/PNG/WEBP photos, optional ward, citizen-stated urgency, model priority estimate, and deterministic department routing.
- Public request tracking by request ID, including the saved status timeline and before/during/after evidence when those files exist.
- Agency queue with priority/status/department/search filters, officer assignment, inspection notes and photos, status updates, resolution notes, and resolution photos.
- Operations analytics using the included historical summary files and locally stored requests, with date windows and ward/department views where the saved records contain those fields.
- Filterable map of requests that have valid stored coordinates, notification read state, and a presentation-oriented command center.
- Optional Streamlit OIDC login with administrator/officer allowlists.

## Data, model, and demo limits

- The included priority model was trained on historical Washington, DC 311 data. Its predictions have **not** been validated for Indian service requests and are decision support only.
- Department routing uses the supplied service-code mapping. It is deterministic; the routing metrics shown in the app describe the supplied evaluation and are not a guarantee for new local operations.
- Image handling currently provides **Demo Vision Analysis** metadata only. It records readable image format and dimensions, and does not detect civic defects or estimate visual severity/confidence.
- Request and notification storage is local CSV with atomic file replacement. This is suitable for a single-process demonstration, not concurrent multi-instance deployment or a durable production database.
- The app does not currently provide a separate HTTP API, server push / Socket.IO, configured SLA policy, cloud image storage, offline PWA, or automated demo scenario runner. System Health reports these limits rather than claiming those services are operational.
- External map tiles and optional Unsplash images require browser network access.

## Deployment notes

The application can be hosted as a Streamlit service, but the current local CSV persistence and bundled model/data paths do not meet the pasted production target. Before exposing it publicly, move request, notification, and audit data to a transactional database; move evidence to private object storage; configure HTTPS, OIDC, backups, retention, monitoring, and request-level authorization; and review the model's local validity. Do not treat the current demo-mode application as production-ready.

## Verification

```powershell
python -m compileall -q app.py src tests
python -m unittest discover -s tests -v
```

`streamlit run app.py` starts the interactive app. Browser-based journeys still need to be exercised against a running deployment and a configured identity provider before release.
