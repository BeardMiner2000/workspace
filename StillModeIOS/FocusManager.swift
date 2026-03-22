import Foundation
import SwiftData
import UserNotifications
import Combine

@MainActor
class FocusManager: NSObject, ObservableObject {
    
    @Published var currentSession: FocusSession?
    @Published var isInFocus: Bool = false
    @Published var timeRemaining: TimeInterval = 0
    @Published var progress: Double = 0
    
    private var timer: Timer?
    private let modelContext: ModelContext
    private let notificationManager = NotificationManager()
    
    init(modelContext: ModelContext) {
        self.modelContext = modelContext
        super.init()
        setupNotifications()
    }
    
    // MARK: - Public API
    
    func startFocus(duration: TimeInterval = 1800, category: String = "Focus") {
        // End any existing session
        if let current = currentSession {
            current.abandon(reason: "New session started")
        }
        
        // Create new session
        let session = FocusSession(
            startTime: Date(),
            duration: duration,
            category: category
        )
        
        self.currentSession = session
        self.isInFocus = true
        
        // Save to database
        modelContext.insert(session)
        try? modelContext.save()
        
        // Play start sound and haptic
        playStartTone()
        hapticFeedback(.light)
        
        // Schedule ambient reminder (first one in 5 min)
        scheduleAmbientReminder(at: 5 * 60)
        
        // Start timer
        startTimer()
    }
    
    func pauseFocus() {
        timer?.invalidate()
        timer = nil
    }
    
    func resumeFocus() {
        startTimer()
    }
    
    func endFocus(completed: Bool = true) {
        timer?.invalidate()
        timer = nil
        
        guard let session = currentSession else { return }
        
        if completed {
            session.complete()
        } else {
            session.abandon()
        }
        
        try? modelContext.save()
        
        // Notify user
        if completed {
            notificationManager.showCompletionNotification(session: session)
            playCompletionTone()
        } else {
            playExitTone()
        }
        
        hapticFeedback(.heavy)
        
        // Clear state
        self.isInFocus = false
        self.currentSession = nil
        self.timeRemaining = 0
    }
    
    // MARK: - Private
    
    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            self?.updateTimer()
        }
    }
    
    private func updateTimer() {
        guard let session = currentSession else { return }
        
        timeRemaining = session.timeRemaining
        progress = session.progress
        
        // Check if time's up
        if timeRemaining <= 0 {
            endFocus(completed: true)
        }
        
        // Notify at milestones (5 min, 1 min remaining)
        if Int(timeRemaining) == 300 {
            notificationManager.showAlert("5 minutes remaining")
        } else if Int(timeRemaining) == 60 {
            notificationManager.showAlert("1 minute remaining")
            hapticFeedback(.medium)
        }
    }
    
    private func scheduleAmbientReminder(at delaySeconds: Int) {
        DispatchQueue.main.asyncAfter(deadline: .now() + Double(delaySeconds)) { [weak self] in
            guard self?.isInFocus == true else { return }
            self?.notificationManager.showAmbientReminder()
            // Schedule next one
            self?.scheduleAmbientReminder(at: 10 * 60)  // Every 10 min after that
        }
    }
    
    private func setupNotifications() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
    }
    
    // MARK: - Audio/Haptic Feedback
    
    private func playStartTone() {
        // Play system sound
        #if !os(macOS)
        let soundID = SystemSoundID(1113)  // "Ping" sound
        AudioServicesPlaySystemSound(soundID)
        #endif
    }
    
    private func playCompletionTone() {
        #if !os(macOS)
        let soundID = SystemSoundID(1054)  // "Bells" sound
        AudioServicesPlaySystemSound(soundID)
        #endif
    }
    
    private func playExitTone() {
        #if !os(macOS)
        let soundID = SystemSoundID(1057)  // "Pop" sound
        AudioServicesPlaySystemSound(soundID)
        #endif
    }
    
    private func hapticFeedback(_ style: UIImpactFeedbackGenerator.FeedbackStyle) {
        #if !os(macOS)
        let generator = UIImpactFeedbackGenerator(style: style)
        generator.impactOccurred()
        #endif
    }
}
