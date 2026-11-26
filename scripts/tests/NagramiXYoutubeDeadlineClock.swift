private final class DeadlineClock {
    var jobs: [DispatchWorkItem] = []
    func asyncAfter(deadline: DispatchTime, execute item: DispatchWorkItem) { jobs.append(item) }
    func expire() {
        let batch = jobs
        jobs.removeAll()
        for job in batch where !job.isCancelled { job.perform() }
    }
}
private enum DispatchQueue { static let main = DeadlineClock() }
