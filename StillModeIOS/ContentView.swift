import SwiftUI
import SwiftData

struct ContentView: View {
    @Environment(\.modelContext) private var modelContext
    @StateObject private var focusManager: FocusManager
    @State private var selectedDuration: TimeInterval = 1800  // 30 min
    @State private var showHistory = false
    @State private var showStats = false
    
    init(modelContext: ModelContext) {
        _focusManager = StateObject(wrappedValue: FocusManager(modelContext: modelContext))
    }
    
    var body: some View {
        ZStack {
            if focusManager.isInFocus {
                FocusView(focusManager: focusManager)
                    .transition(.opacity)
            } else {
                mainView
                    .transition(.opacity)
            }
        }
        .animation(.easeInOut, value: focusManager.isInFocus)
    }
    
    private var mainView: some View {
        VStack(spacing: 24) {
            // Header
            VStack(spacing: 8) {
                Text("🌙 Still Mode")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                Text("Focus on what matters")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.top, 32)
            
            Spacer()
            
            // Duration selector
            VStack(spacing: 16) {
                Text("Duration")
                    .font(.headline)
                
                HStack(spacing: 12) {
                    ForEach([15*60, 30*60, 45*60, 60*60], id: \.self) { duration in
                        DurationButton(
                            label: formatDuration(duration),
                            isSelected: selectedDuration == duration,
                            action: { selectedDuration = duration }
                        )
                    }
                }
                
                // Custom duration input
                HStack {
                    Text("Custom (minutes):")
                    TextField("", value: Binding(
                        get: { selectedDuration / 60 },
                        set: { selectedDuration = $0 * 60 }
                    ), format: .number)
                    .textFieldStyle(.roundedBorder)
                    .keyboardType(.numberPad)
                }
                .padding(.top, 8)
            }
            .padding(.horizontal)
            
            Spacer()
            
            // Start button
            Button(action: startFocus) {
                Text("Start Focus 🧘")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(Color.blue)
                    .cornerRadius(12)
            }
            .padding(.horizontal)
            
            // Navigation buttons
            HStack(spacing: 16) {
                Button(action: { showHistory = true }) {
                    Label("History", systemImage: "clock.fill")
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color.gray.opacity(0.2))
                        .cornerRadius(8)
                }
                
                Button(action: { showStats = true }) {
                    Label("Stats", systemImage: "chart.bar.fill")
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color.gray.opacity(0.2))
                        .cornerRadius(8)
                }
            }
            .padding(.horizontal)
            .padding(.bottom, 32)
        }
        .sheet(isPresented: $showHistory) {
            HistoryView()
        }
        .sheet(isPresented: $showStats) {
            StatsView()
        }
    }
    
    private func startFocus() {
        focusManager.startFocus(duration: selectedDuration)
    }
    
    private func formatDuration(_ seconds: TimeInterval) -> String {
        let mins = Int(seconds) / 60
        return "\(mins)m"
    }
}

struct DurationButton: View {
    let label: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(label)
                .font(.subheadline)
                .fontWeight(.semibold)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(isSelected ? Color.blue : Color.gray.opacity(0.2))
                .foregroundColor(isSelected ? .white : .primary)
                .cornerRadius(8)
        }
    }
}

struct HistoryView: View {
    @Query private var sessions: [FocusSession]
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            List {
                if sessions.isEmpty {
                    Text("No focus sessions yet. Start one to see your history!")
                        .foregroundColor(.secondary)
                } else {
                    ForEach(sessions) { session in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(session.category)
                                .font(.headline)
                            Text(session.startTime.formatted(date: .abbreviated, time: .shortened))
                                .font(.caption)
                                .foregroundColor(.secondary)
                            HStack {
                                Text(session.formattedDuration)
                                Spacer()
                                Text(session.completed ? "✓ Completed" : "Abandoned")
                                    .foregroundColor(session.completed ? .green : .orange)
                            }
                            .font(.subheadline)
                        }
                        .padding(.vertical, 4)
                    }
                }
            }
            .navigationTitle("Focus History")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }
}

struct StatsView: View {
    @Query private var sessions: [FocusSession]
    @Environment(\.dismiss) var dismiss
    
