package com.agentfusion.mobile.tasks

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.agentfusion.core.TaskProgress
import com.agentfusion.core.TaskRuntime

/** Pure rendering only. Caller must supply fresh snapshots from the task owner. */
@Composable
fun TaskProgressPanel(snapshot: TaskProgress.Snapshot?, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier.fillMaxWidth().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text("任务进度", style = MaterialTheme.typography.titleLarge)
        if (snapshot == null || snapshot.total == 0) {
            Text("暂无任务。自动化引擎尚未接入。")
        } else {
            Text("已结束 ${snapshot.settled}/${snapshot.total} · 成功 ${snapshot.succeeded}")
            if (snapshot.isSettled) {
                Text(if (snapshot.isSuccessful) "全部步骤成功" else "任务已结束，但并非全部成功")
            }
            snapshot.states.forEach { (id, state) ->
                Text("$id · ${stateLabel(state)}")
            }
        }
    }
}

private fun stateLabel(state: TaskRuntime.State): String = when (state) {
    TaskRuntime.State.PENDING -> "等待"
    TaskRuntime.State.RUNNING -> "运行中"
    TaskRuntime.State.SUCCEEDED -> "成功"
    TaskRuntime.State.FAILED -> "失败"
    TaskRuntime.State.BLOCKED -> "前置步骤未成功"
    TaskRuntime.State.CANCELLED -> "已取消"
}
