# FINAL SIGN-OFF: Still Mode Code Review

**Date:** Sat 2026-03-21 13:34 PDT  
**Reviewer:** Subagent Sign-Off  
**Status:** 🔴 **NOT APPROVED** — Critical Observer Cleanup Bug Found

---

## Blocker Fixes Verified ✅

### 1. NSWorkspace Monitoring ✅ FIXED
- Using correct `NSWorkspace.shared.notificationCenter` for didActivateApplicationNotification
- Properly listens for app activations

### 2. Menu Flicker ✅ FIXED
- `selectApp()` method no longer rebuilds menu immediately
- Menu closes cleanly after selection
- User must click again to confirm, preventing accidental activations

### 3. Icon Copy ✅ FIXED
- Icon copy wrapped in safe optional cast: `if let icon = app.icon, let img = icon.copy() as? NSImage`
- Prevents nil crashes

---

## 🔴 Critical Issue Found

### Observer Cleanup Bug (FocusManager.swift, line 107)

**Problem:**
```swift
NotificationCenter.default.removeObserver(observer)
```

Should be:
```swift
NSWorkspace.shared.notificationCenter.removeObserver(observer)
```

**Impact:**
- Observer added to `NSWorkspace.shared.notificationCenter` but removed from `NotificationCenter.default`
- Observer is never actually removed → memory leak
- Could cause duplicate notifications on subsequent focus mode entries

**Severity:** HIGH — Must fix before testing

---

## Minor Observations

- **Race Condition (Medium):** 0.1s delay in reactivation (`DispatchQueue.main.asyncAfter`) is soft; fast switchers might slip through. Acceptable for v1, monitor during testing.
- **Icon Resize Logic (Low):** Creates `img` variable but doesn't use it. Code works, but could be cleaner.

---

## Recommendation

**Fix the observer cleanup bug first, then resubmit for approval.**

```swift
// FocusManager.swift, stopMonitoringActivations()
private func stopMonitoringActivations() {
    if let observer = appActivationObserver {
        NSWorkspace.shared.notificationCenter.removeObserver(observer)  // FIX THIS LINE
        appActivationObserver = nil
    }
}
```

Once fixed: **✅ APPROVED FOR TESTING**

---

_Subagent completed 2026-03-21 13:34 PDT_
