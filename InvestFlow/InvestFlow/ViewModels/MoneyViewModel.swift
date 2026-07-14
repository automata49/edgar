import Combine
import Foundation
import SwiftData

@MainActor
final class MoneyViewModel: ObservableObject {
    @Published private(set) var entries: [CashFlowEntry] = []
    @Published private(set) var allocations: [InvestmentAllocation] = []

    private var context: ModelContext?

    var monthlyIncome: Double {
        entries.filter { $0.kind == .income }.reduce(0) { $0 + $1.amount }
    }

    var monthlyExpenses: Double {
        entries.filter { $0.kind == .expense }.reduce(0) { $0 + $1.amount }
    }

    var allocatedMonthly: Double {
        allocations.filter(\.isActive).reduce(0) { $0 + $1.monthlyAmount }
    }

    var investableAmount: Double {
        monthlyIncome - monthlyExpenses - allocatedMonthly
    }

    func configure(context: ModelContext) {
        self.context = context
        reload()
        seedIfNeeded()
    }

    func addQuickEntry(title: String, amount: Double, kind: CashFlowKind) {
        guard let context else { return }
        let entry = CashFlowEntry(title: title, amount: amount, kind: kind, isRecurring: true)
        context.insert(entry)
        saveAndReload()
    }

    func addAllocation(name: String, symbol: String, monthlyAmount: Double) {
        guard let context else { return }
        let safeAmount = max(0, monthlyAmount)
        let total = max(monthlyIncome - monthlyExpenses, 1)
        let allocation = InvestmentAllocation(
            name: name,
            symbol: symbol.uppercased(),
            monthlyAmount: safeAmount,
            targetPercent: min(100, (safeAmount / total) * 100)
        )
        context.insert(allocation)
        saveAndReload()
    }

    func deleteEntry(_ entry: CashFlowEntry) {
        context?.delete(entry)
        saveAndReload()
    }

    func reload() {
        guard let context else { return }
        let entryDescriptor = FetchDescriptor<CashFlowEntry>(sortBy: [SortDescriptor(\.date, order: .reverse)])
        let allocationDescriptor = FetchDescriptor<InvestmentAllocation>(sortBy: [SortDescriptor(\.createdAt, order: .reverse)])
        entries = (try? context.fetch(entryDescriptor)) ?? []
        allocations = (try? context.fetch(allocationDescriptor)) ?? []
    }

    private func seedIfNeeded() {
        guard entries.isEmpty, allocations.isEmpty else { return }
        addQuickEntry(title: "Salary", amount: 6200, kind: .income)
        addQuickEntry(title: "Rent", amount: 2100, kind: .expense)
        addQuickEntry(title: "Core bills", amount: 950, kind: .expense)
        addAllocation(name: "Core ETF", symbol: "VOO", monthlyAmount: 900)
    }

    private func saveAndReload() {
        try? context?.save()
        reload()
    }
}
