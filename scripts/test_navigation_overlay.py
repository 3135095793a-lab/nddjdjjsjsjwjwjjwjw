import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_navigation_overlay import transform

SCREEN = '    data object Workflow : Screen(navItem = NavItem.Workflow) {\n    }\n'
REGISTRY = '            hostEntryDefinition(\n                entryId = "main.workflow",\n                screen = Screen.Workflow,\n            ),\n'

class NavigationTest(unittest.TestCase):
    def test_preserve_workflow(self):
        s, r = transform(SCREEN, REGISTRY)
        self.assertIn(SCREEN, s)
        self.assertIn(REGISTRY, r)
        self.assertEqual(s.count('data object AgentFusionTasks'), 1)
        self.assertEqual(r.count('main.agentfusion_tasks'), 1)
        self.assertIn('TaskProgressPanel(snapshot = null)', s)
    def test_missing_anchor(self):
        with self.assertRaises(ValueError): transform('', REGISTRY)
        with self.assertRaises(ValueError): transform(SCREEN, '')
    def test_duplicate_anchor(self):
        with self.assertRaises(ValueError): transform(SCREEN * 2, REGISTRY)
    def test_reapply_rejected(self):
        with self.assertRaises(ValueError): transform(*transform(SCREEN, REGISTRY))

if __name__ == '__main__': unittest.main()
