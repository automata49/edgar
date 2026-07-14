import Combine
import Foundation
import SwiftData

@MainActor
final class RoutineViewModel: ObservableObject {
    @Published var today: RoutineSession?

    private var context: ModelContext?

    func configure(context: ModelContext) {
        self.context = context
        loadToday()
    }

    func loadToday() {
        guard let context else { return }
        let start = Calendar.current.startOfDay(for: .now)
        let end = Calendar.current.date(byAdding: .day, value: 1, to: start) ?? .now
        let descriptor = FetchDescriptor<RoutineSession>(
            predicate: #Predicate { $0.date >= start && $0.date < end },
            sortBy: [SortDescriptor(\.date, order: .reverse)]
        )

        if let session = try? context.fetch(descriptor).first {
            today = session
        } else {
            let session = RoutineSession()
            context.insert(session)
            try? context.save()
            today = session
        }
    }

    func save() {
        try? context?.save()
        objectWillChange.send()
    }
}
