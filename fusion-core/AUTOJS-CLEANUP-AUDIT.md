# AutoJs6 cleanup audit (adapter not implemented)

Pinned source: SuperMonster003/AutoJs6@ed3eb10e88db5a8425fd94bdddefa4176e5e1c94.
Paths below are relative to app/src/main/java/org/autojs/autojs/.

## Verified facts
- engine/LoopBasedJavaScriptEngine.java:91-112: forceStop quits the looper, optionally finishes the Activity, delegates to super; destroy quits the looper then delegates. isStopped only negates looper membership, not thread liveness.
- engine/RhinoJavaScriptEngine.kt:96-106: forceStop interrupts the engine thread and cancels script jobs. destroy delegates then calls Context.exit(). Neither shown method joins child threads.
- runtime/ScriptRuntime.kt:585-641: onExit wraps cleanup operations in ignoresException, including threads.shutDownAll at line 630. Normal return therefore cannot certify that all cleanup succeeded. Includes potentially shared cleanup calls (CoreWebSocket.onExit, CoreImageWrapper.recycleAll, root-mode reset); ownership scope needs separate inspection.
- runtime/api/Threads.kt:95-99: shutDownAll interrupts tracked threads and immediately clears the set; no join.
- Threads.kt:102-112: exit clears thread-pool tracking and calls shutdownNow, without awaitTermination.
- Threads.kt:115-125: hasRunningThreads inspects tracked sets/pools. Once shutdown clears/removes those entries, false is not proof of quiescence.
- Threads.kt:175-183: shutdown/shutdownNow remove pools from tracking without awaiting termination.

## Required integration constraints
1. Maintain adapter-owned child-thread and executor records through actual termination, including registration races. Do not derive quiescence from upstream tracking emptiness.
2. An owned execution thread ending or engine.destroy returning is insufficient for shared-resource release.
3. Cancellation requests are distinct from outcome and cleanup acknowledgement. Timeout, failed cleanup or unknown ownership quarantines affected resources.
4. Instrument cleanup failure reporting before calling ExecutionCompletionGate.confirmCleanup; upstream ignoresException hides evidence needed by the gate.
5. Initially reject UI-mode scripts and unsupported child-execution capabilities at the actual API boundary, not by regex on script text.
6. Do not invoke global stopAll for a single task. Review shared cleanup ownership before enabling simultaneous runtimes.

These are source findings and requirements only. No real engine adapter, lifecycle test or Runtime resource-lock integration is claimed.
