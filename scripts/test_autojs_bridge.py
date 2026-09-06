import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from patch_autojs_bridge import OLD, transform
SOURCE = ('    private final AbstractAutoJs mAutoJs;\n' + OLD +
          '\nreturn mAutoJs.getInfoProvider();\nreturn mAutoJs.getNotificationObserver();\n')
class BridgePatchTest(unittest.TestCase):
    def test_injection_and_compatibility(self):
        result = transform(SOURCE)
        self.assertIn('AccessibilityBridgeImpl(AbstractAutoJs autoJs)', result)
        self.assertIn('AccessibilityBridgeImpl(android.content.Context context,', result)
        self.assertNotIn('mAutoJs', result)
        self.assertIn('return mInfoProvider;', result)
        self.assertIn('return mNotificationObserver;', result)
    def test_missing_anchor(self):
        with self.assertRaises(ValueError): transform(SOURCE.replace('mAutoJs;', 'other;'))
    def test_ambiguous_anchor(self):
        with self.assertRaises(ValueError): transform(SOURCE + OLD)
    def test_reapply_rejected(self):
        with self.assertRaises(ValueError): transform(transform(SOURCE))
if __name__ == '__main__': unittest.main()
