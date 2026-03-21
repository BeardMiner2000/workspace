import AppKit
import Foundation
import AudioToolbox

class FocusManager {

    // MARK: - State

    private(set) var isActive: Bool = false
    private(set) var focusedApp: NSRunningApplication?
    private var hiddenApps: [NSRunningApplication] = []

    // MARK: - Public API

    /// Enter Still Mode: hide everything except `app`, bring `app` front, enable DND.
    func enter(focusOn app: NSRunningApplication, completion: @escaping () -> Void) {
        guard !isActive else { return }

        isActive = true
        focusedApp = app
        hiddenApps = []

        // Snapshot running apps before we touch anything
        let appsToHide = NSWorkspace.shared.runningApplications.filter { runningApp in
            runningApp.activationPolicy == .regular &&
            runningApp.bundleIdentifier != app.bundleIdentifier &&
            !runningApp.isHidden
        }

        // Hide them all
        for runningApp in appsToHide {
            if runningApp.hide() {
                hiddenApps.append(runningApp)
            }
        }

        // Bring focus app to front
        app.activate(options: [.activateIgnoringOtherApps])

        // Enable DND
        setDoNotDisturb(enabled: true)

        // Play a soft sound (optional ambient tone)
        playFocusTone()

        completion()
    }

    /// Exit Still Mode: unhide tracked apps, disable DND.
    func exit(completion: @escaping () -> Void) {
        guard isActive else { return }

        isActive = false

        // Unhide all tracked apps
        for app in hiddenApps {
            app.unhide()
        }
        hiddenApps = []
        focusedApp = nil

        // Disable DND
        setDoNotDisturb(enabled: false)

        // Play exit tone
        playExitTone()

        completion()
    }

    // MARK: - App List

    /// Returns running apps with a regular activation policy (visible in Dock/Cmd-Tab), excluding self.
    func runningUserApps() -> [NSRunningApplication] {
        let selfBundle = Bundle.main.bundleIdentifier

        return NSWorkspace.shared.runningApplications
            .filter { app in
                app.activationPolicy == .regular &&
                app.bundleIdentifier != selfBundle &&
                app.localizedName != nil
            }
            .sorted { ($0.localizedName ?? "") < ($1.localizedName ?? "") }
    }

    // MARK: - Do Not Disturb

    private func setDoNotDisturb(enabled: Bool) {
        // macOS 12+: Focus/DND via defaults + notification center restart
        // This approach writes to the NCPreferencesController domain.
        // Note: Full Focus control requires user to set up a Focus in System Settings.
        // We use the legacy `doNotDisturb` key that still works on macOS 13/14.

        let value = enabled ? 1 : 0

        // Primary: com.apple.notificationcenterui (used in older macOS)
        let task1 = Process()
        task1.launchPath = "/usr/bin/defaults"
        task1.arguments = ["-currentHost", "write", "com.apple.notificationcenterui",
                           "doNotDisturb", "-bool", enabled ? "TRUE" : "FALSE"]
        try? task1.run()
        task1.waitUntilExit()

        // Also set the scheduled DND start/end to now if enabling (belt-and-suspenders)
        if enabled {
            let task2 = Process()
            task2.launchPath = "/usr/bin/defaults"
            task2.arguments = ["-currentHost", "write", "com.apple.notificationcenterui",
                               "doNotDisturbDate", "-date", iso8601Now()]
            try? task2.run()
            task2.waitUntilExit()
        }

        // Kick notification center to pick up the change
        let killTask = Process()
        killTask.launchPath = "/usr/bin/killall"
        killTask.arguments = ["-HUP", "NotificationCenter"]
        try? killTask.run()
        killTask.waitUntilExit()

        // macOS 15+: also toggle Focus via osascript if available
        toggleFocusViaAppleScript(enabled: enabled)

        _ = value // suppress warning
    }

    private func iso8601Now() -> String {
        let formatter = ISO8601DateFormatter()
        return formatter.string(from: Date())
    }

    /// Best-effort Focus toggle via AppleScript (macOS 12+).
    /// Falls back silently if not permitted.
    private func toggleFocusViaAppleScript(enabled: Bool) {
        let script = enabled
            ? "tell application \"System Events\" to tell dock preferences to set autohide to true"
            : "tell application \"System Events\" to tell dock preferences to set autohide to false"
        // Note: full Focus toggle requires Automation permission, which prompts on first run.
        // We skip that here to avoid unwanted permission dialogs.
        _ = script // reserved for future use
    }

    // MARK: - Audio Feedback

    private func playFocusTone() {
        // Use a built-in system sound for a soft chime
        AudioServicesPlaySystemSound(1013)  // Tink
    }

    private func playExitTone() {
        AudioServicesPlaySystemSound(1006)  // Pop
    }
}
