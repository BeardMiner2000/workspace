# 🌙 Still Mode

A minimal macOS menubar focus tool. One click, one app, everything else disappears.

---

## Concept

Still Mode lives in your menubar as a moon icon. You click it, pick the one app you want to focus on, and everything else vanishes. Click again to exit. That's the whole thing.

**When active:**
- Your chosen app comes to the front
- All other regular apps are hidden
- Do Not Disturb is enabled
- The icon changes from 🌙 to 🌕

**When you exit:**
- All hidden apps are restored
- DND is disabled
- You're back to normal

---

## Build

### Requirements
- macOS 13+ (Ventura or later)
- Xcode 15+ (or Xcode 14 with Swift 5.9)

### With Xcode (recommended)

```bash
cd stillmode
open StillMode.xcodeproj
# Then: Product → Build (⌘B), Product → Run (⌘R)
```

### With xcodebuild (CLI)

```bash
cd stillmode
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  xcodebuild -project StillMode.xcodeproj \
             -scheme StillMode \
             -configuration Release \
             CODE_SIGN_IDENTITY="" \
             CODE_SIGNING_REQUIRED=NO \
             build
```

The built `.app` lands in:
```
~/Library/Developer/Xcode/DerivedData/StillMode-*/Build/Products/Release/StillMode.app
```

### With XcodeGen (optional)

If you want to regenerate the `.xcodeproj` from `project.yml`:

```bash
brew install xcodegen
xcodegen generate
```

---

## Permissions

Still Mode needs **Accessibility** access to hide and show other apps.

1. Go to **System Settings → Privacy & Security → Accessibility**
2. Click the `+` button and add `StillMode.app`
3. Enable the toggle

Without this, the app can bring your focus app to front but can't hide others.

---

## Run at Login

### Option A: Login Items (macOS 13+)

```bash
# Add to login items via System Settings
open "x-apple.systempreferences:com.apple.LoginItems-Settings.extension"
```

Or System Settings → General → Login Items → add StillMode.app

### Option B: LaunchAgent (persistent, recommended)

Create `~/Library/LaunchAgents/com.jl.stillmode.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jl.stillmode</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/StillMode.app/Contents/MacOS/StillMode</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.jl.stillmode.plist
```

---

## How It Works

### FocusManager.swift
- Calls `NSRunningApplication.hide()` on every regular app except the focus target
- Tracks which apps were hidden so Exit can restore them with `unhide()`
- Sets `com.apple.notificationcenterui doNotDisturb` via `defaults write` + kills NotificationCenter

### AppDelegate.swift
- Manages `NSStatusItem` in the system menubar
- Rebuilds the menu fresh on every click (live app list)
- Emoji icon: 🌙 (idle) → 🌕 (active)

### Info.plist
- `LSUIElement = YES` — no Dock icon, no app switcher entry

---

## Do Not Disturb Notes

The DND toggle uses the legacy `com.apple.notificationcenterui` defaults key, which works on macOS 13/14. On macOS 15 (Sequoia), Apple tightened the Focus API — you may need to manually enable a Focus in System Settings and grant Still Mode permission to control it via the Shortcuts/Focus framework.

For a more robust DND solution on macOS 15+, consider:
- Using `NEHotspotHelper` or the Focus framework via `FocusFilterIntent` 
- Or just setting Focus manually before entering Still Mode

---

## App Store Submission Notes

1. **Sandbox** — The app is not sandboxed. Hiding other apps via `NSRunningApplication.hide()` requires `NSAppleEventsUsageDescription` and potentially Accessibility entitlements. App Store submission would require sandboxing + proper entitlements, which limits the ability to hide arbitrary apps.

2. **Notarization** — For distribution outside the App Store, notarize with:
   ```bash
   xcrun notarytool submit StillMode.zip --apple-id you@example.com --team-id XXXXXXXX --wait
   ```

3. **Alternative** — Distribute via direct download or Homebrew cask. This is a power-user tool; the App Store is not the right home for it.

---

## Project Structure

```
stillmode/
  StillMode/
    StillModeApp.swift     # @main, NSApplicationDelegateAdaptor
    AppDelegate.swift      # NSStatusItem + menu logic
    FocusManager.swift     # Hide/show apps, DND toggle, audio
    Info.plist             # LSUIElement = YES
    Assets.xcassets/       # App icon placeholder
  StillMode.xcodeproj/     # Xcode project
  project.yml              # XcodeGen config (optional)
  README.md                # This file
```

---

*Built with Swift + AppKit. No external dependencies. macOS 13+ required.*
