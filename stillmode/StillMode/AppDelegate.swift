import AppKit
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {

    var statusItem: NSStatusItem?
    var focusManager = FocusManager()
    var selectedApp: NSRunningApplication?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide from Dock (belt-and-suspenders in case LSUIElement not set at build time)
        NSApp.setActivationPolicy(.accessory)

        setupStatusItem()
    }

    // MARK: - Status Item Setup

    func setupStatusItem() {
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

    func buildAndShowMenu() {
        let menu = NSMenu()
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
            let focusedName = focusManager.focusedApp?.localizedName ?? "Unknown"
            let statusItem = NSMenuItem(title: "Focusing on: \(focusedName)", action: nil, keyEquivalent: "")
            statusItem.isEnabled = false
            menu.addItem(statusItem)

            menu.addItem(.separator())

            let exitItem = NSMenuItem(title: "Exit Still Mode", action: #selector(exitStillMode), keyEquivalent: "e")
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
                let chooseLabel = NSMenuItem(title: "Focus on…", action: nil, keyEquivalent: "")
                chooseLabel.isEnabled = false
                menu.addItem(chooseLabel)

                for app in apps {
                    let name = app.localizedName ?? app.bundleIdentifier ?? "Unknown"
                    let item = NSMenuItem(title: "  \(name)", action: #selector(selectApp(_:)), keyEquivalent: "")
                    item.target = self
                    item.representedObject = app

                    // Icon
                    if let icon = app.icon {
                        let img = icon.copy() as! NSImage
                        img.size = NSSize(width: 16, height: 16)
                        item.image = img
                    }

                    // Checkmark if selected
                    if let sel = selectedApp, sel == app {
                        item.state = .on
                    }
                    menu.addItem(item)
                }

                menu.addItem(.separator())

                let enterItem = NSMenuItem(
                    title: selectedApp != nil ? "Enter Still Mode  ✓" : "Enter Still Mode",
                    action: selectedApp != nil ? #selector(enterStillMode) : nil,
                    keyEquivalent: selectedApp != nil ? "\r" : ""
                )
                enterItem.target = self
                enterItem.isEnabled = selectedApp != nil
                menu.addItem(enterItem)
            }
        }

        menu.addItem(.separator())

        let quitItem = NSMenuItem(title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        menu.addItem(quitItem)

        statusItem?.menu = menu
        statusItem?.button?.performClick(nil)
        statusItem?.menu = nil  // Clear so next click rebuilds fresh
    }

    // MARK: - Actions

    @objc func selectApp(_ sender: NSMenuItem) {
        selectedApp = sender.representedObject as? NSRunningApplication
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
        }
    }
}
