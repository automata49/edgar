import SwiftData
import SwiftUI

struct RoutineView: View {
    @Environment(\.modelContext) private var modelContext
    @StateObject private var viewModel = RoutineViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                if let session = viewModel.today {
                    VStack(spacing: 12) {
                        FlowCard {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("Today")
                                    .font(.headline)
                                ProgressView(value: session.completionRatio)
                                Text("\(session.completedCount) of 9 complete")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        routineCard("Morning", items: [
                            ("Read market tone", Binding(get: { session.morningMarketRead }, set: { session.morningMarketRead = $0; viewModel.save() })),
                            ("Check cash available", Binding(get: { session.morningCashCheck }, set: { session.morningCashCheck = $0; viewModel.save() })),
                            ("Review watchlist", Binding(get: { session.morningWatchlistReview }, set: { session.morningWatchlistReview = $0; viewModel.save() }))
                        ])

                        routineCard("Intraday", items: [
                            ("Check alerts only", Binding(get: { session.intradayPriceAlerts }, set: { session.intradayPriceAlerts = $0; viewModel.save() })),
                            ("Answer contrarian prompts", Binding(get: { session.intradayContrarianCheck }, set: { session.intradayContrarianCheck = $0; viewModel.save() })),
                            ("No-FOMO confirmation", Binding(get: { session.intradayNoFomoCheck }, set: { session.intradayNoFomoCheck = $0; viewModel.save() }))
                        ])

                        FlowCard {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("Pre-trade contrarian questions")
                                    .font(.headline)
                                TextField("What would make this thesis wrong?", text: Binding(get: { session.contrarianQuestionOne }, set: { session.contrarianQuestionOne = $0; viewModel.save() }), axis: .vertical)
                                    .textFieldStyle(.roundedBorder)
                                TextField("Who is on the other side of this trade?", text: Binding(get: { session.contrarianQuestionTwo }, set: { session.contrarianQuestionTwo = $0; viewModel.save() }), axis: .vertical)
                                    .textFieldStyle(.roundedBorder)
                                TextField("What price would make me wait?", text: Binding(get: { session.contrarianQuestionThree }, set: { session.contrarianQuestionThree = $0; viewModel.save() }), axis: .vertical)
                                    .textFieldStyle(.roundedBorder)
                            }
                        }

                        routineCard("Evening", items: [
                            ("Write review", Binding(get: { session.eveningJournal }, set: { session.eveningJournal = $0; viewModel.save() })),
                            ("Review allocation drift", Binding(get: { session.eveningAllocationReview }, set: { session.eveningAllocationReview = $0; viewModel.save() })),
                            ("Set tomorrow plan", Binding(get: { session.eveningTomorrowPlan }, set: { session.eveningTomorrowPlan = $0; viewModel.save() }))
                        ])

                        FlowCard {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("Daily review notes")
                                    .font(.headline)
                                TextField("What did I learn today?", text: Binding(get: { session.dailyReviewNotes }, set: { session.dailyReviewNotes = $0; viewModel.save() }), axis: .vertical)
                                    .lineLimit(4...8)
                                    .textFieldStyle(.roundedBorder)
                            }
                        }
                    }
                    .padding()
                }
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Routine")
            .onAppear {
                viewModel.configure(context: modelContext)
            }
        }
    }

    private func routineCard(_ title: String, items: [(String, Binding<Bool>)]) -> some View {
        FlowCard {
            VStack(alignment: .leading, spacing: 8) {
                Text(title)
                    .font(.headline)
                ForEach(items, id: \.0) { item in
                    Toggle(item.0, isOn: item.1)
                }
            }
        }
    }
}
