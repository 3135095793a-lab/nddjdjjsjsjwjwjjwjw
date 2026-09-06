import unittest
from apply_host_overlay import transform

SOURCE = '''namespace = "com.ai.assistance.operit"
applicationId = "com.ai.assistance.operit"
applicationIdSuffix = ".debug"
resValue("string", "app_name", "Operit Debug")
resValue("string", "app_name", "Operit Clone")
'''

class OverlayTest(unittest.TestCase):
    def test_identity(self):
        result = transform(SOURCE)
        self.assertIn('applicationId = "com.agentfusion.mobile"', result)
        self.assertIn('namespace = "com.ai.assistance.operit"', result)
        self.assertIn('applicationIdSuffix = ".debug"', result)
        self.assertIn('AgentFusion Dev', result)
    def test_missing_anchor_rejected(self):
        with self.assertRaises(ValueError): transform('')
    def test_duplicate_anchor_rejected(self):
        with self.assertRaises(ValueError): transform(SOURCE + SOURCE)
    def test_reapply_rejected(self):
        with self.assertRaises(ValueError): transform(transform(SOURCE))

if __name__ == '__main__': unittest.main()
