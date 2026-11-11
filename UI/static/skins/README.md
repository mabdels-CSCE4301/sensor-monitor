# Calculator skins

Skins are plain CSS themes loaded after `../style.css`. Each one scopes every
rule under an `html[data-skin="<name>"]` selector, so any number of skins can be
loaded together without leaking styles.

## Available skins

| Name      | File          | Description                                                                          |
| --------- | ------------- | ------------------------------------------------------------------------------------ |
| `default` | `../style.css` | Default dark, glassy theme (base stylesheet, no `data-skin` overrides).              |
| `modern`  | `modern.css`  | Futuristic 2030 theme: dark glass hull, holographic cyan/violet light, HUD brackets. |
| `classic` | `classic.css` | 1990s pocket-calculator look: grey plastic case, green LCD, beveled keys.            |

## Selecting a skin

The page exposes three ways to choose a skin, in order of precedence:

1. URL parameter: `/?skin=classic` (also `/index.html?skin=classic`).
2. Stored preference: `localStorage["calculator-skin"]`, written by the switcher.
3. Default: `default`.

The switcher is the `<select id="skin-select">` rendered above the calculator.
It updates `document.documentElement.dataset.skin`, persists the choice, and
rewrites the `skin` query parameter via `history.replaceState` so the current
view can be bookmarked or shared.

## Adding a skin

1. Create `static/skins/<name>.css`.
2. Scope all rules under `html[data-skin="<name>"]`. Override the custom
   properties declared in `:root` (`--bg`, `--screen`, `--text`, `--button`,
   etc.) plus any component rules the theme needs.
3. Add `<link rel="stylesheet" href="/static/skins/<name>.css" />` to
   `static/index.html` and an `<option value="<name>">` to the switcher.
4. Register the name in `SKINS` in `static/script.js` and in the pre-paint
   script in `index.html` so `?skin=` and stored preferences accept it.

## Requirements for new skins

- Keep the four-column key grid and the `#display` / `#expression` DOM contract.
- Provide visible hover, active, `:focus-visible`, and `:disabled` states.
- Keep text contrast at 4.5:1 or better for body-sized text; verify at 375 px.
- Respect `prefers-reduced-motion` for transitions and animations.
- Do not rely on the skin name for behavior: all skins must work with the same
  markup and the same `script.js`.
