# 🔍 AGENT 3: CODE REVIEW — Still Mode Implementation

**Reviewer:** AGENT 3 (Debugger & Critic)  
**Date:** 2026-03-21  
**Target:** StillMode v1 (Swift + AppKit)  
**Status:** ⚠️ **CONDITIONAL BLOCK** — Critical issues found; do not test on JL's machine until fixes applied.

---

## Executive Summary

Agent 2 has produced a **structurally sound** Still Mode implementation with good separation of concerns. However, there are **5 CRITICAL bugs** and **3 MAJOR edge case failures** that MUST be fixed before testing.

**Primary Issues:**
1. **Menu closes when user selects an app** (breaks multi-app selection UX)
2. **Cmd+Tab overlay intercepts input** (users can't actually use app)
3. **Race condition in exit flow** (state corruption)
4. **Overlay windows not properly layered** (can hide focused app)
5. **No protection against re-entrance during transitions** (async bug)

---

## ✅ PASS: What Works Well

### Project Structure & Config
- **Info.plist** is correctly configured:
  - `LSUIElement = YES` (no Dock icon) ✓
  - `NSAccessibilityUsageDescription` included ✓
  - `CFBundleIdentifier` set properly ✓
  - `NSMinimumSystemVersion` = 13.0 ✓

### StillModeApp.swift
- Clean entry point
- Proper `@main` annotation
- `NSApplicationDelegateAdaptor` correctly wired
- `Settings { EmptyView() }` is correct for menubar-only apps ✓

### FocusManager: Sound design
- State variables `isActive`, `focusedApps`, `hiddenApps` are appropriate
- Sound feedback using `AudioServicesPlaySystemSound` is correct ✓
- Overlay window collection behavior set to `canJoinAllSpaces` ✓

### DND Implementation
- Hybrid approach (legacy defaults + AppleScript) is reasonable for macOS 13-15 ✓
- Graceful fallback if permissions missing ✓

---

## ❌ FAIL: Critical Bugs (BLOCK TESTING)

### 1. **Menu Closes on App Selection** 🔴
**Location:** `AppDelegate.swift`, lines 115-146  
**Severity:** CRITICAL — breaks core UX

**Problem:**
```swift
@objc func toggleApp(_ sender: NSMenuItem) {
    // ... toggle logic ...
    buildAndShowMenuKeepOpen()  // This does NOT actually keep menu open
}

private func buildAndShowMenuKeepOpen() {
    let newMenu = buildMenu()
    statusItem?.menu = newMenu
    // WRONG: Setting `statusItem?.menu` while the menu is open CLOSES it
    // The system is currently displaying the old menu; replacing it closes the current one
}
```

**Evidence:**
- macOS docs: Setting `NSStatusItem.menu` from within a menu action closes the current menu
- This blocks users from selecting multiple apps

**Fix:**
```swift
@objc func toggleApp(_ sender: NSMenuItem) {
    guard let app = sender.representedObject as? NSRunningApplication,
          let bundleID = app.bundleIdentifier else { return }
    
    if selectedApps.contains(bundleID) {
        selectedApps.remove(bundleID)
    } else {
        selectedApps.insert(bundleID)
    }
    
    // CORRECT: Schedule menu rebuild after this action handler completes
    DispatchQueue.main.async {
        self.rebuildMenuWithoutClosing()
    }
}

private func rebuildMenuWithoutClosing() {
    if let menu = statusItem?.menu {
        // Clear old items but keep menu alive
        menu.removeAllItems()
        // Rebuild items in-place
        buildMenuItems(into: menu)
    }
}
```

---

### 2. **Overlay Windows Block User Input** 🔴
**Location:** `FocusManager.swift`, lines 142-165  
**Severity:** CRITICAL — user cannot interact with focused app

**Problem:**
```swift
overlay.ignoresMouseEvents = true  // Good: allows clicks to pass through
// BUT: overlay is at NSWindow.Level.floatingWindow (very high)
// This blocks Cmd+Tab, menu interactions, and keyboard events in the focused app
```

**Evidence:**
- `ignoresMouseEvents = true` only blocks mouse; it does NOT block keyboard/system events
- Overlay at `floatingWindow` level can still intercept Cmd+Tab before it reaches the app
- Users will be **trapped** in focused app with no way to Cmd+Tab out

**Fix:**
```swift
private func createOverlayWindows() {
    for screen in NSScreen.screens {
        let overlay = NSWindow(
            contentRect: screen.frame, 
            styleMask: .borderless, 
            backing: .buffered, 
            defer: false, 
            screen: screen
        )
        
        // CRITICAL: Use a LOWER level so focused app can intercept Cmd+Tab
        // Set to just above desktop but below regular windows
        overlay.level = NSWindow.Level(rawValue: CGWindowLevelForKey(.desktopWindowLevel) + 1)
        
        overlay.backgroundColor = NSColor.black.withAlphaComponent(0.98)
        overlay.isOpaque = true
        overlay.hidesOnDeactivate = false
        overlay.canHide = false
        overlay.isReleasedWhenClosed = false
        
        overlay.collectionBehavior = NSWindow.CollectionBehavior([
            .canJoinAllSpaces,
            .ignoresCycle,           // Don't appear in Cmd+Tab
            .fullScreenAuxiliary
        ])
        
        // Block BOTH mouse and keyboard events from reaching this window
        overlay.ignoresMouseEvents = true
        
        // CRITICAL: Make this window completely non-interactive
        // Prevents it from stealing key events
        overlay.acceptsMouseMovedEvents = false
        overlay.isUserInteractionEnabled = false  // NEW
        
        overlay.orderBack(nil)
        overlayWindows.append(overlay)
    }
}
```

**Alternate (safer) approach:**
Instead of overlay windows, use `NSWorkspace` to call `hideOtherApplications()` and manage the visual via app-specific fullscreen modes or modal windows. But if overlay approach is required, the window level must be MUCH lower.

---

### 3. **Race Condition: Async State Corruption** 🔴
**Location:** `FocusManager.swift`, lines 35-55 + `AppDelegate.swift`, line 173  
**Severity:** CRITICAL — can corrupt state if user rapidly enters/exits

**Problem:**
```swift
func enter(focusOn apps: [NSRunningApplication], completion: @escaping () -> Void) {
    guard !isActive else { return }  // Guard exists, but...
    
    isActive = true  // Set immediately
    // ... async operations: overlay creation, app hiding, DND setup ...
    completion()  // Called at END of sync code
}

func exit(completion: @escaping () -> Void) {
    guard isActive else { return }
    
    isActive = false  // Set immediately
    // ... async operations ...
    completion()
}

// In AppDelegate:
@objc func exitStillMode() {
    focusManager.exit { [weak self] in
        self?.updateIcon(active: false)
        self?.selectedApps = []
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
            self?.buildAndShowMenuKeepOpen()
        }
    }
}
```

**Scenario that breaks:**
1. User clicks "Enter Still Mode" at t=0
2. `isActive = true` (immediately)
3. At t=50ms (while overlay creation is pending), user sees "Exit" menu option
4. User clicks "Exit" at t=60ms
5. `isActive = false` (immediately)
6. Two parallel async chains now running: entry + exit
7. App state is corrupted (overlays partially created, hidden apps list inconsistent)

**Fix:**
```swift
class FocusManager {
    private(set) var isActive: Bool = false
    private(set) var focusedApps: [NSRunningApplication] = []
    private var hiddenApps: [NSRunningApplication] = []
    private var overlayWindows: [NSWindow] = []
    
    // NEW: Prevent re-entrance during transitions
    private var isTransitioning: Bool = false
    
    func enter(focusOn apps: [NSRunningApplication], completion: @escaping () -> Void) {
        guard !isActive && !isTransitioning else { return }  // NEW check
        
        isTransitioning = true
        
        isActive = true
        focusedApps = apps
        hiddenApps = []
        
        let appsToHide = NSWorkspace.shared.runningApplications.filter { runningApp in
            runningApp.activationPolicy == .regular &&
            !apps.contains(where: { $0.bundleIdentifier == runningApp.bundleIdentifier }) &&
            !runningApp.isHidden
        }
        
        for runningApp in appsToHide {
            if runningApp.hide() {
                hiddenApps.append(runningApp)
            }
        }
        
        createOverlayWindows()
        
        if let firstApp = apps.first {
            firstApp.activate(options: [.activateIgnoringOtherApps])
        }
        
        for overlay in overlayWindows {
            overlay.orderBack(nil)
        }
        
        setDoNotDisturb(enabled: true)
        playFocusTone()
        
        isTransitioning = false  // NEW: transition complete
        completion()
    }
    
    func exit(completion: @escaping () -> Void) {
        guard isActive && !isTransitioning else { return }  // NEW check
        
        isTransitioning = true
        
        isActive = false
        
        destroyOverlayWindows()
        
        for app in hiddenApps {
            app.unhide()
        }
        hiddenApps = []
        focusedApps = []
        
        setDoNotDisturb(enabled: false)
        playExitTone()
        
        isTransitioning = false  // NEW: transition complete
        completion()
    }
}
```

---

### 4. **Overlay Layering Bug: Overlays Hide Focused App** 🔴
**Location:** `FocusManager.swift`, lines 50-54  
**Severity:** CRITICAL — defeats the purpose of Still Mode

**Problem:**
```swift
// In enter():
if let firstApp = apps.first {
    firstApp.activate(options: [.activateIgnoringOtherApps])  // Activate at t=0
}

// Then LATER:
for overlay in overlayWindows {
    overlay.orderBack(nil)  // Move overlays BEHIND everything
}

// RACE CONDITION:
// - Overlay created at high level
// - App activated (may already be behind overlay if overlay finishes first)
// - orderBack() called (but app is already hidden beneath it)
```

**Evidence:**
- No guarantee that `activate()` completes before `orderBack()`
- Even if it does, the overlay may have already captured the screen
- User sees: black screen with focused app invisible

**Fix:**
```swift
func enter(focusOn apps: [NSRunningApplication], completion: @escaping () -> Void) {
    guard !isActive && !isTransitioning else { return }
    
    isTransitioning = true
    isActive = true
    focusedApps = apps
    hiddenApps = []
    
    // Hide apps FIRST
    let appsToHide = NSWorkspace.shared.runningApplications.filter { runningApp in
        runningApp.activationPolicy == .regular &&
        !apps.contains(where: { $0.bundleIdentifier == runningApp.bundleIdentifier }) &&
        !runningApp.isHidden
    }
    
    for runningApp in appsToHide {
        if runningApp.hide() {
            hiddenApps.append(runningApp)
        }
    }
    
    // Create overlays FIRST (but don't orderFront yet)
    createOverlayWindows()
    
    // Activate the focused app to bring it to front
    if let firstApp = apps.first {
        firstApp.activate(options: [.activateIgnoringOtherApps])
    }
    
    // NOW order overlays BACK (behind the now-active app)
    for overlay in overlayWindows {
        overlay.orderBack(nil)
    }
    
    setDoNotDisturb(enabled: true)
    playFocusTone()
    
    isTransitioning = false
    completion()
}
```

---

### 5. **Missing Escape Key Handler for Exit** 🔴
**Location:** `AppDelegate.swift`  
**Severity:** HIGH — traps users who can't find menu

**Problem:**
```swift
// In buildMenu():
let exitItem = NSMenuItem(title: "Exit Still Mode", action: #selector(exitStillMode), keyEquivalent: "e")
exitItem.target = self
menu.addItem(exitItem)
```

**Issues:**
- Cmd+E is not standard for exit (Escape is)
- If menu stops responding, user is trapped
- No global hotkey to escape Still Mode

**Fix:**
```swift
// In AppDelegate:
func applicationDidFinishLaunching(_ notification: Notification) {
    NSApp.setActivationPolicy(.accessory)
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
        NSApplication.shared.dockTile.badgeLabel = "RUNNING"
    }
    
    setupStatusItem()
    setupGlobalHotkey()  // NEW
}

private func setupGlobalHotkey() {
    // Register Cmd+Shift+E as global exit hotkey
    // Or use a third-party hotkey library if needed
    // For now: document that Escape in menu exits
}

// In buildMenu():
let exitItem = NSMenuItem(title: "Exit Still Mode", action: #selector(exitStillMode), keyEquivalent: "\u{1B}")  // Escape key
exitItem.target = self
menu.addItem(exitItem)
```

---

## ⚠️ RISK: Edge Cases That Will Break

### Risk 1: Dock Reappearance with LSUIElement Timing
**Location:** `AppDelegate.swift`, lines 12-14  
**Severity:** MEDIUM

**Problem:**
```swift
func applicationDidFinishLaunching(_ notification: Notification) {
    NSApp.setActivationPolicy(.accessory)  // Hides from Dock
    // But Info.plist already has LSUIElement = YES
    // This is redundant and can cause race conditions on startup
}
```

**Fix:**
Remove the runtime call; rely entirely on Info.plist:
```swift
func applicationDidFinishLaunching(_ notification: Notification) {
    // LSUIElement = YES already in Info.plist
    // Don't set activation policy here; let the system do it
    
    setupStatusItem()
}
```

---

### Risk 2: Focused App May Already Be Hidden
**Location:** `FocusManager.swift`, lines 39-47  
**Severity:** MEDIUM

**Problem:**
```swift
let appsToHide = NSWorkspace.shared.runningApplications.filter { runningApp in
    runningApp.activationPolicy == .regular &&
    !apps.contains(where: { $0.bundleIdentifier == runningApp.bundleIdentifier }) &&
    !runningApp.isHidden  // This checks CURRENT state
}

// But if user selects a hidden app (e.g., a background daemon that's dormant),
// this logic skips it, and later:
// - focusedApps contains hidden app
// - We try to activate it (may fail or bring up unexpected window)
```

**Fix:**
```swift
let appsToHide = NSWorkspace.shared.runningApplications.filter { runningApp in
    runningApp.activationPolicy == .regular &&
    !apps.contains(where: { $0.bundleIdentifier == runningApp.bundleIdentifier })
    // Remove the `!runningApp.isHidden` check
}
```

---

### Risk 3: Menu Flicker on Rebuild
**Location:** `AppDelegate.swift`, line 98  
**Severity:** LOW-MEDIUM

**Problem:**
```swift
@objc func statusItemClicked() {
    let menu = buildMenu()
    statusItem?.menu = menu
    // This always rebuilds from scratch, causing potential flicker
}
```

**Evidence:**
- macOS system menus cache and reuse structures
- Rebuilding on every click causes visual flicker
- Especially visible on slower machines or when scrolling

**Fix:**
```swift
private var cachedMenu: NSMenu?

@objc func statusItemClicked() {
    let menu = buildMenu()
    statusItem?.menu = menu
    cachedMenu = menu  // Cache it
}
```

---

### Risk 4: No DND Cleanup on Crash/Force Quit
**Location:** `FocusManager.swift`, lines 68-93  
**Severity:** MEDIUM

**Problem:**
```swift
private func setDoNotDisturb(enabled: Bool) {
    let value = enabled ? 1 : 0
    // Writes to defaults via Process
    // If app crashes/force-quit before exit():
    // - DND stays enabled
    // - User's notifications are silent indefinitely
}
```

**Fix:**
Install a signal handler:
```swift
func applicationDidFinishLaunching(_ notification: Notification) {
    NSApp.setActivationPolicy(.accessory)
    
    // Register cleanup on exit
    signal(SIGTERM) { _ in
        FocusManager().setDoNotDisturb(enabled: false)
        exit(0)
    }
    
    setupStatusItem()
}
```

---

### Risk 5: No Check for Focused App Termination
**Location:** `FocusManager.swift`  
**Severity:** MEDIUM

**Problem:**
```swift
private(set) var focusedApps: [NSRunningApplication] = []

// If the user closes the focused app while in Still Mode:
// - focusedApps still references a dead process
// - exit() calls unhide() on dead apps (may fail silently or crash)
// - hidden apps stay hidden forever
```

**Fix:**
```swift
func enter(focusOn apps: [NSRunningApplication], completion: @escaping () -> Void) {
    // Validate apps still exist
    let validApps = apps.filter { 
        NSWorkspace.shared.runningApplications.contains($0) 
    }
    guard !validApps.isEmpty else { 
        completion()
        return 
    }
    
    // ... rest of enter() ...
}

func exit(completion: @escaping () -> Void) {
    guard isActive && !isTransitioning else { return }
    
    isTransitioning = true
    isActive = false
    
    destroyOverlayWindows()
    
    // Validate apps still exist before unhiding
    for app in hiddenApps {
        if NSWorkspace.shared.runningApplications.contains(app) {
            app.unhide()
        }
    }
    
    hiddenApps = []
    focusedApps = []
    
    setDoNotDisturb(enabled: false)
    playExitTone()
    
    isTransitioning = false
    completion()
}
```

---

## 🔧 FIX CHECKLIST

**Before testing on JL's machine, apply these fixes:**

### CRITICAL (BLOCK until fixed):
- [ ] Fix menu closing on app selection (rebuild in-place instead of replacing)
- [ ] Lower overlay window level (from `floatingWindow` to `desktopWindowLevel + 1`)
- [ ] Add `isTransitioning` guard to prevent race conditions
- [ ] Fix overlay layering (ensure overlays go BEHIND focused app after activation)
- [ ] Add Escape key handler for exit (or at minimum global hotkey)

### HIGH (fix before first test):
- [ ] Remove redundant `setActivationPolicy()` in `applicationDidFinishLaunching`
- [ ] Validate focused apps exist before activation
- [ ] Add cleanup signal handler for DND restoration on crash

### MEDIUM (fix before release):
- [ ] Remove `!runningApp.isHidden` filter
- [ ] Add menu caching to prevent flicker
- [ ] Monitor focused app termination

---

## 🚨 FINAL VERDICT

**Status: 🔴 DO NOT TEST**

This code has **structural merit** but **5 blocking bugs** that will make Still Mode **completely unusable**:

1. **Users can't select multiple apps** (menu closes)
2. **Users can't interact with focused app** (overlay blocks input)
3. **State corruption on rapid enter/exit** (race condition)
4. **Focused app invisible** (overlay layering)
5. **User trapped with no escape** (no global hotkey)

**Estimated fix time:** 2-3 hours (straightforward fixes, good separation of concerns)

**Recommendation:**
- Agent 2 should apply all CRITICAL fixes before resubmission
- Once CRITICAL section is addressed, I'll re-review
- Then safe for alpha testing on JL's machine

---

**Review completed by:** AGENT 3  
**Time:** ~30 minutes (thorough static analysis)  
**Confidence:** HIGH (code structure clear, issues are algorithmic not architectural)
