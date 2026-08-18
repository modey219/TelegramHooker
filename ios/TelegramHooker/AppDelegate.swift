import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        let nav = UINavigationController(rootViewController: LoginViewController())
        nav.navigationBar.barStyle = .black
        nav.navigationBar.tintColor = UIColor(red: 0.3, green: 0.7, blue: 1, alpha: 1)
        nav.navigationBar.titleTextAttributes = [.foregroundColor: UIColor.white]

        window = UIWindow(frame: UIScreen.main.bounds)
        window?.rootViewController = nav
        window?.backgroundColor = UIColor(red: 0.06, green: 0.06, blue: 0.12, alpha: 1)
        window?.makeKeyAndVisible()
        return true
    }
}
