### Apna Slot

Slot booking

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench install-app apna_slot
```

### Development

The backend is a Frappe app (`apna_slot/`). The frontend is a Vue 3 single-page app (`frontend/`)
built on [frappe-ui](https://github.com/frappe/frappe-ui), served at `/apnaslot`.

```bash
npm install           # installs Playwright, and the frontend too
npm run dev           # Vite dev server
npm run build         # builds to apna_slot/public/frontend/ and writes apna_slot/www/apnaslot.html
npm run test:e2e      # Playwright end-to-end suite
```

The suite needs the E2E seed once per site:

```bash
bench --site apnaslot.localhost execute apna_slot.e2e_seed.setup_e2e_data
```

On a bench whose `default_site` is another site, serve this one on its own port and point the
suite at it:

```bash
bench --site apnaslot.localhost serve --port 8001
BASE_URL=http://apnaslot.localhost:8001 SITE_HOST=apnaslot.localhost:8001 \
  API_BASE=http://127.0.0.1:8001 FRAPPE_PASSWORD=frappeadmin npm run test:e2e
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/apna_slot
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade
### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `main` and every pull request.
- UI Tests: Installs this app on `apnaslot.test`, seeds it, and runs the Playwright suite on every push to `main` and every pull request.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

agpl-3.0
