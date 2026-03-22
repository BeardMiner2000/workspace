import SwiftUI
import SwiftData

@main
struct StillModeApp: App {
    let modelContainer: ModelContainer
    
    init() {
        // Configure SwiftData
        let config = ModelConfiguration(isStoredInMemoryOnly: false)
        let container = try! ModelContainer(for: FocusSession.self, configurations: config)
        self.modelContainer = container
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView(modelContext: modelContainer.mainContext)
                .modelContainer(modelContainer)
        }
    }
}
