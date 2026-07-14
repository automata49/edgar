import SwiftData
import SwiftUI

@main
struct InvestFlowApp: App {
    var body: some Scene {
        WindowGroup {
            RootTabView()
        }
        .modelContainer(for: [
            CashFlowEntry.self,
            InvestmentAllocation.self,
            RoutineSession.self,
            PostItIdea.self,
            InvestmentPlanProposal.self
        ])
    }
}
