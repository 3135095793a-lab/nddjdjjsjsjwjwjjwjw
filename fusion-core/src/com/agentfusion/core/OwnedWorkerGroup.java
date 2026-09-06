package com.agentfusion.core;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

/** Tracks only threads created here. Not proof of whole-engine cleanup.
 * No external thread/executor adoption; AutoJs integration is still required.
 */
public final class OwnedWorkerGroup {
    private final List<Thread> workers = new ArrayList<>();
    private boolean sealed;

    /** Starts under the registration lock so sealing cannot miss a starting worker. */
    public synchronized void start(String name, Runnable action) {
        if (sealed) throw new IllegalStateException("Worker registration closed");
        Thread worker = new Thread(Objects.requireNonNull(action), Objects.requireNonNull(name));
        workers.add(worker);
        try { worker.start(); }
        catch (RuntimeException | Error failure) {
            workers.remove(worker);
            throw failure;
        }
    }

    /** Closes registration and requests interruption, but does not report completion. */
    public synchronized void requestStop() {
        sealed = true;
        for (Thread worker : workers) if (worker.isAlive()) worker.interrupt();
    }

    /** No more children may start, including from currently running children. */
    public synchronized void seal() { sealed = true; }

    public synchronized boolean isQuiescent() {
        if (!sealed) return false;
        for (Thread worker : workers) if (worker.isAlive()) return false;
        return true;
    }

    /** Bounded observation only. False means still owned, never safe to release.
     * Interrupting the observer propagates without discarding worker ownership.
     */
    public boolean awaitQuiescence(long timeoutMillis) throws InterruptedException {
        if (timeoutMillis < 0) throw new IllegalArgumentException("Negative timeout");
        final List<Thread> snapshot;
        synchronized (this) {
            if (!sealed) throw new IllegalStateException("Seal registration first");
            snapshot = new ArrayList<>(workers);
        }
        long budget = TimeUnit.MILLISECONDS.toNanos(timeoutMillis);
        long start = System.nanoTime();
        for (Thread worker : snapshot) {
            if (worker == Thread.currentThread()) throw new IllegalStateException("Cannot await self");
            while (worker.isAlive()) {
                long remaining = budget - (System.nanoTime() - start);
                if (remaining <= 0) return false;
                TimeUnit.NANOSECONDS.timedJoin(worker, remaining);
            }
        }
        return isQuiescent();
    }
}
