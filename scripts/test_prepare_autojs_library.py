import os
import shutil
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


def run_real_upstream_fixture(source_root):
    app = Path(source_root) / 'app'
    layout = (app / 'src/main/res/layout/bottom_sheet_log.xml').read_text()
    colors = (app / 'src/main/res/values/colors_legacy.xml').read_text()
    expected = layout.replace(
        '@color/console_debug', '@color/legacy_console_debug'
    ).replace('@color/console_verbose', '@color/legacy_console_verbose')
    actual = prepare_module.transform_log_resources(layout, colors)
    if actual != expected:
        raise AssertionError('fixed upstream layout changed beyond two color references')


class PrepareResourcesTest(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for root in self.roots:
            shutil.rmtree(root)

    def new_root(self):
        root = make_root()
        self.roots.append(root)
        return root

    def snapshot(self, root):
        return {path.relative_to(root): path.read_bytes() for path in root.rglob('*') if path.is_file()}

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

    def test_missing_duplicate_and_invalid_legacy_resources_rejected(self):
        for colors in (
            COLORS.replace('legacy_console_debug', 'missing'),
            COLORS + '<color name="legacy_console_debug">#cc000000</color>',
            COLORS.replace('#cc000000', '#ffffffff'),
        ):
            with self.subTest(colors=colors), self.assertRaises(ValueError):
                prepare_module.transform_log_resources(LAYOUT, colors)

    def test_prepare_success_changes_only_expected_layout_references(self):
        root = self.new_root()
        layout = root / 'app/src/main/res/layout/bottom_sheet_log.xml'
        with patch.object(prepare_module, 'verify', return_value=('patched-bridge', {})):
            prepare_module.prepare(root)
        self.assertEqual(
            layout.read_text(),
            LAYOUT.replace('@color/console_debug', '@color/legacy_console_debug').replace(
                '@color/console_verbose', '@color/legacy_console_verbose'
            ),
        )

    def test_prepare_validation_failure_leaves_tree_unchanged(self):
        root = self.new_root()
        layout = root / 'app/src/main/res/layout/bottom_sheet_log.xml'
        with patch.object(prepare_module, 'verify', return_value=(b'patched-bridge', {})):
            layout.write_text(LAYOUT.replace('@color/console_verbose', 'missing'))
            before_failure = self.snapshot(root)
            with self.assertRaises(ValueError):
                prepare_module.prepare(root)
        self.assertEqual(self.snapshot(root), before_failure)
        self.assertFalse((root / 'fusion-original-manifest.xml').exists())
        self.assertFalse((root / 'fusion-library-probe.json').exists())

    def test_cross_file_color_and_item_conflicts_leave_tree_unchanged(self):
        for definition in (
            '<color name="console_debug">#000000</color>',
            '<item name="console_verbose" type="color">#000000</item>',
        ):
            with self.subTest(definition=definition):
                root = self.new_root()
                conflict = root / 'app/src/main/res/values-v99/conflict.xml'
                conflict.parent.mkdir()
                conflict.write_text('<resources>' + definition + '</resources>')
                before_failure = self.snapshot(root)
                with patch.object(prepare_module, 'verify', return_value=(b'patched-bridge', {})):
                    with self.assertRaisesRegex(ValueError, 'Conflicting old color resource'):
                        prepare_module.prepare(root)
                self.assertEqual(self.snapshot(root), before_failure)


if __name__ == '__main__':
    source_root = os.environ.get('AUTOJS_SOURCE_ROOT')
    if source_root:
        run_real_upstream_fixture(source_root)
    unittest.main()
