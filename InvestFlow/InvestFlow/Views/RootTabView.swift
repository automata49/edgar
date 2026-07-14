import SwiftUI

struct RootTabView: View {
    var body: some View {
        TabView {
            MoneyView()
                .tabItem {
                    Label("Money", systemImage: "dollarsign.circle")
                }

            RoutineView()
                .tabItem {
                    Label("Routine", systemImage: "checklist")
                }

            PostItView()
                .tabItem {
                    Label("Post-it", systemImage: "note.text")
                }
        }
    }
}
