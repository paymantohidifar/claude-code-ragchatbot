# Frontend Code Quality Tooling

## What was added

### Prettier (auto-formatter)
- **File:** `frontend/.prettierrc` — config: 100-char print width, single quotes, 2-space indent, trailing commas (ES5), LF line endings
- **File:** `frontend/.prettierignore` — excludes `node_modules/`
- Applied to `index.html`, `script.js`, and `style.css`

### ESLint (linter)
- **File:** `frontend/.eslintrc.json` — extends `eslint:recommended`, browser + ES2021 env
- Rules enforced: `eqeqeq` (===), `curly` (braces on all if/else), `no-var`, `prefer-const`
- Fixed 4 missing-curly-brace errors in `script.js`

### package.json
- **File:** `frontend/package.json` — npm project with dev deps: `prettier@^3.3.3`, `eslint@^8.57.0`
- Scripts:
  - `npm run format` — auto-format all files
  - `npm run format:check` — CI-safe format check (no writes)
  - `npm run lint` — ESLint check
  - `npm run lint:fix` — ESLint with auto-fix
  - `npm run check` — runs `format:check` + `lint` (full quality gate)

### Dev scripts (shell)
- **File:** `scripts/check-frontend.sh` — runs Prettier check + ESLint, exits non-zero on any failure (CI-friendly)
- **File:** `scripts/format-frontend.sh` — runs Prettier write + ESLint fix (developer convenience)

## How to use

```bash
# From frontend/ directory
npm run check        # verify formatting + lint (CI gate)
npm run format       # auto-format everything

# From repo root
./scripts/check-frontend.sh    # same as npm run check, path-independent
./scripts/format-frontend.sh   # auto-format + fix
```

## Files changed
| File | Change |
|------|--------|
| `frontend/index.html` | Prettier-formatted |
| `frontend/script.js` | Prettier-formatted + ESLint curly-brace fixes |
| `frontend/style.css` | Prettier-formatted |
| `frontend/package.json` | New — npm tooling manifest |
| `frontend/package-lock.json` | New — lockfile |
| `frontend/.prettierrc` | New — Prettier config |
| `frontend/.prettierignore` | New — Prettier ignore |
| `frontend/.eslintrc.json` | New — ESLint config |
| `scripts/check-frontend.sh` | New — CI quality-check script |
| `scripts/format-frontend.sh` | New — developer format script |
