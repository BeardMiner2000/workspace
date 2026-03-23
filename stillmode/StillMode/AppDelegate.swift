import AppKit
import Security

// MARK: - License Manager

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

// MARK: - Popup Window Delegate

class PopupWindowDelegate: NSObject, NSWindowDelegate {
    var allowClose: Bool = false
    
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        // Only allow close if explicitly permitted (via closePopup or explicit close)
        return allowClose
    }
}

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem?
    var focusManager = FocusManager()
    var selectedApps: Set<String> = []
    var popupWindow: NSWindow?
    var popupWindowDelegate: PopupWindowDelegate?
    var checkboxToBundleID: [NSButton: String] = [:]
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        setupStatusItem()
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        if focusManager.isActive {
            focusManager.exit { }
        }
    }
    
    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem?.button {
            button.title = "🌙"
            button.font = NSFont.systemFont(ofSize: 16)
            button.action = #selector(statusItemClicked)
            button.target = self
        }
    }
    
    func updateIcon(active: Bool) {
        DispatchQueue.main.async {
            self.statusItem?.button?.title = active ? "🌕" : "🌙"
        }
    }
    
    @objc func statusItemClicked() {
        if focusManager.isActive {
            showExitPopup()
        } else {
            showSelectionPopup()
        }
    }
    
    private func showSelectionPopup() {
        let width: CGFloat = 320
        let height: CGFloat = 500
        
        guard let statusBarButton = statusItem?.button else { return }
        let buttonFrame = statusBarButton.window?.frame ?? NSRect.zero
        let x = buttonFrame.midX - width / 2
        let y = buttonFrame.minY - height - 10
        
        let popupRect = NSRect(x: x, y: y, width: width, height: height)
        
        let window = NSWindow(
            contentRect: popupRect,
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: false
        )
        
        window.title = "Still Mode"
        window.level = .floating
        window.isMovableByWindowBackground = true
        window.standardWindowButton(.miniaturizeButton)?.isHidden = true
        window.standardWindowButton(.zoomButton)?.isHidden = true
        
        // Set delegate to prevent accidental window closure
        let windowDelegate = PopupWindowDelegate()
        window.delegate = windowDelegate
        self.popupWindowDelegate = windowDelegate
        
        let contentView = NSView(frame: window.contentView?.bounds ?? NSRect.zero)
        contentView.wantsLayer = true
        contentView.layer?.backgroundColor = NSColor(calibratedWhite: 0.95, alpha: 1).cgColor
        
        var yPosition: CGFloat = height - 40
        
        // Title
        let titleLabel = NSTextField(frame: NSRect(x: 16, y: yPosition, width: width - 32, height: 30))
        titleLabel.stringValue = "Select apps to focus on:"
        titleLabel.isBezeled = false
        titleLabel.drawsBackground = false
        titleLabel.isEditable = false
        titleLabel.font = NSFont.boldSystemFont(ofSize: 13)
        contentView.addSubview(titleLabel)
        yPosition -= 40
        
        // Get running apps
        let apps = focusManager.runningUserApps()
        checkboxToBundleID.removeAll()
        
        // Scroll view
        let scrollView = NSScrollView(frame: NSRect(x: 16, y: 80, width: width - 32, height: yPosition - 20))
        scrollView.hasVerticalScroller = true
        scrollView.autohidesScrollers = true
        
        let clipView = NSClipView()
        scrollView.contentView = clipView
        
        let documentView = NSView(frame: NSRect(x: 0, y: 0, width: width - 32, height: CGFloat(apps.count * 30)))
        
        // Add checkboxes
        for (index, app) in apps.enumerated() {
            let bundleID = app.bundleIdentifier ?? "unknown"
            let appName = app.localizedName ?? bundleID
            
            let checkboxFrame = NSRect(x: 0, y: CGFloat(apps.count - index - 1) * 30, width: width - 32, height: 28)
            let checkbox = NSButton(frame: checkboxFrame)
            checkbox.setButtonType(.switch)
            checkbox.title = appName
            checkbox.target = self
            checkbox.action = #selector(appCheckboxChanged(_:))
            checkbox.state = selectedApps.contains(bundleID) ? .on : .off
            
            documentView.addSubview(checkbox)
            checkboxToBundleID[checkbox] = bundleID
        }
        
        clipView.documentView = documentView
        contentView.addSubview(scrollView)
        
        // Be Still button
        let beStillButton = NSButton(frame: NSRect(x: 16, y: 40, width: width - 32, height: 32))
        beStillButton.title = "🧘 Be Still"
        beStillButton.bezelStyle = .rounded
        beStillButton.target = self
        beStillButton.action = #selector(enterStillMode)
        beStillButton.isEnabled = !selectedApps.isEmpty
        contentView.addSubview(beStillButton)
        
        // Cancel button
        let cancelButton = NSButton(frame: NSRect(x: 16, y: 8, width: width - 32, height: 24))
        cancelButton.title = "Cancel"
        cancelButton.bezelStyle = .rounded
        cancelButton.target = self
        cancelButton.action = #selector(closePopup)
        contentView.addSubview(cancelButton)
        
        window.contentView = contentView
        self.popupWindow = window
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    
    private func showExitPopup() {
        let width: CGFloat = 300
        let height: CGFloat = 150
        
        guard let statusBarButton = statusItem?.button else { return }
        let buttonFrame = statusBarButton.window?.frame ?? NSRect.zero
        let x = buttonFrame.midX - width / 2
        let y = buttonFrame.minY - height - 10
        
        let popupRect = NSRect(x: x, y: y, width: width, height: height)
        
        let window = NSWindow(
            contentRect: popupRect,
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        
        window.title = "Still Mode Active"
        window.level = .floating
        window.isMovableByWindowBackground = true
        window.standardWindowButton(.miniaturizeButton)?.isHidden = true
        window.standardWindowButton(.zoomButton)?.isHidden = true
        
        // Set delegate to prevent accidental window closure
        let windowDelegate = PopupWindowDelegate()
        window.delegate = windowDelegate
        self.popupWindowDelegate = windowDelegate
        
        let contentView = NSView(frame: window.contentView?.bounds ?? NSRect.zero)
        contentView.wantsLayer = true
        contentView.layer?.backgroundColor = NSColor(calibratedWhite: 0.95, alpha: 1).cgColor
        
        // Status label
        let statusLabel = NSTextField(frame: NSRect(x: 16, y: 80, width: width - 32, height: 40))
        statusLabel.stringValue = "Still Mode is active.\nClick below to exit."
        statusLabel.isBezeled = false
        statusLabel.drawsBackground = false
        statusLabel.isEditable = false
        statusLabel.alignment = .center
        contentView.addSubview(statusLabel)
        
        // Exit button
        let exitButton = NSButton(frame: NSRect(x: 16, y: 40, width: width - 32, height: 32))
        exitButton.title = "❌ Exit Still Mode"
        exitButton.bezelStyle = .rounded
        exitButton.target = self
        exitButton.action = #selector(exitStillMode)
        contentView.addSubview(exitButton)
        
        // Cancel button
        let cancelButton = NSButton(frame: NSRect(x: 16, y: 8, width: width - 32, height: 24))
        cancelButton.title = "Cancel"
        cancelButton.bezelStyle = .rounded
        cancelButton.target = self
        cancelButton.action = #selector(closePopup)
        contentView.addSubview(cancelButton)
        
        window.contentView = contentView
        self.popupWindow = window
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    
    @objc func appCheckboxChanged(_ sender: NSButton) {
        guard let bundleID = checkboxToBundleID[sender] else { return }
        
        if sender.state == .on {
            selectedApps.insert(bundleID)
        } else {
            selectedApps.remove(bundleID)
        }
        
        // Update the "Be Still" button state
        updateBeStillButtonState()
    }
    
    private func updateBeStillButtonState() {
        // Find and update the "Be Still" button in the current popup window
        guard let window = popupWindow,
              let contentView = window.contentView else { return }
        
        if let beStillButton = contentView.subviews.first(where: { view in
            if let btn = view as? NSButton, btn.title == "🧘 Be Still" {
                return true
            }
            return false
        }) as? NSButton {
            beStillButton.isEnabled = !selectedApps.isEmpty
        }
    }
    
    @objc func enterStillMode() {
        guard !selectedApps.isEmpty else { return }
        
        let selectedRunningApps = NSWorkspace.shared.runningApplications.filter { app in
            selectedApps.contains(app.bundleIdentifier ?? "")
        }
        
        guard !selectedRunningApps.isEmpty else { return }
        
        closePopup()
        
        focusManager.enter(focusOn: selectedRunningApps) { [weak self] in
            self?.updateIcon(active: true)
        }
    }
    
    @objc func exitStillMode() {
        focusManager.exit { [weak self] in
            self?.updateIcon(active: false)
            self?.selectedApps.removeAll()
            self?.closePopup()
        }
    }
    
    @objc func closePopup() {
        if let window = popupWindow {
            // Temporarily allow closing
            if let delegate = window.delegate as? PopupWindowDelegate {
                delegate.allowClose = true
            }
            window.close()
            popupWindow = nil
        }
    }
}
