import Foundation
import UserNotifications

class NotificationManager {
    
    func showAlert(_ message: String) {
        let content = UNMutableNotificationContent()
        content.title = "Still Mode"
        content.body = message
        content.sound = .default
        content.badge = 1
        
        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
        )
        
        UNUserNotificationCenter.current().add(request)
    }
    
    func showAmbientReminder() {
        let content = UNMutableNotificationContent()
        content.title = "Still focusing?"
        content.body = "You're doing great! Keep going. 🌙"
        content.sound = .default
        content.badge = NSNumber(value: UIApplication.shared.applicationIconBadgeNumber + 1)
        
        // Add actions
        let continueAction = UNNotificationAction(
            identifier: "CONTINUE_FOCUS",
            title: "Keep Going",
            options: .foreground
        )
        let endAction = UNNotificationAction(
            identifier: "END_FOCUS",
            title: "Stop Focus",
            options: .destructive
        )
        
        let category = UNNotificationCategory(
            identifier: "FOCUS_REMINDER",
            actions: [continueAction, endAction],
            intentIdentifiers: [],
            options: []
        )
        
        UNUserNotificationCenter.current().setNotificationCategories([category])
        content.categoryIdentifier = "FOCUS_REMINDER"
        
        let request = UNNotificationRequest(
            identifier: "ambient-reminder",
            content: content,
            trigger: UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
        )
        
        UNUserNotificationCenter.current().add(request)
    }
    
    func showCompletionNotification(session: FocusSession) {
        let content = UNMutableNotificationContent()
        content.title = "🎉 Focus Session Complete!"
        content.body = "You focused for \(session.formattedDuration). Great work!"
        content.sound = .default
        content.badge = 0  // Clear badge
        
        let request = UNNotificationRequest(
            identifier: "completion",
            content: content,
            trigger: UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
        )
        
        UNUserNotificationCenter.current().add(request)
    }
}
