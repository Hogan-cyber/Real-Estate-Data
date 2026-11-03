# Daily refresh

This edition uses GitHub Pages and GitHub Actions. The previous Sites deployment is not used.

The workflow is `.github/workflows/monthly.yml`. It runs daily at 10:00 UTC, equivalent to 18:00 Asia/Hong_Kong, and can be triggered manually from Actions.

Run `python updater/refresh.py --output data --app .`, validate with `python updater/validate.py data`, and build with `npm run build`. A clean checkout automatically seeds history from src/data.json. Keep the app ID and metric IDs stable, and retain updater/archives plus committed data history.

Exit 0 means no unresolved source errors; informational notes may remain. Exit 2 means a source was retained or a comparison still needs review. A fatal error must stop publication. Source errors are shown on the dashboard and surfaced by the workflow. No separate AI task, desktop heartbeat, browser login or computer left running is required.

Enable GitHub Pages using GitHub Actions in repository settings before the first deployment. Verify a successful deployment and the rendered public page before claiming the site is live. A workflow file alone does not prove that a scheduled run is active or has executed.

Commercial property is refreshed from nine additional official RVD CSVs in the same run. Office quality grades are independent of residential area classes. PDF/CSV comparisons cover six residential tables. Differences are classified as confirmed revisions only when a provisional PDF cell matches a recorded old-to-new CSV revision chain ending at a freshly collected current CSV value. All original differences remain visible; unknown or partially explained differences still require review. RVD originals, HKMA PDFs and Land Registry JSON responses are archived by content hash. Scheduled refresh uses deterministic Python only, with no GPT or LLM service.
