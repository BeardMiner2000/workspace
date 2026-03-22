# Still Mode – Final Code Review

1. **Prevent app switching?** **No.** `FocusManager.startMonitoringActivations()` registers for `NSWorkspace.didActivateApplicationNotification` via `NotificationCenter.default`, but those workspace notifications are delivered through `NSWorkspace.shared.notificationCenter`. As written, the observer never fires, so rogue apps aren’t re-hidden and the focused app isn’t re-activated. Result: command-tabbing or launching another app will succeed.

2. **Clean exit path?** **Yes (with current flow).** `exitStillMode` calls `FocusManager.exit`, which stops monitoring, unhides every tracked app, disables DND, resets selection, and updates the icon before rebuilding the menu. The ESC key equivalent also maps to `exitStillMode`, so there’s a deterministic way out.

3. **Menu flicker?** **No.** `buildAndShowMenu` rebuilds a fresh `NSMenu`, assigns it to the status item, and triggers a programmatic `performClick`. Because `selectApp` schedules another rebuild-and-click 100 ms later, picking an app immediately reopens the menu, which looks like a flicker/popup loop. Consider rebuilding without re-triggering `performClick` (or use `popUpMenu` once) so the menu only appears when the user requests it.

4. **Obvious bugs/crashes?** **Yes – critical.** Beyond the broken activation observer noted above, forcing app icons through `icon.copy() as! NSImage` will crash for apps whose icons don’t support copying (rare but possible). Use `icon.copy() as? NSImage` or draw into a new `NSImage` safely.

**Critical issues:**
- NSWorkspace activation monitoring is wired to the wrong notification center, so Still Mode never actually enforces focus.
- Menu auto-reopens after selection, leading to visible flicker/looping UX.
- Potential crash when copying app icons with `as! NSImage` if the copy fails.
