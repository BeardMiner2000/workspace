import Foundation
import Security

class iOSLicenseManager: ObservableObject {
    
    static let shared = iOSLicenseManager()
    
    @Published var isPremium: Bool = false
    @Published var licenseKey: String?
    
    private let keychainService = "com.jl.StillMode.iOS"
    private let licenseKeyAttribute = "LicenseKey"
    
    init() {
        loadLicense()
    }
    
    // MARK: - License Management
    
    func activateLicense(key: String) -> Bool {
        guard isValidFormat(key) else { return false }
        return storeLicense(key)
    }
    
    func deactivateLicense() -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: licenseKeyAttribute
        ]
        
        let status = SecItemDelete(query as CFDictionary)
        if status == errSecSuccess {
            DispatchQueue.main.async {
                self.licenseKey = nil
                self.isPremium = false
            }
            return true
        }
        return false
    }
    
    // MARK: - Private
    
    private func loadLicense() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: licenseKeyAttribute,
            kSecReturnData as String: true
        ]
        
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        
        guard status == errSecSuccess,
              let data = result as? Data,
              let key = String(data: data, encoding: .utf8) else {
            return
        }
        
        DispatchQueue.main.async {
            self.licenseKey = key
            self.isPremium = true
        }
    }
    
    private func storeLicense(_ key: String) -> Bool {
        guard let data = key.data(using: .utf8) else { return false }
        
        // Delete existing
        let deleteQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: licenseKeyAttribute
        ]
        SecItemDelete(deleteQuery as CFDictionary)
        
        // Add new
        let addQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: licenseKeyAttribute,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]
        
        let status = SecItemAdd(addQuery as CFDictionary, nil)
        
        if status == errSecSuccess {
            DispatchQueue.main.async {
                self.licenseKey = key
                self.isPremium = true
            }
            return true
        }
        
        return false
    }
    
    private func isValidFormat(_ key: String) -> Bool {
        let pattern = "^STILLMODE-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        guard let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) else {
            return false
        }
        let range = NSRange(key.startIndex..., in: key)
        return regex.firstMatch(in: key, options: [], range: range) != nil
    }
}

// MARK: - In-App Purchase Stub (for App Store)

class PremiumManager: NSObject, ObservableObject {
    
    @Published var isPremiumAvailable = false
    @Published var isLoading = false
    
    static let shared = PremiumManager()
    
    // TODO: Implement StoreKit 2 for actual in-app purchases
    // For now, license key activation is primary method
    
    func purchasePremium() {
        // Stub for future StoreKit 2 implementation
        isLoading = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            self.isLoading = false
            // Show license entry dialog
        }
    }
    
    func restorePurchases() {
        // TODO: Call StoreKit 2 to restore
    }
}
