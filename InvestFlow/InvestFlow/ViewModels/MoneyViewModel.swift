import Combine
import CoreLocation
import Foundation
import SwiftData
import UserNotifications

@MainActor
final class MoneyViewModel: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published private(set) var entries: [CashFlowEntry] = []
    @Published private(set) var places: [SpendingPlace] = []
    @Published private(set) var isMonitoring = false
    @Published var showDetectionAlert = false
    @Published var detectedSource = "온라인 쇼핑"

    private let locationManager = CLLocationManager()
    private var context: ModelContext?
    private var pendingPlaceName: String?

    override init() {
        super.init()
        locationManager.delegate = self
    }

    var todayTotal: Double {
        entries.filter { Calendar.current.isDateInToday($0.date) }.reduce(0) { $0 + $1.amount }
    }

    var todayCount: Int {
        entries.filter { Calendar.current.isDateInToday($0.date) }.count
    }

    var monthTotal: Double {
        entries.filter { Calendar.current.isDate($0.date, equalTo: .now, toGranularity: .month) }
            .reduce(0) { $0 + $1.amount }
    }

    func configure(context: ModelContext) {
        self.context = context
        reload()
        isMonitoring = locationManager.authorizationStatus == .authorizedAlways
        requestNotificationPermission()
        places.forEach(monitor)
    }

    func requestPermissions() {
        requestNotificationPermission()
        locationManager.requestAlwaysAuthorization()
    }

    func addExpense(title: String, amount: Double) {
        guard let context, amount > 0 else { return }
        context.insert(CashFlowEntry(title: title, amount: amount, kind: .expense))
        saveAndReload()
    }

    func addCurrentPlace(name: String) {
        pendingPlaceName = name
        switch locationManager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse:
            locationManager.requestLocation()
        case .notDetermined:
            locationManager.requestAlwaysAuthorization()
        default:
            requestPermissions()
        }
    }

    func detectOnlineShopping() {
        detectedSource = "온라인 쇼핑"
        showDetectionAlert = true
        sendNotification(title: "온라인 쇼핑 중이신가요?", body: "결제했다면 지금 지출을 기록해 보세요.")
    }

    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        Task { @MainActor in
            isMonitoring = manager.authorizationStatus == .authorizedAlways
            if manager.authorizationStatus == .authorizedWhenInUse {
                manager.requestAlwaysAuthorization()
            }
            if pendingPlaceName != nil,
               manager.authorizationStatus == .authorizedAlways || manager.authorizationStatus == .authorizedWhenInUse {
                manager.requestLocation()
            }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        Task { @MainActor in savePendingPlace(at: location.coordinate) }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        Task { @MainActor in pendingPlaceName = nil }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didEnterRegion region: CLRegion) {
        Task { @MainActor in
            let name = places.first { $0.id.uuidString == region.identifier }?.name ?? "소비 장소"
            detectedSource = name
            showDetectionAlert = true
            sendNotification(title: "\(name)에 도착했어요", body: "소비했다면 지출 기록을 남겨주세요.")
        }
    }

    private func savePendingPlace(at coordinate: CLLocationCoordinate2D) {
        guard let context, let name = pendingPlaceName else { return }
        let place = SpendingPlace(name: name, latitude: coordinate.latitude, longitude: coordinate.longitude)
        context.insert(place)
        pendingPlaceName = nil
        saveAndReload()
        monitor(place)
    }

    private func monitor(_ place: SpendingPlace) {
        guard CLLocationManager.isMonitoringAvailable(for: CLCircularRegion.self) else { return }
        let center = CLLocationCoordinate2D(latitude: place.latitude, longitude: place.longitude)
        let region = CLCircularRegion(center: center, radius: place.radius, identifier: place.id.uuidString)
        region.notifyOnEntry = true
        region.notifyOnExit = false
        locationManager.startMonitoring(for: region)
    }

    private func requestNotificationPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { _, _ in }
    }

    private func sendNotification(title: String, body: String) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        UNUserNotificationCenter.current().add(
            UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        )
    }

    private func reload() {
        guard let context else { return }
        entries = (try? context.fetch(
            FetchDescriptor<CashFlowEntry>(sortBy: [SortDescriptor(\.date, order: .reverse)])
        )) ?? []
        places = (try? context.fetch(
            FetchDescriptor<SpendingPlace>(sortBy: [SortDescriptor(\.createdAt, order: .reverse)])
        )) ?? []
    }

    private func saveAndReload() {
        try? context?.save()
        reload()
    }
}
