# GitHub Pages Deploy Checklist

Use this checklist when publishing the PoCP public facade to the repository that should serve:

`https://PoCP-Labs.github.io/pocp-manifesto/`

## 1. Prepare the repository

- Push the `docs/` folder contents to the target repository.
- Push `.github/workflows/pages.yml` to the target repository.
- Confirm that `docs/index.html`, `docs/manifesto.html`, `docs/whitepaper.html`, and `docs/quick-start.html` exist.
- Confirm that `docs/404.html`, `docs/.nojekyll`, `docs/site.css`, and `docs/pocp-mark.svg` exist.

## 2. Configure GitHub Pages

- Open the target repository on GitHub.
- Go to `Settings` -> `Pages`.
- Set `Source` to `GitHub Actions`.
- Save the setting.

## 3. Trigger deployment

- Push to `main`, or run the `Publish Pages` workflow manually from the `Actions` tab.
- Wait for the workflow to finish successfully.

## 4. Verify the site

- Open the site root URL.
- Confirm the home page loads.
- Confirm `manifesto.html`, `whitepaper.html`, and `quick-start.html` load.
- Confirm the 404 page renders for a missing route.
- Confirm styles and favicon load correctly.

## 5. Content update workflow

- Edit HTML or CSS files directly under `docs/`.
- Push the change to `main`.
- Let the `Publish Pages` workflow redeploy automatically.

## 6. Rollback path

- Revert the commit that changed `docs/` or `.github/workflows/pages.yml`.
- Push the revert to `main`.
- Wait for the next Pages deployment to finish.