import AppKit
import Foundation
import AudioToolbox

class FocusManager: NSObject {
    
    // MARK: - State
    
    private(set) var isActive: Bool = false
    private(set) var focusedApp: NSRunningApplication?
    private var hiddenApps: [NSRunningApplication] = []
    private var appActivationObserver: NSObjectProtocol?
    
    // MARK: - Initialization
    
    override init() {
        super.init()
    }
    
    // MARK: - Public API
    
    func enter(focusOn app: NSRunningApplication, completion: @escaping () -> Void) {
        guard !isActive else { return }
        
        isActive = true
        focusedApp = app
        hiddenApps = []
        
        // Snapshot all running apps
        let allApps = NSWorkspace.shared.runningApplications
        
        // Hide all except the focused app
        for runningApp in allApps {
            // Skip system apps, the focused app, and already-hidden apps
            if runningApp.activationPolicy == .regular &&
               runningApp.bundleIdentifier != app.bundleIdentifier &&
               !runningApp.isHidden {
                if runningApp.hide() {
                    hiddenApps.append(runningApp)
                }
            }
        }
        
        // Bring focused app to front
        app.activate(options: [.activateIgnoringOtherApps])
        
        // Enable Do Not Disturb
        setDoNotDisturb(enabled: true)
        
        // Play entry tone
        playFocusTone()
        
        // Monitor for rogue app activations and block them
        startMonitoringActivations()
        
        completion()
    }
    
    func exit(completion: @escaping () -> Void) {
        guard isActive else { return }
        
        isActive = false
        
        // Stop monitoring
        stopMonitoringActivations()
        
        // Unhide all tracked apps
        for app in hiddenApps {
            app.unhide()
        }
        hiddenApps = []
        focusedApp = nil
        
        // Disable Do Not Disturb
        setDoNotDisturb(enabled: false)
        
        // Play exit tone
        playExitTone()
        
        completion()
    }
    
    // MARK: - App Monitoring
    
    private func startMonitoringActivations() {
        // Monitor when apps try to activate via NSWorkspace notifications
        appActivationObserver = NotificationCenter.default.addObserver(
            forName: NSWorkspace.didActivateApplicationNotification,
            object: NSWorkspace.shared,
            queue: .main
        ) { [weak self] notification in
            guard let self = self, self.isActive else { return }
            
            if let activatedApp = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication {
                // If a non-focused app tries to activate, immediately reactivate the focused app
                if activatedApp.bundleIdentifier != self.focusedApp?.bundleIdentifier {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                        self.focusedApp?.activate(options: [.activateIgnoringOtherApps])
                    }
                }
            }
        }
    }
    
    private func stopMonitoringActivations() {
        if let observer = appActivationObserver {
            NotificationCenter.default.removeObserver(observer)
            appActivationObserver = nil
        }
    }
    
    // MARK: - Do Not Disturb
    
    private func setDoNotDisturb(enabled: Bool) {
        let value = enabled ? 1 : 0
        
        // Method 1: Try modern Focus API if available (macOS 12+)
        if #available(macOS 12.0, *) {
            // Focus mode via defaults (newer approach)
            let process = Process()
            process.launchPath = "/usr/bin/defaults"
            process.arguments = ["-currentHost", "write", "com.apple.notificationcenterui", "doNotDisturb", "-int", "\(value)"]
            try? process.run()
            process.waitUntilExit()
        }
        
        // Method 2: Legacy DND via defaults
        let task = Process()
        task.launchPath = "/usr/bin/defaults"
        task.arguments = ["-currentHost", "write", "com.apple.notificationcenterui", "doNotDisturb", "-bool", enabled ? "TRUE" : "FALSE"]
        try? task.run()
        task.waitUntilExit()
        
        // Notify the system
        let killTask = Process()
        killTask.launchPath = "/usr/bin/killall"
        killTask.arguments = ["-HUP", "NotificationCenter"]
        try? killTask.run()
        killTask.waitUntilExit()
    }
    
    // MARK: - Audio Feedback
    
    private func playFocusTone() {
        AudioServicesPlaySystemSound(1013)  // Tink
    }
    
    private func playExitTone() {
        AudioServicesPlaySystemSound(1006)  // Pop
    }
    
    // MARK: - Utility
    
    func runningUserApps() -> [NSRunningApplication] {
        return NSWorkspace.shared.runningApplications.filter { app in
            app.activationPolicy == .regular
        }
    }
}
