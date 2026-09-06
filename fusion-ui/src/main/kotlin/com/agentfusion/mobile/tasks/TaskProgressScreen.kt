package com.agentfusion.mobile.tasks

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.flowWithLifecycle
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Process-local ownership only. No task starts from this UI. */
object TaskRunRegistry {
    private val lock = Any()
    private val current = MutableStateFlow<TaskProgressController?>(null)
    val active = current.asStateFlow()

    fun attach(controller: TaskProgressController) = synchronized(lock) {
        check(current.value == null) { "A task is already attached" }
        current.value = controller
    }

    /** Caller must first wait for actual engine termination, not just cancellation request. */
    fun detachAfterTermination(controller: TaskProgressController) = synchronized(lock) {
        check(current.value === controller) { "Task owner mismatch" }
        check(controller.snapshot().isSettled) { "Task has not settled" }
        current.value = null
    }
}

@Composable
fun TaskProgressScreen() {
    val owner = LocalLifecycleOwner.current
    val activeFlow = remember(owner) {
        TaskRunRegistry.active.flowWithLifecycle(owner.lifecycle, Lifecycle.State.STARTED)
    }
    val controller by activeFlow.collectAsState(initial = TaskRunRegistry.active.value)
    val selected = controller
    if (selected == null) {
        TaskProgressPanel(snapshot = null)
    } else {
        androidx.compose.runtime.key(selected) {
            val progressFlow = remember(selected, owner) {
                selected.snapshots.flowWithLifecycle(owner.lifecycle, Lifecycle.State.STARTED)
            }
            val snapshot by progressFlow.collectAsState(initial = selected.snapshot())
            TaskProgressPanel(snapshot = snapshot)
        }
    }
}
