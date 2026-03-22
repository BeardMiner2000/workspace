# Still Mode iOS — Research & Architecture

**Status:** Research phase  
**Target:** Working prototype by morning

---

## iOS Constraints vs macOS

| Feature | macOS | iOS | Status |
|---------|-------|-----|--------|
| Hide other apps | ✅ Yes | ❌ Apple blocks this | Won't work |
| Global event monitoring | ✅ Yes | ❌ Sandbox restricts | Won't work |
| Block app switching | ✅ Yes | ❌ Can't override OS | Won't work |
| Custom overlay | ✅ Yes | ✅ Yes | ✅ Possible |
| Focus timers | ✅ Custom | ✅ Built-in + custom | ✅ Possible |
| Do Not Disturb control | ✅ Yes | ❌ Read-only | Read-only |
| Screen Time integration | ✅ No | ✅ Yes | ✅ Possible |
| Focus mode integration | ✅ No | ✅ Yes (iOS 15+) | ✅ Possible |
| Notifications control | ✅ Custom | ✅ Limited | Partial |

---

## What iOS Still Mode CAN Do

### Core Features (Achievable)
1. **Manual Focus Activation**
   - User taps "Start Focus" button
   - Full-screen UI shows focused task
   - Timer countdown (Pomodoro style)
   - Lock controls with Face ID

2. **Ambient Reminders**
   - Fullscreen notifications every 5/10 min
   - "Are you still focused?" — yes/no
   - Audio/haptic feedback

3. **Smart Notifications**
   - Suppress non-essential notifications
   - Whitelist only critical apps
   - Show on lock screen when focus ends

4. **Session History & Stats**
   - Track focus sessions (duration, app, category)
   - Weekly/monthly trends
   - Awards (streaks, total hours)

5. **Integration Points**
   - Activate Apple Focus mode (if enabled)
   - Send to calendar (block time)
   - Shortcut automation (Siri)
   - HealthKit (track focus as "exercise"?)

### Premium Features
- Multi-timer (pomodoro, breaks)
- Custom categories (work, creative, health)
- Distraction lists (apps to avoid)
- Accountability partner sharing
- Cloud sync (iCloud)

---

## iOS Architecture

### Tech Stack
- **Language:** Swift (SwiftUI)
- **Frameworks:**
  - SwiftUI (UI)
  - Foundation (timers)
  - UserNotifications (alerts)
  - HealthKit (optional stats)
  - WidgetKit (lock screen widget)
  - Intents (Siri)

### Key Classes
1. **FocusSession** — Data model for each session
2. **FocusManager** — Timer logic, notifications, state
3. **HistoryManager** — Persistence, analytics
4. **NotificationManager** — Local notifications, ambient reminders
5. **FocusView** — Main UI (fullscreen overlay)

### Data Persistence
- Core Data or SwiftData (local, encrypted)
- iCloud sync (optional, Premium)

---

## MVP Feature Set

**Launch Features (Week 1):**
- ✅ Start focus session (manual, no blocking)
- ✅ Timer (15/30/45/60 min presets + custom)
- ✅ Full-screen focus UI
- ✅ Session history (tap to see past sessions)
- ✅ Ambient reminder notifications
- ✅ Quick exit option
- ✅ Daily/weekly stats dashboard

**Not in MVP:**
- ❌ App blocking (impossible on iOS)
- ❌ Notification suppression (limited API access)
- ❌ iCloud sync (v1.1)
- ❌ Widgets (v1.1)
- ❌ Focus mode integration (nice-to-have)

---

## Monetization

**Free Tier:**
- 1 focus session per day
- Basic timer (default 30 min)
- Session history (7 days)

**Premium ($2.99):**
- Unlimited sessions
- Custom timers + presets
- Full history + export
- Advanced stats & trends
- Notification customization
- No ads

---

## Licensing

Use same key format: `STILLMODE-XXXX-XXXX-XXXX`
- Shared Keychain between macOS & iOS (iCloud Keychain)
- User buys once, works on both platforms

---

## Timeline

- **Phase 1 (2 hours):** Prototype core UI + timer + persistence
- **Phase 2 (1 hour):** Notifications + ambient reminders
- **Phase 3 (1 hour):** History + stats dashboard
- **Phase 4 (30 min):** Monetization hooks (in-app purchase stub)

**Total: ~4.5 hours to MVP**

---

## Files to Create

```
StillModeIOS/
├── StillModeApp.swift
├── Models/
│   ├── FocusSession.swift
│   ├── FocusManager.swift
│   └── HistoryManager.swift
├── Views/
│   ├── ContentView.swift
│   ├── FocusView.swift
│   ├── HistoryView.swift
│   └── StatsView.swift
├── Managers/
│   ├── NotificationManager.swift
│   └── LicenseManager.swift
└── Assets/
```

---

## Starting Point

1. Create new iOS project in Xcode
2. Delete default ContentView
3. Build data models (FocusSession, etc.)
4. Implement basic timer
5. Create fullscreen focus UI
6. Add persistence
7. Wire up notifications
8. Add history view
