import SwiftUI
import AppKit

@main
struct StillModeApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        // No windows — this is a menubar-only app
        Settings {
            EmptyView()
        }
    }
}
