# Code Review: Why "Ready to be Still 🧘" Isn't Activating Still Mode

## Flow Trace

### Step 1: User Selects App
```
User clicks app → statusItemClicked() → buildAndShowMenu()
```
- Menu is built and displayed
- `selectApp()` is attached to each app menu item with `action: #selector(selectApp(_:))`
- When clicked: `selectApp()` sets `selectedAppBundleID` and rebuilds menu

✅ **This works correctly.**

---

### Step 2: Menu Rebuilds with Checkmark
```
selectApp() → DispatchQueue.main.asyncAfter(0.05) → buildAndShowMenu()
```
- Menu is rebuilt
- The selected app now shows a checkmark: `item.state = .on`
- The "Ready to be Still 🧘" button is now **enabled**: `enterItem.isEnabled = hasSelection`
- The button gets a **bold font** and has an action set: `action: #selector(enterStillMode)`

✅ **This works correctly.**

---

## 🔴 THE CRITICAL BUG: Menu Closes Before Click is Registered

### Step 3: User Clicks "Ready to be Still 🧘" — **BUT THE MENU IS CLOSED**

Here's the issue:

**When `selectApp()` is called:**
1. It sets `selectedAppBundleID`
2. It calls: `self.buildAndShowMenu()` with a 0.05s delay
3. `buildAndShowMenu()` does: `statusItem?.menu = menu` and then `statusItem?.button?.performClick(nil)`

**The `performClick(nil)` is the culprit.** This line:
```swift
statusItem?.button?.performClick(nil)
```

This **closes the currently open menu** and should reopen it. However, there's a timing issue:

1. User clicks app in menu → `selectApp()` called
2. `selectApp()` schedules `buildAndShowMenu()` for 50ms later
3. **But the menu is STILL OPEN when `buildAndShowMenu()` is called**
4. Assigning a new menu (`statusItem?.menu = menu`) while the old menu is displayed causes a transition
5. `performClick(nil)` is supposed to re-toggle the menu open, but there's a race condition

### The Race Condition

When the user clicks an app item:
- The menu stays open temporarily (it hasn't been dismissed yet)
- `selectApp()` returns, but the menu is still rendering
- The 50ms async fires
- `buildAndShowMenu()` assigns the new menu
- The menu gets rebuilt, **BUT the focus has been lost**
- The user's next click (on "Ready to be Still") may not register because the menu handling is in a weird state

---

## 🔍 Root Cause: Menu Rebuild Timing

The problem isn't that `enterStillMode()` isn't being called — it's that **the menu closes between selecting an app and clicking the activation button.**

### Evidence in the Code:

**AppDelegate.swift, lines 294–296:**
```swift
// Rebuild menu to show checkmark and enable button
DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
    self.buildAndShowMenu()
}
```

**AppDelegate.swift, lines 247:**
```swift
statusItem?.button?.performClick(nil)
```

The `performClick(nil)` is meant to re-open the menu after rebuilding, but:
1. It's async and timing-dependent
2. The menu might not fully transition
3. macOS menu handling is event-driven, not reliable with async manipulation

---

## 🎯 The Fix

### Option 1: **Don't Close the Menu After Selection (BEST)**

Remove the menu rebuild after `selectApp()`. Instead, update the menu items in-place:

```swift
@objc func selectApp(_ sender: NSMenuItem) {
    if let newBundleID = sender.representedObject as? String {
        if selectedAppBundleID == newBundleID {
            selectedAppBundleID = nil
        } else {
            selectedAppBundleID = newBundleID
        }
    }
    
    // Update the menu in-place WITHOUT closing it
    if let menu = statusItem?.menu {
        updateMenuCheckmarks(menu)
        updateEnterButtonState(menu)
    }
}
```

This avoids closing/reopening the menu entirely.

---

### Option 2: **Delay Menu Rebuild Until Menu Closes**

Listen for menu dismissal before rebuilding:

```swift
@objc func selectApp(_ sender: NSMenuItem) {
    if let newBundleID = sender.representedObject as? String {
        if selectedAppBundleID == newBundleID {
            selectedAppBundleID = nil
        } else {
            selectedAppBundleID = newBundleID
        }
    }
    
    // Delay rebuild until menu is definitely closed
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
        self.buildAndShowMenu()
    }
}
```

But this feels clunky and slow.

---

### Option 3: **Use Menu Delegates for Cleaner Updates**

Implement `NSMenuDelegate` to handle menu display/dismissal events:

```swift
class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    
    func menuDidClose(_ menu: NSMenu) {
        // Rebuild if needed after menu closes
    }
    
    func menuWillOpen(_ menu: NSMenu) {
        // Update checkmarks before menu opens
    }
}
```

---

## 📋 Summary

| Issue | Details | Impact |
|-------|---------|--------|
| **Root Cause** | Menu rebuilt while still open; `performClick(nil)` causes state confusion | User selects app, menu closes, next click doesn't register |
| **Why It Fails** | Menu event handling is interrupted mid-sequence | `enterStillMode()` isn't reached |
| **Best Fix** | Update menu items in-place without closing/reopening | Smooth UX, no timing issues |

---

## 🛠 Recommended Implementation

Replace the `selectApp()` method with:

```swift
@objc func selectApp(_ sender: NSMenuItem) {
    if let newBundleID = sender.representedObject as? String {
        if selectedAppBundleID == newBundleID {
            selectedAppBundleID = nil
        } else {
            selectedAppBundleID = newBundleID
        }
    }
    
    print("Selected app: \(selectedAppBundleID ?? "none")")
    
    // Update checkmarks and button state WITHOUT closing the menu
    if let menu = statusItem?.menu {
        let hasSelection = selectedAppBundleID != nil
        
        // Find and update all app items
        for item in menu.items {
            if let bundleID = item.representedObject as? String {
                let isSelected = bundleID == selectedAppBundleID
                item.state = isSelected ? .on : .off
            }
        }
        
        // Find and update the enter button
        if let enterItem = menu.items.first(where: { $0.title.contains("Ready to be Still") }) {
            enterItem.isEnabled = hasSelection
            if !hasSelection {
                enterItem.action = nil
            } else {
                enterItem.action = #selector(enterStillMode)
            }
        }
    }
}
```

This keeps the menu open, updates state immediately, and lets the user click "Ready to be Still" without delay or re-opening.

---

## ✅ Verification Checklist

After implementing the fix:
- [ ] Select an app — checkmark appears immediately
- [ ] "Ready to be Still" button enables immediately
- [ ] Click "Ready to be Still" while menu is still open
- [ ] `enterStillMode()` is called and activates focus mode
- [ ] App is brought to focus, others are hidden
- [ ] Focus tone plays
