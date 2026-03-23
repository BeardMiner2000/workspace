import AppKit
import Foundation
import AudioToolbox

class FocusManager: NSObject {
    
    // MARK: - State
    
    private(set) var isActive: Bool = false
    private(set) var focusedApps: [NSRunningApplication]?
    private var hiddenApps: [NSRunningApplication] = []
    private var appActivationObserver: NSObjectProtocol?
    
    // MARK: - Initialization
    
    override init() {
        super.init()
    }
    
    // MARK: - Public API
    
    func enter(focusOn apps: [NSRunningApplication], completion: @escaping () -> Void) {
        guard !isActive else { return }
        guard !apps.isEmpty else { return }
        
        isActive = true
        focusedApps = apps
        hiddenApps = []
        
        // Snapshot all running apps
        let allApps = NSWorkspace.shared.runningApplications
        
        // Hide all except the focused apps
        for runningApp in allApps {
            let isFocused = apps.contains { $0.bundleIdentifier == runningApp.bundleIdentifier }
            
            if runningApp.activationPolicy == .regular &&
               !isFocused &&
               !runningApp.isHidden {
                if runningApp.hide() {
                    hiddenApps.append(runningApp)
                }
            }
        }
        
        // Bring focused apps to front (in order)
        for app in apps {
            app.activate(options: [.activateIgnoringOtherApps])
        }
        
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
        focusedApps = nil
        
        // Disable Do Not Disturb
        setDoNotDisturb(enabled: false)
        
        // Play exit tone
        playExitTone()
        
        completion()
    }
    
    // MARK: - App Monitoring
    
    private func startMonitoringActivations() {
        // Monitor when apps try to activate
        appActivationObserver = NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.didActivateApplicationNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let self = self, self.isActive else { return }
            
            if let activatedApp = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication {
                // If a non-focused app tries to activate, immediately reactivate the focused apps
                let isFocused = self.focusedApps?.contains { $0.bundleIdentifier == activatedApp.bundleIdentifier } ?? false
                
                if !isFocused {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                        // Reactivate the first focused app
                        self.focusedApps?.first?.activate(options: [.activateIgnoringOtherApps])
                    }
                }
            }
        }
    }
    
    private func stopMonitoringActivations() {
        if let observer = appActivationObserver {
            NSWorkspace.shared.notificationCenter.removeObserver(observer)
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
