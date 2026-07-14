import Combine
import Foundation
import SwiftData

@MainActor
final class PostItViewModel: ObservableObject {
    @Published private(set) var ideas: [PostItIdea] = []
    @Published private(set) var quotes: [MarketQuote] = []
    @Published var selectedStatus: IdeaStatus = .inbox

    private var context: ModelContext?
    private let marketData: MarketDataService
    private let aiService: AIInvestmentService
    private let voiceService: VoiceNoteService

    init(
        marketData: MarketDataService = MockMarketDataService(),
        aiService: AIInvestmentService = MockAIInvestmentService(),
        voiceService: VoiceNoteService = MockVoiceNoteService()
    ) {
        self.marketData = marketData
        self.aiService = aiService
        self.voiceService = voiceService
    }

    var filteredIdeas: [PostItIdea] {
        ideas.filter { $0.status == selectedStatus }
    }

    func configure(context: ModelContext) {
        self.context = context
        reload()
        Task { await loadQuotes() }
    }

    func addIdea(title: String, symbol: String, assetKind: AssetKind, note: String) {
        guard let context, !title.isEmpty, !symbol.isEmpty else { return }
        context.insert(PostItIdea(title: title, symbol: symbol, assetKind: assetKind, noteText: note))
        saveAndReload()
    }

    func addVoiceIdea(title: String, symbol: String, assetKind: AssetKind) {
        Task {
            let transcript = (try? await voiceService.transcribeLatestNote()) ?? ""
            guard let context else { return }
            context.insert(PostItIdea(title: title, symbol: symbol, assetKind: assetKind, noteText: transcript, voiceTranscript: transcript))
            saveAndReload()
        }
    }

    func move(_ idea: PostItIdea, to status: IdeaStatus) {
        idea.status = status
        saveAndReload()
    }

    func generateSummary(for idea: PostItIdea, investableAmount: Double) {
        Task {
            let quote = try? await marketData.quote(for: idea.symbol)
            idea.aiSummary = (try? await aiService.summarize(idea: idea, marketQuote: quote)) ?? "Summary unavailable."
            let proposal = try? await aiService.proposeAllocation(idea: idea, investableAmount: investableAmount)
            idea.proposedAllocation = proposal?.monthlyAmount ?? 0
            if let proposal, let context {
                context.insert(InvestmentPlanProposal(ideaID: idea.id, symbol: idea.symbol, monthlyAmount: proposal.monthlyAmount, rationale: proposal.rationale))
            }
            saveAndReload()
        }
    }

    func approveProposal(for idea: PostItIdea) {
        guard let context, idea.proposedAllocation > 0 else { return }
        idea.status = .portfolio
        idea.approvedAt = .now
        context.insert(InvestmentAllocation(name: idea.title, symbol: idea.symbol, monthlyAmount: idea.proposedAllocation, targetPercent: 0))
        saveAndReload()
    }

    func reload() {
        guard let context else { return }
        let descriptor = FetchDescriptor<PostItIdea>(sortBy: [SortDescriptor(\.createdAt, order: .reverse)])
        ideas = (try? context.fetch(descriptor)) ?? []
    }

    private func loadQuotes() async {
        quotes = (try? await marketData.watchlistQuotes()) ?? []
    }

    private func saveAndReload() {
        try? context?.save()
        reload()
    }
}
