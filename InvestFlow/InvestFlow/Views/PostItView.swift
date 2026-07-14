import SwiftData
import SwiftUI

struct PostItView: View {
    @Environment(\.modelContext) private var modelContext
    @StateObject private var viewModel = PostItViewModel()
    @State private var title = ""
    @State private var symbol = ""
    @State private var note = ""
    @State private var assetKind: AssetKind = .stock
    @State private var investableAmount = 1000.0

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 12) {
                    FlowCard {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Capture")
                                .font(.headline)
                            TextField("Idea title", text: $title)
                                .textFieldStyle(.roundedBorder)
                            HStack {
                                TextField("Symbol", text: $symbol)
                                    .textInputAutocapitalization(.characters)
                                    .textFieldStyle(.roundedBorder)
                                Picker("Asset", selection: $assetKind) {
                                    ForEach(AssetKind.allCases) { kind in
                                        Text(kind.rawValue).tag(kind)
                                    }
                                }
                                .pickerStyle(.segmented)
                            }
                            TextField("Text note", text: $note, axis: .vertical)
                                .lineLimit(3...6)
                                .textFieldStyle(.roundedBorder)

                            HStack {
                                Button("Save text") {
                                    viewModel.addIdea(title: title, symbol: symbol, assetKind: assetKind, note: note)
                                    clearDraft()
                                }
                                .buttonStyle(.borderedProminent)

                                Button("Save voice") {
                                    viewModel.addVoiceIdea(title: title.isEmpty ? "Voice idea" : title, symbol: symbol, assetKind: assetKind)
                                    clearDraft()
                                }
                                .buttonStyle(.bordered)
                            }
                        }
                    }

                    FlowCard {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Mock market data")
                                .font(.headline)
                            ForEach(viewModel.quotes) { quote in
                                HStack {
                                    Text(quote.symbol)
                                        .font(.subheadline.weight(.semibold))
                                    Text(quote.name)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    Spacer()
                                    Text(quote.price.formatted(.currency(code: "USD")))
                                    Text("\(quote.dailyChangePercent, specifier: "%.1f")%")
                                        .foregroundStyle(quote.dailyChangePercent >= 0 ? .green : .red)
                                }
                            }
                        }
                    }

                    Picker("Status", selection: $viewModel.selectedStatus) {
                        ForEach(IdeaStatus.allCases) { status in
                            Text(status.rawValue).tag(status)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)

                    ForEach(viewModel.filteredIdeas) { idea in
                        ideaCard(idea)
                    }
                }
                .padding(.vertical)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Post-it")
            .onAppear {
                viewModel.configure(context: modelContext)
            }
        }
    }

    private func ideaCard(_ idea: PostItIdea) -> some View {
        FlowCard {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(idea.title)
                            .font(.headline)
                        Text("\(idea.assetKind.rawValue) · \(idea.symbol)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Menu(idea.status.rawValue) {
                        ForEach(IdeaStatus.allCases) { status in
                            Button(status.rawValue) {
                                viewModel.move(idea, to: status)
                            }
                        }
                    }
                }

                Text(idea.noteText)
                    .font(.subheadline)

                if !idea.aiSummary.isEmpty {
                    Text(idea.aiSummary)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                if idea.proposedAllocation > 0 {
                    HStack {
                        Text("Proposed: \(idea.proposedAllocation.usd)/mo")
                            .font(.subheadline.weight(.semibold))
                        Spacer()
                        Button("Approve") {
                            viewModel.approveProposal(for: idea)
                        }
                        .buttonStyle(.borderedProminent)
                    }
                }

                HStack {
                    TextField("Investable", value: $investableAmount, format: .currency(code: "USD"))
                        .keyboardType(.decimalPad)
                        .textFieldStyle(.roundedBorder)
                    Button("AI summary") {
                        viewModel.generateSummary(for: idea, investableAmount: investableAmount)
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
        .padding(.horizontal)
    }

    private func clearDraft() {
        title = ""
        symbol = ""
        note = ""
    }
}
