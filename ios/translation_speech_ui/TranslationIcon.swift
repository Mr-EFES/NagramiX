import UIKit

// Consistent lightweight badges drawn locally; no remote icon fetches.
func nagramiXServiceIcon(_ title: String) -> UIImage? {
    let normalized = title.lowercased()
    let symbol: String
    let color: UIColor
    switch normalized {
    case "apple": symbol = "apple.logo"; color = .systemGray
    case "google": symbol = "G"; color = .systemBlue
    case "яндекс": symbol = "Я"; color = .systemRed
    case "telegram", "telegram premium": symbol = "paperplane.fill"; color = .systemBlue
    case "gemini": symbol = "sparkles"; color = .systemIndigo
    case "chatgpt": symbol = "GPT"; color = .systemTeal
    case "deepseek": symbol = "D"; color = .systemBlue
    case "grok": symbol = "X"; color = .darkGray
    case "cloudflare": symbol = "cloud.fill"; color = .systemOrange
    case "whisper", "vosk": symbol = "waveform"; color = .systemTeal
    default: symbol = "gearshape.fill"; color = .systemGray
    }
    return UIGraphicsImageRenderer(size: CGSize(width: 28, height: 28)).image { ctx in
        color.setFill(); UIBezierPath(roundedRect: CGRect(x: 0, y: 0, width: 28, height: 28), cornerRadius: 8).fill()
        if let image = UIImage(systemName: symbol)?.withTintColor(.white, renderingMode: .alwaysOriginal) {
            image.draw(in: CGRect(x: 5, y: 5, width: 18, height: 18))
        } else {
            let font = UIFont.systemFont(ofSize: symbol.count > 1 ? 9 : 16, weight: .bold)
            let attr: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: UIColor.white]
            let size = (symbol as NSString).size(withAttributes: attr)
            (symbol as NSString).draw(at: CGPoint(x: (28-size.width)/2, y: (28-size.height)/2), withAttributes: attr)
        }
        _ = ctx
    }
}
