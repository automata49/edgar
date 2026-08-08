import SwiftUI

struct FlowCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.background)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(.quaternary, lineWidth: 1)
            )
    }
}

extension Double {
    var usd: String {
        formatted(.currency(code: "USD").precision(.fractionLength(0)))
    }

    var krw: String {
        formatted(.currency(code: "KRW").precision(.fractionLength(0)))
    }
}
