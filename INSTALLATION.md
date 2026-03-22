# Still Mode — Installation Guide

## Quick Start (< 2 minutes)

### Step 1: Disable Code Signing Requirement (Temporary)
Since Still Mode isn't code-signed yet, macOS will block it on first launch.

```bash
# Run this ONCE to allow Still Mode to run
sudo spctl --add --label "Still Mode" ~/Library/Developer/Xcode/DerivedData/StillMode-*/Build/Products/Release/StillMode.app
```

Or manually:
1. Open System Settings → Privacy & Security
2. Find the message: "Still Mode was blocked"
3. Click "Open Anyway"

### Step 2: Grant Accessibility Permission

1. **Open System Settings**
2. Go to **Privacy & Security → Accessibility**
3. Click the **`+`** button
4. Use **Cmd+Shift+G** to open "Go to Folder"
5. Paste: `/Users/jl/Library/Developer/Xcode/DerivedData/StillMode-biajbqnduufjnwdzfpdbdllcwylf/Build/Products/Release/`
6. Select `StillMode.app` and click **Open**

### Step 3: Launch

```bash
open ~/Library/Developer/Xcode/DerivedData/StillMode-biajbqnduufjnwdzfpdbdllcwylf/Build/Products/Release/StillMode.app
```

Or use Finder to navigate to that folder and double-click `StillMode.app`.

---

## For Production Release

### Code Signing

To sign the app with your Developer Certificate:

```bash
codesign --deep --force --verify --verbose --sign "Apple Development: Your Name (TEAM_ID)" \
  ~/Library/Developer/Xcode/DerivedData/StillMode-biajbqnduufjnwdzfpdbdllcwylf/Build/Products/Release/StillMode.app
```

### Creating a DMG Installer

```bash
# Create DMG
hdiutil create -volname "Still Mode" \
  -srcfolder ~/Library/Developer/Xcode/DerivedData/StillMode-biajbqnduufjnwdzfpdbdllcwylf/Build/Products/Release/ \
  -ov -format UDZO \
  ~/Desktop/StillMode-1.0.dmg
```

### Notarization (for macOS 10.15+)

```bash
# Submit for notarization (requires Apple Developer account)
xcrun notarytool submit ~/Desktop/StillMode-1.0.dmg --apple-id your-apple-id@icloud.com --team-id TEAM_ID

# Staple the notarization ticket
xcrun stapler staple ~/Desktop/StillMode-1.0.dmg
```

---

## Distribution Channels

### Option 1: Direct Download (stillmode.app)
- Host DMG on website
- Users download and drag to Applications

### Option 2: Homebrew Cask
```bash
# Create cask formula
brew cask create stillmode
```

### Option 3: App Store
- Requires code signing and notarization
- More discovery but takes 1-2 weeks for review

### Option 4: Gumroad
- Instant distribution
- Licensing key generation
- Direct payments to your account

---

## Verification

After installation, verify everything works:

```bash
# Check if running
pgrep StillMode || echo "Not running"

# Check Accessibility permission
defaults read /Library/Application\ Support/com.apple.TCC/TCC.db 2>/dev/null | grep -i stillmode || echo "Permission not granted"

# Test app blocking
# 1. Click 🌙
# 2. Select Chrome
# 3. Click "Ready to be Still"
# 4. Try to switch to Safari (should fail)
# 5. Press ESC (should exit)
```

---

## Troubleshooting

### "Still Mode is damaged and can't be opened"
This happens when code signing is missing. Run:
```bash
sudo xattr -rd com.apple.quarantine ~/Library/Developer/Xcode/DerivedData/StillMode-*/Build/Products/Release/StillMode.app
```

### "Still Mode needs permission to access your apps"
Grant Accessibility (Step 2 above).

### App blocking doesn't work
- Verify Accessibility permission is granted
- Make sure the app you selected is a regular app (not System Preferences, etc.)
- Restart Still Mode

---

## Next Steps

1. ✅ Still Mode is ready to use
2. 📝 Create landing page at stillmode.app
3. 💰 Set up payment (Gumroad or Stripe)
4. 🚀 Launch on Product Hunt, Twitter, etc.
