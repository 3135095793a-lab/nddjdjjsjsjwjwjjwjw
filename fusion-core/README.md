# Fusion core — prototype, not Android integrated

TaskRuntime and eight JVM tests are now versioned here. They are original project prototype code, not an AutoJs6 adapter. No fusion APK is produced by this directory.

Run with Java 8 or newer:

```sh
out=$(mktemp -d)
javac --release 8 -d "$out" src/com/agentfusion/core/*.java tests/com/agentfusion/core/*.java && java -cp "$out" com.agentfusion.core.TaskRuntimeTest
```

Known limitations: cooperative cancellation only, locks local to one run, no persistence or Android UI. Executor shutdown and event-sink failure handling require further hardening before production integration.

Operit integration must preserve ToolExecutionManager's exposure, role-card, hook and permission checks; calling AIToolHandler directly is not a substitute for those checks.

## Baseline evidence

Run 33999293003 completed successfully; downloaded Gradle report says `BUILD SUCCESSFUL in 20m 47s`, exit code 0. Uploaded baseline archive is 430439750 bytes, not a fusion release. Its APK has not been installed or runtime-tested.

Warnings requiring follow-up: duplicate arm64 libc++_shared.so and libsudo.so could not be stripped. The latter was packaged unchanged. Compilation success does not establish native runtime compatibility.
