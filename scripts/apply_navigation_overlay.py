"""Pinned native navigation patch; no task execution is wired yet."""
from pathlib import Path

def transform(screens, registry):
    anchor = '    data object Workflow : Screen(navItem = NavItem.Workflow) {'
    page = '''    data object AgentFusionTasks : Screen(titleRes = R.string.agentfusion_tasks_title) {
        @Composable
        override fun Content(
                navController: NavController,
                navigateTo: ScreenNavigationHandler,
                onGoBack: () -> Unit,
                hasBackgroundImage: Boolean,
                onLoading: (Boolean) -> Unit,
                onError: (String) -> Unit,
                onGestureConsumed: (Boolean) -> Unit
        ) {
            com.agentfusion.mobile.tasks.TaskProgressScreen()
        }
    }
'''
    entry_anchor = '            hostEntryDefinition(\n                entryId = "main.workflow",'
    entry = '''            hostEntryDefinition(
                entryId = "main.agentfusion_tasks",
                screen = Screen.AgentFusionTasks,
                surface = NavigationSurface.MAIN_SIDEBAR_TOOLS,
                titleResId = R.string.agentfusion_tasks_title,
                icon = NavItem.Workflow.icon,
                order = 31
            ),
'''
    if screens.count(anchor) != 1 or registry.count(entry_anchor) != 1:
        raise ValueError('Navigation anchors changed')
    if 'AgentFusionTasks' in screens or 'main.agentfusion_tasks' in registry:
        raise ValueError('Navigation overlay already present')
    return screens.replace(anchor, page + anchor), registry.replace(entry_anchor, entry + entry_anchor)

def apply(root):
    base = Path(root) / 'app/src/main'
    directory = base / 'java/com/ai/assistance/operit/ui/main/screens'
    screens = directory / 'OperitScreens.kt'
    registry = directory / 'ScreenRouteRegistry.kt'
    resource = base / 'res/values/agentfusion.xml'
    if resource.exists():
        raise ValueError('Resource collision')
    s, r = transform(screens.read_text(), registry.read_text())
    screens.write_text(s)
    registry.write_text(r)
    resource.write_text('<resources><string name="agentfusion_tasks_title">AgentFusion 任务</string></resources>\n')
