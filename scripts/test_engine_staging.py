"""Regression: build is also a legitimate Kotlin package directory."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrate_autojs_engine import main, align_catalog, PIN



CATALOG = """[versions]
agp = "8.13.2"
desugar = "2.0.4"
[libraries]
desugar-jdk = { group = "com.android.tools", name = "desugar_jdk_libs", version.ref = "desugar" }
"""
APP = """dependencies {
    coreLibraryDesugaring(libs.desugar.jdk)
}
"""

class StagingTest(unittest.TestCase):

    def test_catalog_alignment(self):
        result = align_catalog(CATALOG, APP)
        self.assertIn('desugar = "2.1.5"', result)
        self.assertEqual(align_catalog(result, APP), result)

    def test_invalid_catalog_inputs(self):
        for text, app in [
            (CATALOG, ""),
            (CATALOG, APP + APP),
            (CATALOG.replace("2.0.4", "2.0.3"), APP),
            (CATALOG.replace("[libraries]", 'desugar = "2.0.4"\n[libraries]'), APP),
            (CATALOG.replace("desugar-jdk", "other-lib"), APP),
            (CATALOG.replace('version.ref = "desugar"', 'version = "2.0.4"'), APP),
        ]:
            with self.subTest(text=text, app=app), self.assertRaises(ValueError):
                align_catalog(text, app)

    def test_pre_checks_failure_leaves_host_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            host, source = root / "host", root / "source"
            (host / "app").mkdir(parents=True)
            (host / "gradle").mkdir()
            (host / "gradle/libs.versions.toml").write_text(CATALOG)
            source.mkdir()
            (source / "version.properties").write_text("OVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=NONE\n")
            (host / "settings.gradle.kts").write_text('rootProject.name = "host"\n')
            (host / "app/build.gradle.kts").write_text("dependencies {\n}\n")

            with patch("integrate_autojs_engine.subprocess.check_output", return_value=PIN):
                with self.assertRaises(ValueError):
                    main(host, source)

            self.assertFalse((host / "autojs-engine").exists())
            self.assertEqual((host / "gradle/libs.versions.toml").read_text(), CATALOG)
            self.assertNotIn("autojs-engine", (host / "settings.gradle.kts").read_text())

    def test_plugin_sources_and_composite_dependency_survive(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            host, source = root/'host', root/'source'
            (host/'app').mkdir(parents=True)
            (host/'gradle').mkdir()
            (host / 'gradle/libs.versions.toml').write_text(CATALOG)
            source.mkdir()
            (source/'version.properties').write_text('OVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=NONE\n')
            (host/'settings.gradle.kts').write_text('rootProject.name = "host"\n')
            (host / 'app/build.gradle.kts').write_text(APP)
            relative = Path('build-logic/convention/src/main/kotlin/org/autojs/build/UtilsPlugin.kt')
            plugin = source/relative
            plugin.parent.mkdir(parents=True)
            plugin.write_text('package org.autojs.build\nclass UtilsPlugin\n')
            with patch('integrate_autojs_engine.subprocess.check_output', return_value=PIN), patch('integrate_autojs_engine.prepare') as prepare:
                main(host, source)
                prepare.assert_called_once_with(host/'autojs-engine')
            self.assertEqual(plugin.read_bytes(), (host/'autojs-engine'/relative).read_bytes())
            self.assertIn('using(project(":app"))', (host/'settings.gradle.kts').read_text())
            self.assertIn('org.agentfusion:autojs-engine:1.0', (host/'app/build.gradle.kts').read_text())
            self.assertIn('desugar = "2.1.5"', (host / 'gradle/libs.versions.toml').read_text())
            with patch('integrate_autojs_engine.subprocess.check_output', return_value=PIN):
                with self.assertRaises(ValueError):
                    main(host, source)

if __name__ == '__main__':
    unittest.main()
