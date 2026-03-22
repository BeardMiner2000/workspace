import AppKit
import SwiftUI
import Security

// MARK: - License Manager (Simplified)

class LicenseManager {
    static let shared = LicenseManager()
    
    private let keychainService = "com.jl.StillMode.License"
    private let licenseKeyAttribute = "LicenseKey"
    
    var isPremium: Bool {
        return getLicenseKey() != nil
    }
    
    private func getLicenseKey() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: licenseKeyAttribute,
            kSecReturnData as String: true
        ]
        
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        
        guard status == errSecSuccess,
              let data = result as? Data,
              let key = String(data: data, encoding: .utf8) else {
            return nil
        }
        
        return key
    }
    
    func activateLicense(key: String) -> Bool {
        guard isValidFormat(key) else { return false }
        
        guard let data = key.data(using: .utf8) else { return false }
        
        let deleteQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: licenseKeyAttribute
        ]
        SecItemDelete(deleteQuery as CFDictionary)
        
        let addQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: licenseKeyAttribute,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlocked
        ]
        
        let status = SecItemAdd(addQuery as CFDictionary, nil)
        return status == errSecSuccess
    }
    
    private func isValidFormat(_ key: String) -> Bool {
        let pattern = "^STILLMODE-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        guard let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) else {
            return false
        }
        let range = NSRange(key.startIndex..., in: key)
        return regex.firstMatch(in: key, options: [], range: range) != nil
    }
}

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    
    var statusItem: NSStatusItem?
    var focusManager = FocusManager()
    var selectedAppBundleID: String?  // Store bundle ID instead of app object
    var globalEventMonitor: Any?  // Keyboard monitor for Escape key
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide from Dock
        NSApp.setActivationPolicy(.accessory)
        
        // Setup menubar icon
        setupStatusItem()
        
        // Setup global keyboard monitoring for Escape key
        setupGlobalKeyboardMonitor()
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        if let monitor = globalEventMonitor {
            NSEvent.removeMonitor(monitor)
        }
        
        // Exit still mode if active
        if focusManager.isActive {
            focusManager.exit { }
        }
    }
    
    private func setupGlobalKeyboardMonitor() {
        globalEventMonitor = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
            // Escape key = 53
            if event.keyCode == 53 && self?.focusManager.isActive == true {
                self?.exitStillMode()
            }
        }
    }
    
    // MARK: - Status Item Setup
    
    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem?.button {
            button.title = "🌙"
            button.font = NSFont.systemFont(ofSize: 16)
            button.action = #selector(statusItemClicked)
            button.target = self
            button.sendAction(on: [.leftMouseUp, .rightMouseUp])
        }
    }
    
    func updateIcon(active: Bool) {
        DispatchQueue.main.async {
            self.statusItem?.button?.title = active ? "🌕" : "🌙"
        }
    }
    
    // MARK: - Menu
    
    @objc func statusItemClicked() {
        buildAndShowMenu()
    }
    
    private func buildAndShowMenu() {
        let menu = NSMenu()
        menu.autoenablesItems = false
        
        // Title
        let titleItem = NSMenuItem(title: "Still Mode", action: nil, keyEquivalent: "")
        titleItem.isEnabled = false
        let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.boldSystemFont(ofSize: 13)]
        titleItem.attributedTitle = NSAttributedString(string: "Still Mode", attributes: attrs)
        menu.addItem(titleItem)
        menu.addItem(.separator())
        
        if focusManager.isActive {
            // ACTIVE STATE
            if let focusedApp = focusManager.focusedApp {
                let status = NSMenuItem(title: "Focusing: \(focusedApp.localizedName ?? "Unknown")", action: nil, keyEquivalent: "")
                status.isEnabled = false
                menu.addItem(status)
            }
            
            menu.addItem(.separator())
            
            // Exit button (prominent)
            let exitItem = NSMenuItem(title: "❌ Exit Still Mode", action: #selector(exitStillMode), keyEquivalent: "e")
            exitItem.target = self
            let exitAttrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.boldSystemFont(ofSize: 13)
            ]
            exitItem.attributedTitle = NSAttributedString(string: "❌ Exit Still Mode", attributes: exitAttrs)
            menu.addItem(exitItem)
            
            // Also add Escape hint
            let escapeHint = NSMenuItem(title: "(or press ESC)", action: nil, keyEquivalent: "")
            escapeHint.isEnabled = false
            menu.addItem(escapeHint)
            
        } else {
            // IDLE STATE
            let apps = focusManager.runningUserApps()
            let isPremium = LicenseManager.shared.isPremium
            
            if apps.isEmpty {
                let noApps = NSMenuItem(title: "No apps running", action: nil, keyEquivalent: "")
                noApps.isEnabled = false
                menu.addItem(noApps)
            } else {
                let chooseLabel = NSMenuItem(title: isPremium ? "Select app(s) to focus on:" : "Select app to focus on:", action: nil, keyEquivalent: "")
                chooseLabel.isEnabled = false
                menu.addItem(chooseLabel)
                
                for app in apps {
                    let name = app.localizedName ?? app.bundleIdentifier ?? "Unknown"
                    let item = NSMenuItem(title: "  \(name)", action: #selector(selectApp(_:)), keyEquivalent: "")
                    item.target = self
                    item.representedObject = app.bundleIdentifier  // Store bundle ID, not app object
                    
                    // Add app icon if available (safely)
                    if let icon = app.icon, icon.copy() as? NSImage != nil {
                        let resized = NSImage(size: NSSize(width: 16, height: 16))
                        resized.lockFocus()
                        icon.draw(in: NSRect(x: 0, y: 0, width: 16, height: 16))
                        resized.unlockFocus()
                        item.image = resized
                    }
                    
                    // Checkmark if selected (compare by bundle ID)
                    if let selectedID = selectedAppBundleID, selectedID == app.bundleIdentifier {
                        item.state = .on
                    }
                    
                    menu.addItem(item)
                }
                
                menu.addItem(.separator())
                
                let hasSelection = selectedAppBundleID != nil
                let enterItem = NSMenuItem(
                    title: "Ready to be Still 🧘",
                    action: hasSelection ? #selector(enterStillMode) : nil,
                    keyEquivalent: hasSelection ? "\r" : ""
                )
                enterItem.target = self
                enterItem.isEnabled = hasSelection
                
                // Make button bold when enabled
                if hasSelection {
                    let attrs: [NSAttributedString.Key: Any] = [
                        .font: NSFont.boldSystemFont(ofSize: 13)
                    ]
                    enterItem.attributedTitle = NSAttributedString(string: "Ready to be Still 🧘", attributes: attrs)
                }
                
                menu.addItem(enterItem)
            }
        }
        
        menu.addItem(.separator())
        
        // Show license info / upgrade button
        if !LicenseManager.shared.isPremium {
            let upgradeItem = NSMenuItem(title: "Upgrade to Premium", action: #selector(showUpgradePrompt), keyEquivalent: "")
            upgradeItem.target = self
            menu.addItem(upgradeItem)
            menu.addItem(.separator())
        } else {
            let licenseItem = NSMenuItem(title: "✓ Premium Active", action: nil, keyEquivalent: "")
            licenseItem.isEnabled = false
            menu.addItem(licenseItem)
            menu.addItem(.separator())
        }
        
        let quitItem = NSMenuItem(title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        menu.addItem(quitItem)
        
        statusItem?.menu = menu
        statusItem?.button?.performClick(nil)
    }
    
    // MARK: - Actions
    
    @objc func selectApp(_ sender: NSMenuItem) {
        if let newBundleID = sender.representedObject as? String {
            // Toggle: if clicking the same app, deselect it
            if selectedAppBundleID == newBundleID {
                selectedAppBundleID = nil
            } else {
                selectedAppBundleID = newBundleID
            }
        }
        
        // Update menu in-place WITHOUT closing it
        if let menu = statusItem?.menu {
            let hasSelection = selectedAppBundleID != nil
            
            // Update all app items' checkmarks
            for item in menu.items {
                if let bundleID = item.representedObject as? String {
                    item.state = (bundleID == selectedAppBundleID) ? .on : .off
                }
            }
            
            // Find and update the "Ready to be Still" button
            if let enterItem = menu.items.first(where: { $0.title.contains("Ready to be Still") }) {
                enterItem.isEnabled = hasSelection
                if hasSelection {
                    enterItem.action = #selector(enterStillMode)
                } else {
                    enterItem.action = nil
                }
            }
        }
    }
    
    @objc func enterStillMode() {
        guard let bundleID = selectedAppBundleID else { return }
        
        // Find the running app with this bundle ID
        guard let app = NSWorkspace.shared.runningApplications.first(where: { $0.bundleIdentifier == bundleID }) else {
            return
        }
        
        focusManager.enter(focusOn: app) { [weak self] in
            self?.updateIcon(active: true)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                self?.buildAndShowMenu()
            }
        }
    }
    
    @objc func exitStillMode() {
        focusManager.exit { [weak self] in
            self?.updateIcon(active: false)
            self?.selectedAppBundleID = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                self?.buildAndShowMenu()
            }
        }
    }
    
    @objc func showUpgradePrompt() {
        let alert = NSAlert()
        alert.messageText = "Upgrade to Still Mode Premium"
        alert.informativeText = "Premium unlocks:\n• Focus on multiple apps\n• Focus timers (15m, 30m, 1h)\n• Session history & stats\n\nOne-time purchase: $2.99"
        alert.addButton(withTitle: "Learn More")
        alert.addButton(withTitle: "Enter License Key")
        alert.addButton(withTitle: "Cancel")
        
        let response = alert.runModal()
        
        switch response {
        case .alertFirstButtonReturn:
            // Open website
            NSWorkspace.shared.open(URL(string: "https://stillmode.app")!)
        case .alertSecondButtonReturn:
            // Show license entry dialog
            showLicenseEntryDialog()
        default:
            break
        }
    }
    
    private func showLicenseEntryDialog() {
        let alert = NSAlert()
        alert.messageText = "Enter License Key"
        alert.informativeText = "Paste your license key (format: STILLMODE-XXXX-XXXX-XXXX)"
        
        let textField = NSTextField(frame: NSRect(x: 0, y: 0, width: 300, height: 24))
        textField.placeholderString = "STILLMODE-XXXX-XXXX-XXXX"
        alert.accessoryView = textField
        
        alert.addButton(withTitle: "Activate")
        alert.addButton(withTitle: "Cancel")
        
        let response = alert.runModal()
        
        if response == .alertFirstButtonReturn, !textField.stringValue.isEmpty {
            if LicenseManager.shared.activateLicense(key: textField.stringValue) {
                NSAlert(title: "Success", message: "License activated! Restart the app to see premium features.").runModal()
                buildAndShowMenu()
            } else {
                NSAlert(title: "Invalid License", message: "The license key format is incorrect or invalid.").runModal()
            }
        }
    }
}

extension NSAlert {
    convenience init(title: String, message: String) {
        self.init()
        self.messageText = title
        self.informativeText = message
        self.addButton(withTitle: "OK")
    }
}
