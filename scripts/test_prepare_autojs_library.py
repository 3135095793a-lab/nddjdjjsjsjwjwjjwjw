import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_autojs_library as prepare_module

LAYOUT = '''<log-view
    app:color_debug="@color/console_debug"
    app:color_verbose="@color/console_verbose"/>
'''
COLORS = '''<resources>
    <color name="legacy_console_debug">#cc000000</color>
    <color name="legacy_console_verbose">#dfc0c0c0</color>
</resources>
'''
GRADLE = '''plugins {
    id("com.android.application")
    id("org.autojs.build.signs")
}
utils.registerTemplateApkCopy(project)

android {
    old = true
}
'''
LOG = 'AutoJs.getInstance()\nAutoJs.getInstance()\n'


def make_root():
    root = Path(tempfile.mkdtemp())
    app = root / 'app'
    (app / 'src/main/res/layout').mkdir(parents=True)
    (app / 'src/main/res/values').mkdir(parents=True)
    (app / 'src/main/java/org/autojs/autojs/core/accessibility').mkdir(parents=True)
    (app / 'src/main/java/org/autojs/autojs/ui/log').mkdir(parents=True)
    (app / 'build.gradle.kts').write_text(GRADLE)
    (app / 'src/main/res/layout/bottom_sheet_log.xml').write_text(LAYOUT)
    (app / 'src/main/res/values/colors_legacy.xml').write_text(COLORS)
    (app / 'src/main/java/org/autojs/autojs/core/accessibility/AccessibilityBridgeImpl.java').write_text('bridge')
    (app / 'src/main/java/org/autojs/autojs/ui/log/LogBottomSheet.kt').write_text(LOG)
    (app / 'src/main/AndroidManifest.xml').parent.mkdir(parents=True, exist_ok=True)
    (app / 'src/main/AndroidManifest.xml').write_text('<manifest />\n')
    return root


class PrepareResourcesTest(unittest.TestCase):
    def test_fixed_fixture_and_unrelated_content(self):
        result = prepare_module.transform_log_resources(LAYOUT, COLORS)
        self.assertEqual(result.count('@color/legacy_console_debug'), 1)
        self.assertEqual(result.count('@color/legacy_console_verbose'), 1)
        self.assertIn('<log-view', result)
        self.assertIn('app:color_debug=', result)
        self.assertNotIn('@color/console_debug', result)
        self.assertNotIn('@color/console_verbose', result)

    def test_missing_and_duplicate_anchors_rejected(self):
        with self.assertRaises(ValueError):
            prepare_module.transform_log_resources(LAYOUT.replace('@color/console_debug', 'missing'), COLORS)
        with self.assertRaises(ValueError):
            prepare_module.transform_log_resources(LAYOUT + LAYOUT, COLORS)

    def test_missing_duplicate_invalid_and_conflicting_resources_rejected(self):
        for colors in (
            COLORS.replace('legacy_console_debug', 'missing'),
            COLORS + '<color name="legacy_console_debug">#cc000000</color>',
            COLORS.replace('#cc000000', '#ffffffff'),
            COLORS.replace('legacy_console_debug', 'console_debug'),
        ):
            with self.subTest(colors=colors), self.assertRaises(ValueError):
                prepare_module.transform_log_resources(LAYOUT, colors)

    def test_prepare_validation_failure_leaves_tree_unchanged(self):
        root = make_root()
        layout = root / 'app/src/main/res/layout/bottom_sheet_log.xml'
        snapshot = {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}
        with patch.object(prepare_module, 'verify', return_value=(b'patched-bridge', {})):
            layout.write_text(LAYOUT.replace('@color/console_verbose', 'missing'))
            before_failure = {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}
            with self.assertRaises(ValueError):
                prepare_module.prepare(root)
        after = {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}
        self.assertEqual(after, before_failure)
        self.assertFalse((root / 'fusion-original-manifest.xml').exists())
        self.assertFalse((root / 'fusion-library-probe.json').exists())
        self.assertEqual(snapshot.keys(), before_failure.keys())


if __name__ == '__main__':
    unittest.main()
