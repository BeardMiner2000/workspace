import AppKit
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {

    var statusItem: NSStatusItem?
    var focusManager = FocusManager()
    var selectedApps: Set<String> = []  // Track selected app bundle IDs

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide from Dock (belt-and-suspenders in case LSUIElement not set at build time)
        NSApp.setActivationPolicy(.accessory)
        
        // Post a notification to verify this is running
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            NSApplication.shared.dockTile.badgeLabel = "RUNNING"
        }

        setupStatusItem()
    }

    // MARK: - Status Item Setup

    func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        print("🔍 DEBUG: statusItem created: \(statusItem != nil)")
        print("🔍 DEBUG: statusItem.button: \(statusItem?.button != nil)")

        if let button = statusItem?.button {
            button.title = "🌙"
            button.font = NSFont.systemFont(ofSize: 16)
            button.action = #selector(statusItemClicked)
            button.target = self
            button.sendAction(on: [.leftMouseUp, .rightMouseUp])
            print("🔍 DEBUG: statusItem button configured")
        } else {
            print("🔍 DEBUG: ERROR - statusItem or button is nil!")
        }
    }

    func updateIcon(active: Bool) {
        DispatchQueue.main.async {
            self.statusItem?.button?.title = active ? "🌕" : "🌙"
        }
    }

    // MARK: - Menu

    @objc func statusItemClicked() {
        let menu = buildMenu()
        statusItem?.menu = menu
        // Don't call performClick — it closes the menu. Just set it and let the system show it.
    }

    private func buildMenu() -> NSMenu {
        let menu = NSMenu()
        buildMenuItems(into: menu)
        return menu
    }

    private func buildAndShowMenuKeepOpen() {
        // Rebuild the menu to show updated state (exit button gone, app list back)
        let newMenu = buildMenu()
        statusItem?.menu = newMenu
    }

    // MARK: - Actions

    @objc func toggleApp(_ sender: NSMenuItem) {
        guard let app = sender.representedObject as? NSRunningApplication,
              let bundleID = app.bundleIdentifier else { return }
        
        if selectedApps.contains(bundleID) {
            selectedApps.remove(bundleID)
        } else {
            selectedApps.insert(bundleID)
        }
        
        // Schedule menu rebuild AFTER this action handler completes
        // This avoids closing the menu due to NSStatusItem.menu assignment
        DispatchQueue.main.async {
            self.rebuildMenuWithoutClosing()
        }
    }
    
    private func rebuildMenuWithoutClosing() {
        if let menu = statusItem?.menu {
            // Clear old items but keep menu alive by modifying in-place
            menu.removeAllItems()
            // Rebuild items in-place
            buildMenuItems(into: menu)
        }
    }
    
    private func buildMenuItems(into menu: NSMenu) {
        menu.autoenablesItems = false

        // Title
        let titleItem = NSMenuItem(title: "Still Mode", action: nil, keyEquivalent: "")
        titleItem.isEnabled = false
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.boldSystemFont(ofSize: 13)
        ]
        titleItem.attributedTitle = NSAttributedString(string: "Still Mode", attributes: attrs)
        menu.addItem(titleItem)
        menu.addItem(.separator())

        if focusManager.isActive {
            // ── ACTIVE STATE ──
            let appNames = focusManager.focusedApps.compactMap { $0.localizedName }.joined(separator: ", ")
            let statusItem = NSMenuItem(title: "Focusing: \(appNames)", action: nil, keyEquivalent: "")
            statusItem.isEnabled = false
            menu.addItem(statusItem)

            menu.addItem(.separator())

            let exitItem = NSMenuItem(title: "Exit Still Mode", action: #selector(exitStillMode), keyEquivalent: "\u{1B}")  // Escape key
            exitItem.target = self
            menu.addItem(exitItem)

        } else {
            // ── IDLE STATE ──
            let apps = focusManager.runningUserApps()

            if apps.isEmpty {
                let noApps = NSMenuItem(title: "No apps running", action: nil, keyEquivalent: "")
                noApps.isEnabled = false
                menu.addItem(noApps)
            } else {
                let chooseLabel = NSMenuItem(title: "Select apps to keep visible:", action: nil, keyEquivalent: "")
                chooseLabel.isEnabled = false
                menu.addItem(chooseLabel)

                for app in apps {
                    let name = app.localizedName ?? app.bundleIdentifier ?? "Unknown"
                    let item = NSMenuItem(title: "  \(name)", action: #selector(toggleApp(_:)), keyEquivalent: "")
                    item.target = self
                    item.representedObject = app

                    // Icon
                    if let icon = app.icon {
                        let img = icon.copy() as! NSImage
                        img.size = NSSize(width: 16, height: 16)
                        item.image = img
                    }

                    // Checkmark if selected
                    if let bundleID = app.bundleIdentifier, selectedApps.contains(bundleID) {
                        item.state = .on
                    }
                    menu.addItem(item)
                }

                menu.addItem(.separator())

                let enterItem = NSMenuItem(
                    title: "Ready to be Still 🧘",
                    action: !selectedApps.isEmpty ? #selector(enterStillMode) : nil,
                    keyEquivalent: !selectedApps.isEmpty ? "\r" : ""
                )
                enterItem.target = self
                enterItem.isEnabled = !selectedApps.isEmpty
                
                // Make it bold when enabled (white text, just like other items)
                if !selectedApps.isEmpty {
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
    }

    @objc func enterStillMode() {
        let selectedAppsObjects = focusManager.runningUserApps().filter { app in
            if let bundleID = app.bundleIdentifier {
                return selectedApps.contains(bundleID)
            }
            return false
        }
        
        guard !selectedAppsObjects.isEmpty else { return }
        
        focusManager.enter(focusOn: selectedAppsObjects) { [weak self] in
            self?.updateIcon(active: true)
        }
    }

    @objc func exitStillMode() {
        focusManager.exit { [weak self] in
            self?.updateIcon(active: false)
            self?.selectedApps = []
            // Rebuild menu to show idle state
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                self?.buildAndShowMenuKeepOpen()
            }
        }
    }
}
