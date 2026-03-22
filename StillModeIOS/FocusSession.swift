import Foundation
import SwiftData

@Model
final class FocusSession {
    var id: UUID = UUID()
    var startTime: Date
    var endTime: Date?
    var duration: TimeInterval  // in seconds
    var category: String = "Focus"  // work, creative, health, etc.
    var notes: String = ""
    var completed: Bool = false
    var abandonedReason: String?  // why user stopped early
    
    init(
        startTime: Date = Date(),
        duration: TimeInterval = 1800,  // 30 min default
        category: String = "Focus"
    ) {
        self.startTime = startTime
        self.duration = duration
        self.category = category
    }
    
    // Mark session as completed
    func complete() {
        self.endTime = Date()
        self.completed = true
    }
    
    // Mark session as abandoned
    func abandon(reason: String = "User stopped") {
        self.endTime = Date()
        self.abandonedReason = reason
        self.completed = false
    }
    
    // Time remaining (in seconds)
    var timeRemaining: TimeInterval {
        let elapsed = Date().timeIntervalSince(startTime)
        return max(0, duration - elapsed)
    }
    
    // Progress (0-1)
    var progress: Double {
        let elapsed = Date().timeIntervalSince(startTime)
        return min(1.0, elapsed / duration)
    }
    
    // Is this session active?
    var isActive: Bool {
        endTime == nil && timeRemaining > 0
    }
    
    // Format duration as MM:SS
    var formattedTime: String {
        let totalSeconds = Int(timeRemaining)
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }
    
    // Format duration as human-readable
    var formattedDuration: String {
        let mins = Int(duration) / 60
        if mins < 60 {
            return "\(mins) min"
        } else {
            let hours = mins / 60
            let remainingMins = mins % 60
            if remainingMins == 0 {
                return "\(hours)h"
            } else {
                return "\(hours)h \(remainingMins)m"
            }
        }
    }
}

// Statistics
struct FocusStats {
    let totalSessions: Int
    let completedSessions: Int
    let totalTimeInFocus: TimeInterval
    let averageSessionLength: TimeInterval
    let currentStreak: Int  // consecutive days with focus
    let thisWeekTotal: TimeInterval
    let thisMonthTotal: TimeInterval
    
    var completionRate: Double {
        guard totalSessions > 0 else { return 0 }
        return Double(completedSessions) / Double(totalSessions)
    }
}
