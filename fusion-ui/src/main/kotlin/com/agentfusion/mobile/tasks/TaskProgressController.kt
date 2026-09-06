package com.agentfusion.mobile.tasks

import com.agentfusion.core.TaskProgress
import com.agentfusion.core.TaskRuntime
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.concurrent.atomic.AtomicReference

/**
 * Owns the current run's progress projection. It deliberately does not execute
 * arbitrary scripts or tools; the future host adapter will provide Actions.
 */
class TaskProgressController(stepIds: Collection<String>) {
    private val progress = TaskProgress(stepIds)
    private val current = AtomicReference(progress.snapshot())
    private val state = MutableStateFlow(current.get())
    val snapshots: StateFlow<TaskProgress.Snapshot> = state.asStateFlow()
    val events: TaskRuntime.Events = TaskRuntime.Events { id, next, detail ->
        synchronized(progress) {
            progress.emit(id, next, detail)
            val snapshot = progress.snapshot()
            current.set(snapshot)
            state.value = snapshot
        }
    }
    fun snapshot(): TaskProgress.Snapshot = current.get()
    fun eventsAfter(cursor: Long): List<TaskProgress.Event> = progress.eventsAfter(cursor)
}