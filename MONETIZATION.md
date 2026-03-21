# Still Mode — Monetization Strategy

**Model:** Freemium  
**Free tier:** 1 app focus (single focus mode, unlimited time)  
**Premium tier:** Unlimited apps (rotate between multiple focus modes, advanced features)  
**Price target:** $2.99-$4.99 one-time purchase

---

## Freemium Features

### Free Tier (Default)
- ✅ Focus on 1 app at a time (unlimited duration)
- ✅ Basic entry/exit
- ✅ Escape key to exit
- ✅ Do Not Disturb toggle
- ❌ Cannot select multiple apps
- ❌ No timer/sessions
- ❌ No focus history

### Premium Tier ($2.99 one-time)
- ✅ All free features
- ✅ Focus on 2+ apps simultaneously
- ✅ Focus timer (15min, 30min, 1hr, custom)
- ✅ Session history & stats
- ✅ Custom focus labels
- ✅ Quick-switch between focus sets
- ✅ App-specific pause/resume
- ✅ No ads (if any)

---

## Implementation Plan

### Phase 1: Licensing Engine
1. `LicenseManager.swift` — check premium status
2. Store license key in Keychain
3. Default: free (1 app max)
4. Premium unlock via license key or in-app purchase stub

### Phase 2: UI Gating
1. Multi-app selector → disabled in free tier (show "Upgrade to Premium" button)
2. Timer feature → premium only
3. History tab → premium only
4. License check on startup

### Phase 3: App Store Integration (Optional)
1. Stub for in-app purchase (if selling via App Store)
2. License validation endpoint (if selling direct)

### Phase 4: Direct Sales
1. License generation (simple UUID-based)
2. Gumroad / Stripe integration (user handles)
3. License key distribution in receipt

---

## Timeline
- **Phase 1:** 1 hour (LicenseManager + Keychain storage)
- **Phase 2:** 1.5 hours (UI gating + premium labels)
- **Phase 3:** 0.5 hours (stubbed in-app purchase)
- **Phase 4:** 1 hour (license validation logic)

**Total:** ~4 hours to full monetization-ready

---

## Files to Create/Modify

**New files:**
- `LicenseManager.swift` — license validation
- `PremiumOverlayViewController.swift` — upgrade prompts

**Modify:**
- `AppDelegate.swift` — add license check on startup
- `FocusManager.swift` — gate multi-app focus
- Menu building — show premium-only indicators

---

## Direct Sales Strategy

**Delivery method:** License key emailed to customer  
**Platform:** Gumroad (you handle) or Stripe (you handle)  
**License format:** `STILLMODE-XXXX-XXXX-XXXX` (simple UUID)  

**Validation:** App checks Keychain for license key on startup. If not present → free tier.

---

## Start Date
Ready to begin when you confirm testing is done.
