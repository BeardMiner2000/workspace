import AppKit
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    
    var statusItem: NSStatusItem?
    var focusManager = FocusManager()
    var selectedApp: NSRunningApplication?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide from Dock
        NSApp.setActivationPolicy(.accessory)
        
        // Setup menubar icon
        setupStatusItem()
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
            
            let exitItem = NSMenuItem(title: "Exit Still Mode", action: #selector(exitStillMode), keyEquivalent: "\u{1B}")  // Escape key
            exitItem.target = self
            menu.addItem(exitItem)
            
        } else {
            // IDLE STATE
            let apps = focusManager.runningUserApps()
            
            if apps.isEmpty {
                let noApps = NSMenuItem(title: "No apps running", action: nil, keyEquivalent: "")
                noApps.isEnabled = false
                menu.addItem(noApps)
            } else {
                let chooseLabel = NSMenuItem(title: "Select app to focus on:", action: nil, keyEquivalent: "")
                chooseLabel.isEnabled = false
                menu.addItem(chooseLabel)
                
                for app in apps {
                    let name = app.localizedName ?? app.bundleIdentifier ?? "Unknown"
                    let item = NSMenuItem(title: "  \(name)", action: #selector(selectApp(_:)), keyEquivalent: "")
                    item.target = self
                    item.representedObject = app
                    
                    // Add app icon if available (safely)
                    if let icon = app.icon, let img = icon.copy() as? NSImage {
                        let resized = NSImage(size: NSSize(width: 16, height: 16))
                        resized.lockFocus()
                        icon.draw(in: NSRect(x: 0, y: 0, width: 16, height: 16))
                        resized.unlockFocus()
                        item.image = resized
                    }
                    
                    // Checkmark if selected
                    if let selected = selectedApp, selected == app {
                        item.state = .on
                    }
                    
                    menu.addItem(item)
                }
                
                menu.addItem(.separator())
                
                let enterItem = NSMenuItem(
                    title: selectedApp != nil ? "Ready to be Still 🧘" : "Ready to be Still 🧘",
                    action: selectedApp != nil ? #selector(enterStillMode) : nil,
                    keyEquivalent: selectedApp != nil ? "\r" : ""
                )
                enterItem.target = self
                enterItem.isEnabled = selectedApp != nil
                
                // Make button bold and green when enabled
                if selectedApp != nil {
                    let attrs: [NSAttributedString.Key: Any] = [
                        .font: NSFont.boldSystemFont(ofSize: 13)
                    ]
                    enterItem.attributedTitle = NSAttributedString(string: "Ready to be Still 🧘", attributes: attrs)
                }
                
                menu.addItem(enterItem)
            }
        }
        
        menu.addItem(.separator())
        
        let quitItem = NSMenuItem(title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        menu.addItem(quitItem)
        
        statusItem?.menu = menu
        statusItem?.button?.performClick(nil)
    }
    
    // MARK: - Actions
    
    @objc func selectApp(_ sender: NSMenuItem) {
        selectedApp = sender.representedObject as? NSRunningApplication
        // Don't rebuild; let the menu close naturally. User clicks again to confirm.
    }
    
    @objc func enterStillMode() {
        guard let app = selectedApp else { return }
        focusManager.enter(focusOn: app) { [weak self] in
            self?.updateIcon(active: true)
        }
    }
    
    @objc func exitStillMode() {
        focusManager.exit { [weak self] in
            self?.updateIcon(active: false)
            self?.selectedApp = nil
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                self?.buildAndShowMenu()
            }
        }
    }
}
