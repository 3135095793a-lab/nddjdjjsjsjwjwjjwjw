package com.agentfusion.core;
import static com.agentfusion.core.ExecutionCompletionGate.Outcome.*;
public final class ExecutionCompletionGateTest {
    static void check(boolean b) { if (!b) throw new AssertionError(); }
    static void rejects(Runnable r) {
        try { r.run(); } catch (IllegalStateException e) { return; }
        throw new AssertionError("Expected rejection");
    }
    public static void main(String[] args) {
        ExecutionCompletionGate g = new ExecutionCompletionGate();
        g.requestCancel(); check(g.isCancelRequested() && !g.canReleaseResources());
        rejects(() -> g.completedOutcome());
        System.out.println("PASS cancel_request_is_not_completion");
        g.recordOutcome(CANCELLED); check(!g.canReleaseResources());
        g.confirmCleanup(); check(g.completedOutcome() == CANCELLED);
        System.out.println("PASS result_requires_cleanup");
        ExecutionCompletionGate reversed = new ExecutionCompletionGate();
        reversed.confirmCleanup(); check(!reversed.canReleaseResources());
        reversed.recordOutcome(SUCCEEDED); check(reversed.canReleaseResources());
        System.out.println("PASS cleanup_requires_result");
        ExecutionCompletionGate failed = new ExecutionCompletionGate();
        failed.recordOutcome(FAILED); failed.quarantine();
        rejects(() -> failed.confirmCleanup()); check(!failed.canReleaseResources());
        System.out.println("PASS quarantine_is_sticky");
        ExecutionCompletionGate conflict = new ExecutionCompletionGate();
        conflict.recordOutcome(SUCCEEDED);
        rejects(() -> conflict.recordOutcome(FAILED)); check(conflict.isQuarantined());
        System.out.println("PASS conflicting_outcomes_quarantine");
        ExecutionCompletionGate duplicate = new ExecutionCompletionGate();
        duplicate.recordOutcome(SUCCEEDED); duplicate.recordOutcome(SUCCEEDED);
        duplicate.confirmCleanup(); duplicate.confirmCleanup();
        check(duplicate.completedOutcome() == SUCCEEDED);
        System.out.println("PASS duplicate_acknowledgements");
        System.out.println("6 completion gate tests passed. No real engine lifecycle tested.");
    }
}