package com.agentfusion.core;
import java.util.*;
public final class TaskProgressTest {
    static void check(boolean value) { if (!value) throw new AssertionError(); }
    static void reject(Runnable action) {
        try { action.run(); } catch (IllegalArgumentException | IllegalStateException expected) { return; }
        throw new AssertionError("Expected rejection");
    }
    public static void main(String[] args) throws Exception {
        TaskProgress p = new TaskProgress(Arrays.asList("a", "b"));
        TaskProgress.Snapshot before = p.snapshot();
        p.emit("a", TaskRuntime.State.RUNNING, "");
        p.emit("a", TaskRuntime.State.FAILED, "test");
        p.emit("b", TaskRuntime.State.BLOCKED, "dependency");
        check(p.snapshot().isSettled() && !p.snapshot().isSuccessful());
        check(p.snapshot().settled == 2 && p.snapshot().succeeded == 0);
        System.out.println("PASS settled_is_not_success");
        check(before.sequence == 0 && before.states.get("a") == TaskRuntime.State.PENDING);
        try { before.states.clear(); throw new AssertionError(); } catch (UnsupportedOperationException expected) { }
        System.out.println("PASS immutable_snapshot");
        check(p.eventsAfter(1).size() == 2 && p.eventsAfter(1).get(0).sequence == 2);
        check(p.eventsAfter(3).isEmpty());
        reject(() -> p.eventsAfter(4));
        System.out.println("PASS event_cursor");
        reject(() -> p.emit("a", TaskRuntime.State.SUCCEEDED, ""));
        reject(() -> p.emit("unknown", TaskRuntime.State.RUNNING, ""));
        check(p.snapshot().sequence == 3);
        System.out.println("PASS invalid_transition_no_mutation");
        TaskProgress linked = new TaskProgress(Collections.singletonList("x"));
        TaskRuntime runtime = new TaskRuntime(1, linked);
        runtime.run(Collections.singletonList(new TaskRuntime.Step("x", Collections.emptySet(), Collections.emptySet(), ctx -> {})));
        check(linked.snapshot().isSuccessful() && linked.eventsAfter(0).size() == 2);
        System.out.println("PASS runtime_projection_integration");
        reject(() -> new TaskProgress(Arrays.asList("x", "x")));
        System.out.println("PASS duplicate_id_rejection");
        System.out.println("6 progress tests passed; JVM only, no Android UI or persistence.");
    }
}