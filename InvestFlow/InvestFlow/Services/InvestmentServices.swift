import Foundation

struct MarketQuote: Identifiable, Hashable {
    let id = UUID()
    let symbol: String
    let name: String
    let price: Double
    let dailyChangePercent: Double
}

struct AllocationProposal {
    let monthlyAmount: Double
    let rationale: String
}

protocol MarketDataService {
    func quote(for symbol: String) async throws -> MarketQuote
    func watchlistQuotes() async throws -> [MarketQuote]
}

protocol AIInvestmentService {
    func summarize(idea: PostItIdea, marketQuote: MarketQuote?) async throws -> String
    func proposeAllocation(idea: PostItIdea, investableAmount: Double) async throws -> AllocationProposal
}

protocol VoiceNoteService {
    func transcribeLatestNote() async throws -> String
}

struct MockMarketDataService: MarketDataService {
    private let quotes: [String: MarketQuote] = [
        "AAPL": MarketQuote(symbol: "AAPL", name: "Apple", price: 214.35, dailyChangePercent: -0.8),
        "NVDA": MarketQuote(symbol: "NVDA", name: "NVIDIA", price: 148.20, dailyChangePercent: 1.4),
        "BTC": MarketQuote(symbol: "BTC", name: "Bitcoin", price: 68250, dailyChangePercent: -2.1),
        "ETH": MarketQuote(symbol: "ETH", name: "Ethereum", price: 3520, dailyChangePercent: 0.7),
        "VOO": MarketQuote(symbol: "VOO", name: "Vanguard S&P 500 ETF", price: 521.12, dailyChangePercent: 0.3)
    ]

    func quote(for symbol: String) async throws -> MarketQuote {
        let normalized = symbol.uppercased()
        if let quote = quotes[normalized] {
            return quote
        }

        return MarketQuote(symbol: normalized, name: normalized, price: 100, dailyChangePercent: 0)
    }

    func watchlistQuotes() async throws -> [MarketQuote] {
        Array(quotes.values).sorted { $0.symbol < $1.symbol }
    }
}

struct MockAIInvestmentService: AIInvestmentService {
    func summarize(idea: PostItIdea, marketQuote: MarketQuote?) async throws -> String {
        let quoteText: String
        if let marketQuote {
            quoteText = "\(marketQuote.symbol) is mocked at \(marketQuote.price.formatted(.currency(code: "USD"))) with a \(marketQuote.dailyChangePercent.formatted(.number.precision(.fractionLength(1))))% day move."
        } else {
            quoteText = "No market quote is available yet."
        }

        return "Thesis: \(idea.noteText). \(quoteText) Check valuation, catalyst durability, and downside before moving past Candidate."
    }

    func proposeAllocation(idea: PostItIdea, investableAmount: Double) async throws -> AllocationProposal {
        let riskWeight = idea.assetKind == .crypto ? 0.08 : 0.12
        let amount = max(0, (investableAmount * riskWeight).rounded())
        let rationale = "Mock proposal: start \(idea.symbol) at a small recurring weight so the idea earns its way into the plan after review."
        return AllocationProposal(monthlyAmount: amount, rationale: rationale)
    }
}

struct MockVoiceNoteService: VoiceNoteService {
    func transcribeLatestNote() async throws -> String {
        "Voice note placeholder: investigate entry after a pullback, confirm thesis, and avoid chasing green candles."
    }
}
