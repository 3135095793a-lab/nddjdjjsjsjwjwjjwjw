package com.agentfusion.core;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Prototype scheduler. Not yet integrated with Android or persistent storage. */
public final class TaskRuntime {
    public enum State { PENDING, RUNNING, SUCCEEDED, FAILED, BLOCKED, CANCELLED }
    public interface Action { void run(Context context) throws Exception; }
    public interface Events { void emit(String id, State state, String detail); }
    public static final class Context {
        private final AtomicBoolean cancelled;
        Context(AtomicBoolean cancelled) { this.cancelled = cancelled; }
        public void checkCancelled() throws InterruptedException {
            if (cancelled.get() || Thread.currentThread().isInterrupted())
                throw new InterruptedException("Task cancelled");
        }
    }
    public static final class Step {
        public final String id;
        public final Set<String> dependencies, resources;
        final Action action;
        public Step(String id, Set<String> dependencies, Set<String> resources, Action action) {
            this.id = Objects.requireNonNull(id);
            this.dependencies = Collections.unmodifiableSet(new HashSet<>(dependencies));
            this.resources = Collections.unmodifiableSet(new HashSet<>(resources));
            this.action = Objects.requireNonNull(action);
        }
    }
    private final AtomicBoolean cancelled = new AtomicBoolean();
    private final int parallelism;
    private final Events events;
    private boolean used;
    public TaskRuntime(int parallelism, Events events) {
        if (parallelism < 1) throw new IllegalArgumentException("parallelism must be positive");
        this.parallelism = parallelism;
        this.events = Objects.requireNonNull(events);
    }
    public void cancel() { cancelled.set(true); }
    private void transition(Map<String, State> states, String id, State state, String detail) {
        states.put(id, state);
        events.emit(id, state, detail);
    }
    private static void validate(Map<String, Step> steps) {
        Set<String> resolved = new HashSet<>();
        for (Step s : steps.values()) for (String d : s.dependencies)
            if (!steps.containsKey(d)) throw new IllegalArgumentException("Missing dependency: " + d);
        boolean changed;
        do {
            changed = false;
            for (Step s : steps.values())
                if (!resolved.contains(s.id) && resolved.containsAll(s.dependencies)) {
                    resolved.add(s.id); changed = true;
                }
        } while (changed);
        if (resolved.size() != steps.size()) throw new IllegalArgumentException("Dependency cycle");
    }
    public synchronized Map<String, State> run(List<Step> input) throws InterruptedException {
        if (used) throw new IllegalStateException("Runtime is single-use");
        used = true;
        Map<String, Step> steps = new LinkedHashMap<>();
        for (Step s : input) if (steps.put(s.id, s) != null)
            throw new IllegalArgumentException("Duplicate step: " + s.id);
        validate(steps); // No actions execute before the whole graph is validated.
        Map<String, State> states = new LinkedHashMap<>();
        for (String id : steps.keySet()) states.put(id, State.PENDING);
        Map<String, Future<?>> running = new LinkedHashMap<>();
        Set<String> held = new HashSet<>();
        ExecutorService pool = Executors.newFixedThreadPool(parallelism);
        try {
            while (states.values().stream().anyMatch(s -> s == State.PENDING || s == State.RUNNING)) {
                for (Iterator<Map.Entry<String, Future<?>>> it = running.entrySet().iterator(); it.hasNext();) {
                    Map.Entry<String, Future<?>> e = it.next();
                    if (!e.getValue().isDone()) continue;
                    State result = State.SUCCEEDED; String detail = "";
                    try { e.getValue().get(); }
                    catch (ExecutionException error) {
                        Throwable cause = error.getCause();
                        result = cause instanceof InterruptedException ? State.CANCELLED : State.FAILED;
                        detail = cause.getClass().getSimpleName();
                    }
                    catch (CancellationException error) { result = State.CANCELLED; }
                    held.removeAll(steps.get(e.getKey()).resources);
                    transition(states, e.getKey(), result, detail); it.remove();
                }
                for (Step step : steps.values()) {
                    if (states.get(step.id) != State.PENDING) continue;
                    if (cancelled.get()) { transition(states, step.id, State.CANCELLED, "Not started"); continue; }
                    boolean blocked = step.dependencies.stream().anyMatch(d ->
                        states.get(d) == State.FAILED || states.get(d) == State.BLOCKED || states.get(d) == State.CANCELLED);
                    if (blocked) { transition(states, step.id, State.BLOCKED, "Dependency unsuccessful"); continue; }
                    if (!step.dependencies.stream().allMatch(d -> states.get(d) == State.SUCCEEDED)) continue;
                    if (running.size() >= parallelism || !Collections.disjoint(held, step.resources)) continue;
                    held.addAll(step.resources);
                    transition(states, step.id, State.RUNNING, "");
                    running.put(step.id, pool.submit(() -> {
                        Context context = new Context(cancelled);
                        context.checkCancelled(); step.action.run(context); return null;
                    }));
                }
                if (!running.isEmpty()) Thread.sleep(5);
            }
            return Collections.unmodifiableMap(new LinkedHashMap<>(states));
        } finally { pool.shutdownNow(); }
    }
}
