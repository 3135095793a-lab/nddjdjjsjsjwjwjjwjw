package com.agentfusion.core;

/** Adapter primitive only: never infers cleanup from result or cancellation.
 * The adapter must verify engine/child-worker quiescence before confirming cleanup.
 */
public final class ExecutionCompletionGate {
    public enum Outcome { SUCCEEDED, FAILED, CANCELLED }
    private Outcome outcome;
    private boolean cancelRequested, cleanupConfirmed, quarantined;

    public synchronized void requestCancel() { cancelRequested = true; }
    public synchronized boolean isCancelRequested() { return cancelRequested; }

    public synchronized void recordOutcome(Outcome result) {
        if (result == null) throw new NullPointerException("outcome");
        if (outcome != null && outcome != result) {
            quarantined = true;
            throw new IllegalStateException("Conflicting execution outcomes");
        }
        outcome = result;
    }
    public synchronized void confirmCleanup() {
        if (quarantined) throw new IllegalStateException("Resource quarantined");
        cleanupConfirmed = true;
    }
    public synchronized void quarantine() { quarantined = true; }
    public synchronized boolean isQuarantined() { return quarantined; }
    public synchronized boolean canReleaseResources() {
        return outcome != null && cleanupConfirmed && !quarantined;
    }
    public synchronized Outcome completedOutcome() {
        if (!canReleaseResources()) throw new IllegalStateException("Execution not safely settled");
        return outcome;
    }
}
