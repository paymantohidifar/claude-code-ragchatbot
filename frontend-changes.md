# Frontend Changes

## Code Quality Tooling

### What was added

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

### How to use

```bash
# From frontend/ directory
npm run check        # verify formatting + lint (CI gate)
npm run format       # auto-format everything

# From repo root
./scripts/check-frontend.sh    # same as npm run check, path-independent
./scripts/format-frontend.sh   # auto-format + fix
```

## Dark/Light Theme Toggle Button

### What was added

A fixed-position icon button in the top-right corner that toggles between the existing dark theme and a new light theme.

**`frontend/style.css`**
- Added two new custom-property blocks:
  - `:root` — four new `--theme-toggle-*` variables for the button's idle/hover colors.
  - `:root.light-theme` — overrides every color variable to produce a light palette (`#f8fafc` background, `#ffffff` surface, `#0f172a` text, etc.).
- Added a global `transition` rule (`background-color`, `border-color`, `color` all 0.3 s ease) so every themed element animates smoothly when the class toggles.
- Added `.theme-toggle` styles: 40 × 40 px circular button, `position: fixed; top: 1rem; right: 1rem; z-index: 1000`, hover scale + shadow, and a focus ring using `--focus-ring`.
- Icon visibility rules: `.icon-moon` visible by default (dark mode); `:root.light-theme .icon-sun` visible, `.icon-moon` hidden.

**`frontend/index.html`**
- Bumped stylesheet cache-bust version (`v12`).
- Added `<button id="themeToggle" class="theme-toggle">` just before the closing `</body>`, containing inline SVG sun and moon icons with `aria-hidden="true"` and a descriptive `aria-label` on the button itself.
- Bumped script cache-bust version (`v11`).

**`frontend/script.js`**
- `initTheme()` — reads `localStorage.getItem('theme')` on page load and applies `light-theme` to `<html>` if previously saved.
- `toggleTheme()` — toggles the `light-theme` class on `document.documentElement`, persists the choice to `localStorage`, and updates the button's `aria-label` dynamically.
- Wired `toggleTheme` to the `#themeToggle` click event inside `setupEventListeners()`.
- Called `initTheme()` at the top of the `DOMContentLoaded` handler (before `setupEventListeners`).

### Behavior

| Aspect | Detail |
|---|---|
| Default | Dark theme (existing palette, no class on `<html>`) |
| Toggle | Adds/removes `light-theme` class on `<html>` |
| Persistence | Choice saved in `localStorage` under key `"theme"` |
| Animation | All color properties transition over 0.3 s |
| Icon | Moon shown in dark mode; sun shown in light mode |
| Accessibility | Button has `aria-label`, SVGs have `aria-hidden`, fully keyboard-navigable with visible focus ring |

## Files changed
| File | Change |
|------|--------|
| `frontend/index.html` | Prettier-formatted + theme toggle button |
| `frontend/script.js` | Prettier-formatted + ESLint fixes + theme init/toggle |
| `frontend/style.css` | Prettier-formatted + light theme variables + toggle styles |
| `frontend/package.json` | New — npm tooling manifest |
| `frontend/.prettierrc` | New — Prettier config |
| `frontend/.prettierignore` | New — Prettier ignore |
| `frontend/.eslintrc.json` | New — ESLint config |
| `scripts/check-frontend.sh` | New — CI quality-check script |
| `scripts/format-frontend.sh` | New — developer format script |
