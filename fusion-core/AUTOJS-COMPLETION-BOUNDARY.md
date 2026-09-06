# AutoJs6 completion boundary — verified source, adapter not implemented

Pinned source: SuperMonster003/AutoJs6 ed3eb10e88db5a8425fd94bdddefa4176e5e1c94.

## Findings

- `org/autojs/autojs/execution/RunnableScriptExecution.java`, private `execute(engine)`: calls listener onSuccess (or onException) before the finally block invokes engine.destroy(). Callback outcome alone therefore does not establish cleanup completion.
- Engine creation in public execute() occurs before the private execute(engine) try/finally. Creation errors need a separate adapter boundary.
- `engine/ScriptEngineManager.java`, stopAll(): iterates engine.forceStop() and returns engine count. There is no wait/join in this method. Do not use its return as stop acknowledgement.
- `engine/ScriptEngineService.java`: normal scripts use a ThreadCompat running RunnableScriptExecution/LoopedBasedJavaScriptExecution; UI-mode scripts use ScriptExecuteActivity. Do not apply thread-join assumptions to UI mode.

## Adapter requirements (not implemented)

1. Capture result/error separately from lifecycle completion.
2. Own the execution thread in the source-level adapter; surround creation, initialization, execution and cleanup with a host boundary.
3. Resource release requires verified cleanup plus quiescence of relevant child workers. Even return from destroy() is not proof until its implementation is audited.
4. Cancellation requests must not mark the job completed. A cleanup error or timeout should quarantine the resource rather than allow a new screen-writing action.
5. Stop only the owned execution, not all scripts in the host. Avoid global stopAll in per-task cancellation.
6. Initial support should reject UI-mode scripts explicitly until their Activity lifecycle is adapted, rather than launch the original AutoJs6 app.

No adapter or Android runtime tests are claimed by this document. Previous statements implying listener callbacks prove resource release were too strong.
