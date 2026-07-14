import Charts
import SwiftData
import SwiftUI

struct MoneyView: View {
    @Environment(\.modelContext) private var modelContext
    @StateObject private var viewModel = MoneyViewModel()
    @State private var customTitle = ""
    @State private var customAmount = 250.0
    @State private var customKind: CashFlowKind = .expense
    @State private var allocationSymbol = "VOO"
    @State private var allocationAmount = 250.0

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 12) {
                    FlowCard {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Investable this month")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            Text(viewModel.investableAmount.usd)
                                .font(.system(.largeTitle, design: .rounded, weight: .semibold))
                            HStack {
                                metric("Income", viewModel.monthlyIncome)
                                metric("Expenses", viewModel.monthlyExpenses)
                                metric("Allocated", viewModel.allocatedMonthly)
                            }
                        }
                    }

                    FlowCard {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Quick cash flow")
                                .font(.headline)
                            HStack {
                                Button("+ Paycheck") {
                                    viewModel.addQuickEntry(title: "Paycheck", amount: 2500, kind: .income)
                                }
                                .buttonStyle(.borderedProminent)

                                Button("- Bill") {
                                    viewModel.addQuickEntry(title: "Bill", amount: 120, kind: .expense)
                                }
                                .buttonStyle(.bordered)
                            }

                            TextField("Label", text: $customTitle)
                                .textFieldStyle(.roundedBorder)
                            HStack {
                                Picker("Kind", selection: $customKind) {
                                    ForEach(CashFlowKind.allCases) { kind in
                                        Text(kind.rawValue.capitalized).tag(kind)
                                    }
                                }
                                .pickerStyle(.segmented)

                                TextField("Amount", value: $customAmount, format: .currency(code: "USD"))
                                    .keyboardType(.decimalPad)
                                    .textFieldStyle(.roundedBorder)
                            }
                            Button("Add monthly entry") {
                                viewModel.addQuickEntry(title: customTitle.isEmpty ? customKind.rawValue.capitalized : customTitle, amount: customAmount, kind: customKind)
                                customTitle = ""
                            }
                            .buttonStyle(.borderedProminent)
                        }
                    }

                    FlowCard {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Recurring allocation")
                                .font(.headline)
                            HStack {
                                TextField("Symbol", text: $allocationSymbol)
                                    .textInputAutocapitalization(.characters)
                                    .textFieldStyle(.roundedBorder)
                                TextField("Monthly", value: $allocationAmount, format: .currency(code: "USD"))
                                    .keyboardType(.decimalPad)
                                    .textFieldStyle(.roundedBorder)
                            }
                            Button("Add to plan") {
                                viewModel.addAllocation(name: allocationSymbol.uppercased(), symbol: allocationSymbol, monthlyAmount: allocationAmount)
                            }
                            .buttonStyle(.borderedProminent)

                            ForEach(viewModel.allocations) { allocation in
                                HStack {
                                    VStack(alignment: .leading) {
                                        Text(allocation.symbol)
                                            .font(.headline)
                                        Text("Monthly recurring")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    Text(allocation.monthlyAmount.usd)
                                        .font(.headline)
                                }
                                .padding(.vertical, 4)
                            }
                        }
                    }

                    FlowCard {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Cash-flow mix")
                                .font(.headline)
                            Chart {
                                BarMark(x: .value("Type", "Income"), y: .value("Amount", viewModel.monthlyIncome))
                                BarMark(x: .value("Type", "Expenses"), y: .value("Amount", viewModel.monthlyExpenses))
                                BarMark(x: .value("Type", "Allocated"), y: .value("Amount", viewModel.allocatedMonthly))
                            }
                            .frame(height: 180)
                        }
                    }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Money")
            .onAppear {
                viewModel.configure(context: modelContext)
            }
        }
    }

    private func metric(_ title: String, _ amount: Double) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(amount.usd)
                .font(.subheadline.weight(.semibold))
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
