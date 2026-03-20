# JL Command Center

Private mobile-first business dashboard for JL Zoeckler.

## Live URL
https://jl-command-center.jl-zoeckler.workers.dev/

Protected by Cloudflare Access — login required (jl.zoeckler@gmail.com only).

## Hosting
- **Cloudflare Pages** — auto-deploys on every push to `master`
- **Cloudflare Access (Zero Trust)** — Google login gate, only authorized emails can access

## Updating content
All content is in `index.html`. The data is hardcoded near the top in the `<script>` section and in the card HTML.

To update:
1. Edit `index.html`
2. `git add index.html && git commit -m "Update: ..." && git push`
3. Cloudflare auto-deploys in ~30 seconds

## Access
Neon Cortex (the AI) updates this dashboard automatically as business status changes.
