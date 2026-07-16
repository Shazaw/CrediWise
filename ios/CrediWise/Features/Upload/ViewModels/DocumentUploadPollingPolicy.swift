struct DocumentUploadPollingPolicy: Equatable, Sendable {
    let initialDelaySeconds: UInt64
    let maximumDelaySeconds: UInt64
    let timeoutSeconds: UInt64

    init(
        initialDelaySeconds: UInt64 = 1,
        maximumDelaySeconds: UInt64 = 8,
        timeoutSeconds: UInt64 = 90
    ) {
        self.initialDelaySeconds = initialDelaySeconds
        self.maximumDelaySeconds = maximumDelaySeconds
        self.timeoutSeconds = timeoutSeconds
    }

    func delaySeconds(forAttempt attempt: Int) -> UInt64 {
        var delay = min(initialDelaySeconds, maximumDelaySeconds)
        guard attempt > 0, delay > 0 else {
            return delay
        }

        for _ in 0..<attempt {
            if delay >= maximumDelaySeconds || delay > maximumDelaySeconds / 2 {
                return maximumDelaySeconds
            }
            delay *= 2
        }
        return min(delay, maximumDelaySeconds)
    }
}
