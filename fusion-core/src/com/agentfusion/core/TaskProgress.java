package com.agentfusion.core;

import java.util.*;

/** Thread-safe in-memory projection for one run. No Android or disk persistence yet. */
public final class TaskProgress implements TaskRuntime.Events {
    public static final class Event {
        public final long sequence;
        public final String stepId;
        public final TaskRuntime.State state;
        public final String detail;
        private Event(long sequence, String stepId, TaskRuntime.State state, String detail) {
            this.sequence = sequence; this.stepId = stepId;
            this.state = state; this.detail = detail;
        }
    }
    public static final class Snapshot {
        public final long sequence;
        public final Map<String, TaskRuntime.State> states;
        public final int total, settled, succeeded;
        private Snapshot(long sequence, Map<String, TaskRuntime.State> source) {
            this.sequence = sequence;
            states = Collections.unmodifiableMap(new LinkedHashMap<>(source));
            total = states.size();
            int done = 0, ok = 0;
            for (TaskRuntime.State state : states.values()) {
                if (terminal(state)) done++;
                if (state == TaskRuntime.State.SUCCEEDED) ok++;
            }
            settled = done; succeeded = ok;
        }
        public boolean isSettled() { return settled == total; }
        public boolean isSuccessful() { return isSettled() && succeeded == total; }
    }
    private final Map<String, TaskRuntime.State> states = new LinkedHashMap<>();
    private final List<Event> events = new ArrayList<>();
    private long sequence;
    public TaskProgress(Collection<String> ids) {
        for (String id : ids) {
            Objects.requireNonNull(id);
            if (id.isEmpty() || states.put(id, TaskRuntime.State.PENDING) != null)
                throw new IllegalArgumentException("Invalid or duplicate step id");
        }
    }
    private static boolean terminal(TaskRuntime.State state) {
        return state != TaskRuntime.State.PENDING && state != TaskRuntime.State.RUNNING;
    }
    @Override public synchronized void emit(String id, TaskRuntime.State next, String detail) {
        Objects.requireNonNull(next);
        TaskRuntime.State old = states.get(id);
        if (old == null) throw new IllegalArgumentException("Unknown step");
        boolean allowed = old == TaskRuntime.State.PENDING
            ? next == TaskRuntime.State.RUNNING || next == TaskRuntime.State.BLOCKED || next == TaskRuntime.State.CANCELLED
            : old == TaskRuntime.State.RUNNING && (next == TaskRuntime.State.SUCCEEDED || next == TaskRuntime.State.FAILED || next == TaskRuntime.State.CANCELLED);
        if (!allowed) throw new IllegalStateException("Invalid task transition: " + old + " -> " + next);
        events.add(new Event(++sequence, id, next, detail == null ? "" : detail));
        states.put(id, next);
    }
    public synchronized Snapshot snapshot() { return new Snapshot(sequence, states); }
    public synchronized List<Event> eventsAfter(long cursor) {
        if (cursor < 0 || cursor > sequence) throw new IllegalArgumentException("Invalid event cursor");
        List<Event> result = new ArrayList<>();
        for (Event event : events) if (event.sequence > cursor) result.add(event);
        return Collections.unmodifiableList(result);
    }
}
