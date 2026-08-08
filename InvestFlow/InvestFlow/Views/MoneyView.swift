import SwiftData
import SwiftUI

struct MoneyView: View {
    @Environment(\.modelContext) private var modelContext
    @StateObject private var viewModel = MoneyViewModel()
    @State private var showExpense = false
    @State private var showPlace = false
    @State private var amount = ""
    @State private var merchant = ""
    @State private var placeName = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    FlowCard {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("오늘 쓴 돈").font(.subheadline).foregroundStyle(.secondary)
                            Text(viewModel.todayTotal.krw)
                                .font(.system(size: 38, weight: .bold, design: .rounded))
                            Text("이번 달 \(viewModel.monthTotal.krw) · 오늘 \(viewModel.todayCount)건")
                                .font(.subheadline).foregroundStyle(.secondary)
                        }
                    }

                    FlowCard {
                        HStack(spacing: 14) {
                            Image(systemName: viewModel.isMonitoring ? "location.fill" : "location.slash.fill")
                                .font(.title2)
                                .foregroundStyle(viewModel.isMonitoring ? .green : .orange)
                            VStack(alignment: .leading, spacing: 3) {
                                Text(viewModel.isMonitoring ? "소비 감지 켜짐" : "위치 알림을 켜주세요").font(.headline)
                                Text("등록한 소비 장소에 도착하면 알려드려요")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Button("설정") { viewModel.requestPermissions() }
                        }
                    }

                    HStack(spacing: 12) {
                        quickButton("온라인 쇼핑", "bag.fill", .indigo) {
                            viewModel.detectOnlineShopping()
                        }
                        quickButton("직접 기록", "plus.circle.fill", .blue) {
                            merchant = ""; amount = ""; showExpense = true
                        }
                    }

                    FlowCard {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Text("소비 장소").font(.headline)
                                Spacer()
                                Button("현재 위치 추가") { showPlace = true }
                            }
                            if viewModel.places.isEmpty {
                                Text("마트, 쇼핑몰, 카페 등을 등록해 보세요.")
                                    .font(.subheadline).foregroundStyle(.secondary)
                            }
                            ForEach(viewModel.places) { place in
                                Label(place.name, systemImage: "mappin.circle.fill")
                                    .foregroundStyle(.primary)
                            }
                        }
                    }

                    FlowCard {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("최근 지출").font(.headline)
                            if viewModel.entries.isEmpty {
                                Text("아직 기록이 없어요.").foregroundStyle(.secondary)
                            }
                            ForEach(viewModel.entries.prefix(6)) { entry in
                                HStack {
                                    VStack(alignment: .leading) {
                                        Text(entry.title).font(.subheadline.weight(.medium))
                                        Text(entry.date, format: .dateTime.month().day().hour().minute())
                                            .font(.caption).foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    Text("-\(entry.amount.krw)").font(.subheadline.weight(.semibold))
                                }
                            }
                        }
                    }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Spend Flow")
            .onAppear { viewModel.configure(context: modelContext) }
            .alert("소비 활동이 감지됐어요", isPresented: $viewModel.showDetectionAlert) {
                Button("지금 기록") {
                    merchant = viewModel.detectedSource
                    amount = ""
                    showExpense = true
                }
                Button("나중에", role: .cancel) {}
            } message: {
                Text("\(viewModel.detectedSource)에서 결제했다면 잊기 전에 기록하세요.")
            }
            .sheet(isPresented: $showExpense) { expenseSheet }
            .sheet(isPresented: $showPlace) { placeSheet }
        }
    }

    private func quickButton(_ title: String, _ icon: String, _ color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 12) {
                Image(systemName: icon).font(.title2).foregroundStyle(color)
                Text(title).font(.headline).foregroundStyle(.primary)
                Text("탭해서 알림 · 기록").font(.caption).foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
            .background(.background)
            .clipShape(RoundedRectangle(cornerRadius: 14))
        }
        .buttonStyle(.plain)
    }

    private var expenseSheet: some View {
        NavigationStack {
            Form {
                TextField("금액", text: $amount).keyboardType(.numberPad)
                TextField("사용처", text: $merchant)
            }
            .navigationTitle("지출 기록")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("취소") { showExpense = false } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("저장") {
                        viewModel.addExpense(title: merchant.isEmpty ? "지출" : merchant, amount: parsedAmount)
                        showExpense = false
                    }
                    .disabled(parsedAmount <= 0)
                }
            }
        }
        .presentationDetents([.medium])
    }

    private var placeSheet: some View {
        NavigationStack {
            Form {
                TextField("장소 이름 (예: 동네 마트)", text: $placeName)
                Text("현재 위치 반경 150m에 진입하면 알림을 보냅니다.")
                    .font(.caption).foregroundStyle(.secondary)
            }
            .navigationTitle("소비 장소 등록")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("취소") { showPlace = false } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("등록") {
                        viewModel.addCurrentPlace(name: placeName.isEmpty ? "소비 장소" : placeName)
                        placeName = ""
                        showPlace = false
                    }
                }
            }
        }
        .presentationDetents([.medium])
    }

    private var parsedAmount: Double {
        Double(amount.filter(\.isNumber)) ?? 0
    }
}
