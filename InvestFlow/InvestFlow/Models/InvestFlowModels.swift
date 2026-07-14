import Foundation
import SwiftData

enum CashFlowKind: String, CaseIterable, Codable, Identifiable {
    case income
    case expense

    var id: String { rawValue }
}

enum RoutinePeriod: String, CaseIterable, Codable, Identifiable {
    case morning
    case intraday
    case evening

    var id: String { rawValue }
    var title: String { rawValue.capitalized }
}

enum IdeaStatus: String, CaseIterable, Codable, Identifiable {
    case inbox = "Inbox"
    case watch = "Watch"
    case candidate = "Candidate"
    case rejected = "Rejected"
    case portfolio = "Portfolio"

    var id: String { rawValue }
}

enum AssetKind: String, CaseIterable, Codable, Identifiable {
    case stock = "Stock"
    case crypto = "Crypto"

    var id: String { rawValue }
}

@Model
final class CashFlowEntry {
    var id: UUID
    var title: String
    var amount: Double
    var kindRawValue: String
    var date: Date
    var isRecurring: Bool

    var kind: CashFlowKind {
        get { CashFlowKind(rawValue: kindRawValue) ?? .expense }
        set { kindRawValue = newValue.rawValue }
    }

    init(title: String, amount: Double, kind: CashFlowKind, date: Date = .now, isRecurring: Bool = false) {
        self.id = UUID()
        self.title = title
        self.amount = amount
        self.kindRawValue = kind.rawValue
        self.date = date
        self.isRecurring = isRecurring
    }
}

@Model
final class InvestmentAllocation {
    var id: UUID
    var name: String
    var symbol: String
    var monthlyAmount: Double
    var targetPercent: Double
    var isActive: Bool
    var createdAt: Date

    init(name: String, symbol: String, monthlyAmount: Double, targetPercent: Double, isActive: Bool = true) {
        self.id = UUID()
        self.name = name
        self.symbol = symbol
        self.monthlyAmount = monthlyAmount
        self.targetPercent = targetPercent
        self.isActive = isActive
        self.createdAt = .now
    }
}

@Model
final class RoutineSession {
    var id: UUID
    var date: Date
    var morningMarketRead: Bool
    var morningCashCheck: Bool
    var morningWatchlistReview: Bool
    var intradayPriceAlerts: Bool
    var intradayContrarianCheck: Bool
    var intradayNoFomoCheck: Bool
    var eveningJournal: Bool
    var eveningAllocationReview: Bool
    var eveningTomorrowPlan: Bool
    var contrarianQuestionOne: String
    var contrarianQuestionTwo: String
    var contrarianQuestionThree: String
    var dailyReviewNotes: String

    var completedCount: Int {
        [
            morningMarketRead,
            morningCashCheck,
            morningWatchlistReview,
            intradayPriceAlerts,
            intradayContrarianCheck,
            intradayNoFomoCheck,
            eveningJournal,
            eveningAllocationReview,
            eveningTomorrowPlan
        ].filter { $0 }.count
    }

    var completionRatio: Double {
        Double(completedCount) / 9.0
    }

    init(date: Date = .now) {
        self.id = UUID()
        self.date = date
        self.morningMarketRead = false
        self.morningCashCheck = false
        self.morningWatchlistReview = false
        self.intradayPriceAlerts = false
        self.intradayContrarianCheck = false
        self.intradayNoFomoCheck = false
        self.eveningJournal = false
        self.eveningAllocationReview = false
        self.eveningTomorrowPlan = false
        self.contrarianQuestionOne = ""
        self.contrarianQuestionTwo = ""
        self.contrarianQuestionThree = ""
        self.dailyReviewNotes = ""
    }
}

@Model
final class PostItIdea {
    var id: UUID
    var title: String
    var symbol: String
    var assetKindRawValue: String
    var statusRawValue: String
    var noteText: String
    var voiceTranscript: String
    var aiSummary: String
    var proposedAllocation: Double
    var createdAt: Date
    var approvedAt: Date?

    var assetKind: AssetKind {
        get { AssetKind(rawValue: assetKindRawValue) ?? .stock }
        set { assetKindRawValue = newValue.rawValue }
    }

    var status: IdeaStatus {
        get { IdeaStatus(rawValue: statusRawValue) ?? .inbox }
        set { statusRawValue = newValue.rawValue }
    }

    init(title: String, symbol: String, assetKind: AssetKind, noteText: String, voiceTranscript: String = "") {
        self.id = UUID()
        self.title = title
        self.symbol = symbol.uppercased()
        self.assetKindRawValue = assetKind.rawValue
        self.statusRawValue = IdeaStatus.inbox.rawValue
        self.noteText = noteText
        self.voiceTranscript = voiceTranscript
        self.aiSummary = ""
        self.proposedAllocation = 0
        self.createdAt = .now
        self.approvedAt = nil
    }
}

@Model
final class InvestmentPlanProposal {
    var id: UUID
    var ideaID: UUID
    var symbol: String
    var monthlyAmount: Double
    var rationale: String
    var isApproved: Bool
    var createdAt: Date

    init(ideaID: UUID, symbol: String, monthlyAmount: Double, rationale: String, isApproved: Bool = false) {
        self.id = UUID()
        self.ideaID = ideaID
        self.symbol = symbol
        self.monthlyAmount = monthlyAmount
        self.rationale = rationale
        self.isApproved = isApproved
        self.createdAt = .now
    }
}