    var stats: FocusStats {
        let total = sessions.count
        let completed = sessions.filter { $0.completed }.count
        let totalTime = sessions.reduce(0) { $0 + $1.duration }
        let avg = total > 0 ? totalTime / Double(total) : 0
        
        return FocusStats(
            totalSessions: total,
            completedSessions: completed,
            totalTimeInFocus: totalTime,
            averageSessionLength: avg,
            currentStreak: calculateStreak(),
            thisWeekTotal: weekTotal(),
            thisMonthTotal: monthTotal()
        )
    }
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                ScrollView {
                    VStack(spacing: 16) {
                        StatCard(
                            title: "Total Sessions",
                            value: String(stats.totalSessions),
                            icon: "🎯"
                        )
                        
                        StatCard(
                            title: "Completion Rate",
                            value: String(format: "%.0f%%", stats.completionRate * 100),
                            icon: "✓"
                        )
                        
                        StatCard(
                            title: "Total Focus Time",
                            value: formatTotalTime(stats.totalTimeInFocus),
                            icon: "⏱"
                        )
                        
                        StatCard(
                            title: "This Week",
                            value: formatTotalTime(stats.thisWeekTotal),
                            icon: "📊"
                        )
                        
                        StatCard(
                            title: "Current Streak",
                            value: String(stats.currentStreak) + " days",
                            icon: "🔥"
                        )
                    }
                    .padding()
                }
            }
            .navigationTitle("Your Stats")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }
    
    private func calculateStreak() -> Int {
        // Simplified: count consecutive days with focus
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        var streak = 0
        var currentDate = today
        
        for session in sessions.sorted(by: { $0.startTime > $1.startTime }) {
            let sessionDate = calendar.startOfDay(for: session.startTime)
            if sessionDate == currentDate {
                streak += 1
                currentDate = calendar.date(byAdding: .day, value: -1, to: currentDate) ?? Date()
            } else if sessionDate < currentDate {
                break
            }
        }
        
        return streak
    }
    
    private func weekTotal() -> TimeInterval {
        let calendar = Calendar.current
        let weekAgo = calendar.date(byAdding: .day, value: -7, to: Date()) ?? Date()
        return sessions
            .filter { $0.startTime > weekAgo }
            .reduce(0) { $0 + $1.duration }
    }
    
    private func monthTotal() -> TimeInterval {
        let calendar = Calendar.current
        let monthAgo = calendar.date(byAdding: .month, value: -1, to: Date()) ?? Date()
        return sessions
            .filter { $0.startTime > monthAgo }
            .reduce(0) { $0 + $1.duration }
    }
    
    private func formatTotalTime(_ seconds: TimeInterval) -> String {
        let hours = Int(seconds) / 3600
        let mins = (Int(seconds) % 3600) / 60
        
        if hours == 0 {
            return "\(mins)m"
        } else if mins == 0 {
            return "\(hours)h"
        } else {
            return "\(hours)h \(mins)m"
        }
    }
}

struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    
    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Text(icon).font(.title)
                Text(title)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                Spacer()
            }
            Text(value)
                .font(.title2)
                .fontWeight(.bold)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding()
        .background(Color.gray.opacity(0.1))
        .cornerRadius(12)
    }
}

struct FocusView: View {
    @ObservedObject var focusManager: FocusManager
    @State private var showQuitDialog = false
    
    var body: some View {
        ZStack {
            // Full-screen black background
            Color.black.ignoresSafeArea()
            
            VStack(spacing: 20) {
                Spacer()
                
                // Large timer display
                VStack(spacing: 12) {
                    Text("Focus Mode Active")
                        .font(.headline)
                        .foregroundColor(.white.opacity(0.7))
                    
                    Text(focusManager.currentSession?.formattedTime ?? "00:00")
                        .font(.system(size: 80, weight: .thin, design: .monospaced))
                        .foregroundColor(.white)
                        .minimumScaleFactor(0.5)
                        .lineLimit(1)
                    
                    // Progress ring
                    Circle()
                        .trim(from: 0, to: focusManager.progress)
                        .stroke(Color.blue, lineWidth: 4)
                        .frame(width: 120, height: 120)
                        .rotationEffect(.degrees(-90))
                        .animation(.linear, value: focusManager.progress)
                }
                
                Spacer()
                
                // Category
                if let session = focusManager.currentSession {
                    Text(session.category)
                        .font(.subheadline)
                        .foregroundColor(.white.opacity(0.6))
                }
                
                Spacer()
                
                // Controls
                HStack(spacing: 16) {
                    Button(action: {
                        focusManager.pauseFocus()
                    }) {
                        Image(systemName: "pause.fill")
                            .font(.title2)
                            .foregroundColor(.white)
                            .frame(width: 50, height: 50)
                            .background(Color.white.opacity(0.2))
                            .cornerRadius(25)
                    }
                    
                    Spacer()
                    
                    Button(action: { showQuitDialog = true }) {
                        Text("Exit")
                            .font(.headline)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .background(Color.red.opacity(0.7))
                            .cornerRadius(8)
                    }
                }
                .padding()
                .padding(.bottom)
            }
            .padding()
        }
        .alert("Exit Focus Mode?", isPresented: $showQuitDialog) {
            Button("Cancel", role: .cancel) { }
            Button("Exit", role: .destructive) {
                focusManager.endFocus(completed: false)
            }
        }
    }
}
