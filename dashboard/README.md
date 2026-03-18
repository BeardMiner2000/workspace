# JL Command Center — Dashboard

A private, mobile-first personal dashboard. Single static HTML file — no build step, no backend, no dependencies.

---

## 🚀 Hosting Options

### Option A: GitHub Pages (free, private with paid plan)

1. Create a new GitHub repo (e.g. `jl-command-center`) — set it **private** if you don't want it public
2. Push `index.html` to the repo:
   ```bash
   git init
   git add index.html
   git commit -m "Initial dashboard"
   git branch -M main
   git remote add origin git@github.com:YOUR_USERNAME/jl-command-center.git
   git push -u origin main
   ```
3. Go to **Settings → Pages** in your GitHub repo
4. Under *Source*, select `main` branch, root (`/`) folder → Save
5. Your dashboard will be live at:
   `https://YOUR_USERNAME.github.io/jl-command-center/`

> ⚠️ **Note:** GitHub Pages on free accounts serves public repos publicly even if the repo is private. Use a paid GitHub plan for private Pages, or use Netlify below.

---

### Option B: Netlify (free, truly private with password)

1. Go to [netlify.com](https://netlify.com) → Log in
2. Drag and drop the `dashboard/` folder onto the Netlify drop zone:
   `https://app.netlify.com/drop`
3. You'll get an instant URL like `https://amazing-name-12345.netlify.app`
4. To **password-protect it** (free on Netlify):
   - Site settings → Access control → Site protection → Set password
5. To use a custom domain, go to Domain settings

**To update:** Just drag and drop the folder again, or connect to a GitHub repo for auto-deploy on push.

---

### Option C: Open Locally (no hosting needed)

Just open `index.html` directly in any browser:
```bash
open /Users/jl/.openclaw/workspace/dashboard/index.html
```
Everything runs client-side. Works 100% offline.

---

## ✏️ How to Update the Content

The file is designed to be easy to edit. Here's what to change and where:

### Last Updated Date
Search for:
```html
<span class="last-updated">Updated Mar 18, 2026</span>
```
Change the date string.

### Milestone Checkboxes (Tuque Trading)
Find the `<ul class="milestones">` section. Each `<li>` has either class `milestone done` (checked) or just `milestone` (unchecked).

To check off a milestone, add `done` to the class:
```html
<!-- Before -->
<li class="milestone">

<!-- After (checked) -->
<li class="milestone done">
```

### This Week Items
Find the comment `<!-- ✏️  UPDATE THIS LIST WEEKLY -->` and edit the list items below it.

Each item follows this pattern:
```html
<li class="week-item">
  <span class="num">01</span>
  <span><strong>Project:</strong> Description of the task</span>
</li>
```

### Status Badges
Each card has a badge like:
```html
<div class="badge green">
  <span class="dot"></span>
  Active
</div>
```
Just change the text inside.

### Project Focus Text
Each card has a `<p class="focus-text">` block — update the content as priorities shift.

### Adding a New Card
Copy an existing `<div class="card [color]">` block and update the content. Available colors: `green`, `orange`, `yellow`, `blue`.

### Colors / Theming
All colors are defined in CSS variables at the top of the `<style>` block. Easy to retheme by changing values in the `:root {}` block.

---

## 📁 File Structure

```
dashboard/
  index.html   ← The entire app. This is all you need.
  README.md    ← This file
```

---

## 🔒 Privacy Notes

- No data is sent anywhere — everything is hardcoded in the HTML
- The Google Fonts CDN request can be removed for full offline use (fallback fonts are already defined)
- Safe to open on any device without a server
