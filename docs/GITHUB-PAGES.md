# GitHub Pages Facade

This folder now contains a zero-build static site for a public PoCP manifesto facade.

## Files

- `index.html`: the landing page entry
- `manifesto.html`: the public manifesto page
- `whitepaper.html`: the protocol whitepaper page
- `quick-start.html`: the quick start page
- `404.html`: the fallback page for invalid routes
- `.nojekyll`: disables Jekyll processing on GitHub Pages
- `pocp-mark.svg`: the site icon
- `site.css`: the shared visual style

## Recommended publish target

For the repository that should resolve to:

`https://PoCP-Labs.github.io/pocp-manifesto/`

the simplest publish path is now GitHub Pages via GitHub Actions.

## Included automation

- `.github/workflows/pages.yml`: deploys the `docs/` folder to GitHub Pages on every push to `main`

## Recommended setup

1. Push this repository to the target GitHub repository.
2. In repository settings, set GitHub Pages source to GitHub Actions.
3. Keep the site content in the `docs/` folder.
4. Edit the static HTML and CSS files directly when you need content updates.

## Alternative publish paths

If you do not want to use GitHub Actions, you can still publish from:

1. `main` branch `/docs` folder
2. `main` branch root folder after copying the static site files to the repository root

## Content coverage

The site includes:

- Manifesto framing
- Whitepaper summary
- Quick start guidance

## Maintenance model

- No build step
- No JavaScript dependency
- No server runtime
- Safe to edit as plain HTML and CSS