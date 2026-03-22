# Still Mode v1.0 — Release Notes

**Release Date:** March 21, 2026  
**Status:** ✅ Production Ready

---

## What's New

### Core Features
- **Focus Mode** — Lock in on one app, block all others
- **Global Shortcuts** — Press ESC anytime to exit
- **Ambient Focus** — Beautiful blackout overlay on inactive screens
- **Do Not Disturb** — Automatically silence notifications while focusing
- **Menubar Control** — Single-click activation from macOS menubar

### Monetization
- **Free Tier** — Focus on 1 app, unlimited time
- **Premium Tier ($2.99)** — Multi-app focus, timers, history (coming v1.1)

---

## Installation

### Option 1: Direct Download
1. Download `StillMode.app` from stillmode.app
2. Move to `/Applications/`
3. Open System Settings → Privacy & Security → Accessibility
4. Click `+` and add `StillMode.app`
5. Launch and enjoy!

### Option 2: Homebrew (Cask)
```bash
brew install stillmode
```

---

## Usage

1. **Click 🌙** in your menubar
2. **Select an app** from the list (e.g., Chrome)
3. **Click "Ready to be Still 🧘"** to lock in
4. **Try switching apps** — they'll bounce back
5. **Press ESC** anytime to exit and resume normal app switching

---

## Features in Detail

### App Blocking
When Still Mode is active:
- All apps except your chosen one are hidden
- Attempting to switch apps automatically brings focus back
- The blackout overlay dims the surroundings for psychological effect

### Exit Options
- **Keyboard:** Press ESC (works anywhere, menu not required)
- **Menu:** Click 🌙 → Click "❌ Exit Still Mode"

### Automatic Features
- Do Not Disturb automatically enables
- Focus tone plays on entry (Tink sound)
- Exit tone plays on exit (Pop sound)

---

## Known Limitations

- **Single Screen Primary** — Overlay currently works best on single-monitor setups (multi-monitor support in v1.1)
- **Pre-Hidden Apps** — Apps already minimized won't be shown afterward (restore manually)
- **Accessibility Required** — Must grant Accessibility permission for app blocking to work

---

## System Requirements

- **macOS 13+** (Ventura or later)
- **Apple Silicon or Intel** (arm64 or x86_64)
- **Accessibility Permissions**

---

## Troubleshooting

### "Still Mode can't access your apps" Error
**Solution:** Grant Accessibility permission
1. System Settings → Privacy & Security → Accessibility
2. Click `+`
3. Find and select StillMode.app
4. Restart the app

### Apps don't get blocked
**Solution:** Make sure they're regular apps (not system apps or utilities)

### Can't see the 🌙 in menubar
**Solution:** It may be hidden. Use Cmd+click on the menubar clock and drag the 🌙 into view, or restart the app

---

## Roadmap (v1.1 & Beyond)

- [ ] Multi-app focus (Premium)
- [ ] Focus timers (Premium)
- [ ] Session history & stats (Premium)
- [ ] Custom focus profiles
- [ ] Multi-monitor support
- [ ] iOS companion app
- [ ] In-app purchase support

---

## Support

Email: support@stillmode.app  
Twitter: @stillmodeapp  
Website: stillmode.app

---

## License

Still Mode is $2.99 one-time purchase (free tier available).

**Privacy:** No tracking, no analytics, no internet connection required.

---

**Thank you for using Still Mode. Focus well.** 🌙
