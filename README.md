# Animated Explainers: home page

Auto-updating, topic-organised index of the interactive explainers published on GitHub Pages.

**Live: https://brijs.github.io/explainers/**

## How it works

A GitHub Action (`.github/workflows/update-index.yml`) runs every 6 hours, on demand, and when this repo's scripts change:

1. Finds every public repo of `brijs` with the GitHub topic **`explainer`** and Pages enabled.
2. Reads each live page's `<head>` for its title, description and topic/tags.
3. Takes a screenshot thumbnail (only when the repo has changed), renders `site/index.html` grouped by topic, and deploys it to Pages.

### Adding a new explainer (nothing to edit here)

1. In the explainer's page `<head>`:
   ```html
   <meta name="description" content="One-line pitch">
   <meta name="explainer:topic" content="Science">          <!-- picks the section; any new name creates a new section -->
   <meta name="explainer:tags" content="DNA, genes, 3D">    <!-- comma separated -->
   <meta property="og:image" content="thumb.png">           <!-- optional; otherwise a screenshot is taken -->
   ```
2. Give the repo the topic `explainer` and set its homepage to the Pages URL:
   `gh repo edit OWNER/REPO --add-topic explainer --homepage https://brijs.github.io/REPO/`
3. Refresh the index now instead of waiting: `gh workflow run update-index.yml -R brijs/explainers`

The `animated-explainer-builder` skill does steps 1 to 3 for new explainers.

## Files

| Path | Purpose |
|---|---|
| `scripts/build_index.py` | `fetch` (discover + read metadata) and `render` (HTML). Python stdlib only |
| `scripts/thumbs.py` | Playwright screenshots into `thumbs/` |
| `templates/index.html` | Page template (styles + search/filter JS) |
| `topics.json` | Optional: order, emoji, colour, blurb per topic. Unlisted topics still appear |
| `fallbacks.json` | Used only for pages that have no `explainer:*` meta tags yet |
| `data/explainers.json`, `thumbs/` | Generated, committed by the Action |

Local preview: `GITHUB_TOKEN=$(gh auth token) python3 scripts/build_index.py fetch && python3 scripts/build_index.py render && open site/index.html`
