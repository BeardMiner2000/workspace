# AGENT 1: Architecture Design — Still Mode Refactor

## Problem Statement
Current Swift/AppKit overlay approach fails due to z-order conflicts, window layering issues, and menu flicker. Overlays leak through focused app windows, breaking the illusion of isolation. Solution: switch to **Accessibility API** to monitor and block app activation events instead of visual masking.

---

## Language Recommendation: **Swift (macOS) + Swift Concurrency**

### Why NOT the alternatives:
- **Kotlin Multiplatform (KMM)**: Elegant for Android/Windows, but macOS support is secondary. Still Mode's power comes from AppKit's deep system integration (AXUIElement, Process Events, DND). KMM buys cross-platform at cost of losing that elegance.
- **Flutter/Dart**: One codebase, weak system integration. Can't intercept Cmd+Tab, can't hook into Accessibility API at needed depth. Cloud-heavy.
- **Electron/React Native**: Too heavy, poor Accessibility API access, worse battery on menubar apps.

### Why Swift:
1. **AppKit is the right tool**: Direct access to AXUIElement, CGEvent taps, ProcessEvents. No layer between you and the system.
2. **Cross-platform via native ports**: macOS (AppKit) → iOS (SwiftUI) → Android (Kotlin rewrite) → Windows (SwiftUI Windows). Share business logic, rewrite UI per platform. This is cleaner than a unified fragile codebase.
3. **DX is unbeatable**: Swift concurrency, type safety, live preview for UI. Faster iteration.
4. **Still Mode is a *system* tool**: It needs to be lean, responsive, and privileged. Swift compiles to a single binary with zero runtime overhead.

**Strategy**: macOS gets AppKit + Accessibility. iOS gets SwiftUI. Others rewritten natively. Shared domain model in Swift Package.

---

## Architecture: Accessibility API + Event Tapping

### High-Level Flow
```
┌─────────────────────────────────────────────────────────┐
│  STILL MODE: Accessibility-Based Blocking             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [Menubar UI] ← (state updates)                        │
│       ↓                                                 │
│  [Enter Still Mode] → [AccessibilityMonitor]           │
│       ↓                                                 │
│  ┌─ Monitor all window activation events via AX API   │
│  │   • Hook NSWorkspace.didActivateApplicationNotification
│  │   • Block activation if app ≠ focused_app          │
│  │   • Use CGEventTap to intercept Cmd+Tab            │
│  ├─ When user tries to switch apps:                   │
│  │   1. CGEventTap intercepts key combo               │
│  │   2. Check if target_app in focus_list?           │
│  │   3. YES → allow activation                        │
│  │   4. NO → consume event, activate focus_app        │
│  └─ Exit button: Float small SwiftUI window at (0,0)  │
│     (corner anchor, always accessible, low z-level)   │
│                                                         │
│  [Do Not Disturb] (via Focus API, cleaner than before)│
│  [Audio Feedback]                                      │
└─────────────────────────────────────────────────────────┘
```

### Key Insight: Why This Fixes The Problem
- **No overlays**: No z-order conflicts, no window layering nightmares.
- **Blocking at source**: Intercept Cmd+Tab *before* it activates a window.
- **Exit button**: Lightweight SwiftUI window anchored to corner (0,0), styled as a small red X. Always reachable.
- **Cmd+Tab handling**: If user presses Cmd+Tab to an unfocused app, CGEventTap detects it, consumes the event, and re-activates the focus app instead.

---

## Implementation Checklist

- [ ] **Phase 1: Accessibility Monitor** — Create `AXMonitor` class using NSWorkspace notifications + CGEventTap for Cmd+Tab detection. Handle app activation events, consume non-allowed keys.

- [ ] **Phase 2: Exit Button UI** — Swap overlay windows for single SwiftUI `FloatingExitWindow` anchored to (0, 0) with fixed position. Style as compact red button with close icon. Use `canBecomeKey = true` for interaction.

- [ ] **Phase 3: Focus Enforcement Loop** — Add periodic check every 500ms: if foreground app ≠ focused_app and not in allowed list, re-activate focus_app. Prevents escape via Mission Control, Space changes, Cmd+Up.

- [ ] **Phase 4: Multi-App Support** — Update menu to allow selecting 1-N apps. AXMonitor's allow-list checks if activated_app in `focusedApps` set rather than `== first_app`.

- [ ] **Phase 5: Polish & macOS 15 DND** — Test on Sequoia, migrate DND to modern Focus API if available, add keyboard shortcut for instant exit (Cmd+Esc?), smooth transitions.

---

## Technical Debt Addressed
| Problem | Old | New |
|---------|-----|-----|
| Z-order conflicts | Overlay z-level wars | No overlays |
| Window leak-through | Futile layering | Event interception |
| Menu flicker | Rebuild every click | Cache until state change |
| Escape via Mission Control | Can't intercept | CGEventTap blocks Cmd+Tab, periodic loop re-enforces |

---

## Next Steps
1. Refactor `FocusManager` into two classes: `AXMonitor` (Accessibility) and `FocusEnforcer` (periodic reactivation).
2. Replace `createOverlayWindows()` with `createExitButton()` — SwiftUI window only.
3. Add CGEventTap in `AXMonitor.start()`, teardown in `stop()`.
4. Test on macOS 13, 14, 15 (Sequoia).
5. Plan iOS/Android rewrites as native projects (no KMM needed).

**Elegance Metric**: From 180 lines of overlay logic → ~100 lines of Accessibility API. Smaller, simpler, more reliable.

