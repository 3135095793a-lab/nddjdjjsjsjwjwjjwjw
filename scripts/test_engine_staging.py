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

        # Leading whitespace on [versions] and indented sections
        indented_catalog = f"""  [versions]
agp = "8.13.2"
desugar = "2.0.4"
  [libraries]
desugar-jdk = {{ group = "com.android.tools", name = "desugar_jdk_libs", version.ref = "desugar" }}
"""
        indented_res = align_catalog(indented_catalog, APP)
        self.assertIn('desugar = "2.1.5"', indented_res)
        self.assertEqual(align_catalog(indented_res, APP), indented_res)

        # Verbatim preservation of unrelated versions, libraries, and comments
        complex_catalog = f"""# Top-level comment
[versions]
# Version comments
agp = "8.13.2" # inline comment
desugar = "2.0.4"
kotlin = "2.2.21"

[libraries]
# Lib comment
desugar-jdk = {{ group = "com.android.tools", name = "desugar_jdk_libs", version.ref = "desugar" }}
other-lib = "foo:bar:1.0"
"""
        aligned_complex = align_catalog(complex_catalog, APP)
        expected_complex = complex_catalog.replace('"2.0.4"', '"2.1.5"', 1)
        self.assertEqual(aligned_complex, expected_complex)

    def test_invalid_catalog_inputs(self):
        for text, app in [
            (CATALOG, ""),
            (CATALOG, APP + APP),
            (CATALOG.replace("2.0.4", "2.0.3"), APP),
            (CATALOG.replace("[libraries]", 'desugar = "2.0.4"\n[libraries]'), APP),
            (CATALOG.replace("desugar = \"2.0.4\"", ""), APP),
            (CATALOG.replace("desugar-jdk", "other-lib"), APP),
            (CATALOG.replace('group = "com.android.tools"', 'group = "other.tools"'), APP),
            (CATALOG.replace('name = "desugar_jdk_libs"', 'name = "other_libs"'), APP),
            (CATALOG.replace('version.ref = "desugar"', 'version.ref = "other_ref"'), APP),
            (CATALOG.replace('version.ref = "desugar"', 'version = "2.0.4"'), APP),
        ]:
            with self.subTest(text=text, app=app), self.assertRaises(ValueError):
                align_catalog(text, app)

    def test_pre_checks_failure_leaves_host_untouched(self):
        cases = [
            ("corrupted_app_desugar", lambda h, s: (h / "app/build.gradle.kts").write_text("dependencies {\n}\n"), "Missing or ambiguous host desugar dependency"),
            ("missing_app", lambda h, s: (h / "app/build.gradle.kts").unlink(), "Missing host app/build.gradle.kts"),
            ("missing_settings", lambda h, s: (h / "settings.gradle.kts").unlink(), "Missing host settings.gradle.kts"),
            ("missing_catalog", lambda h, s: (h / "gradle/libs.versions.toml").unlink(), "Missing host libs.versions.toml"),
            ("missing_dependencies_anchor", lambda h, s: (h / "app/build.gradle.kts").write_text(APP.replace("dependencies {", "no_anchor {")), "Missing or ambiguous dependencies anchor"),
            ("duplicate_dependencies_anchor", lambda h, s: (h / "app/build.gradle.kts").write_text(APP + "\ndependencies {\n}\n"), "Missing or ambiguous dependencies anchor"),
            ("already_registered_include", lambda h, s: (h / "settings.gradle.kts").write_text('includeBuild("autojs-engine")\n'), "Engine already registered"),
            ("already_registered_dep", lambda h, s: (h / "app/build.gradle.kts").write_text(APP + '\n    implementation("org.agentfusion:autojs-engine:1.0")\n'), "Engine already registered"),
            ("missing_upstream_version", lambda h, s: (s / "version.properties").unlink(), "Missing upstream version.properties"),
            ("corrupted_upstream_agp", lambda h, s: (s / "version.properties").write_text("NO_AGP_OVERRIDE=1\n"), "Missing or ambiguous upstream AGP override"),
            ("duplicate_upstream_agp", lambda h, s: (s / "version.properties").write_text("OVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=8.13.2\nOVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=8.13.2\n"), "Missing or ambiguous upstream AGP override"),
        ]
        for name, corrupt, expected_regex in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                host, source = root / "host", root / "source"
                (host / "app").mkdir(parents=True)
                (host / "gradle").mkdir()
                (host / "gradle/libs.versions.toml").write_text(CATALOG)
                source.mkdir()
                (source / "version.properties").write_text("OVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=NONE\n")
                (host / "settings.gradle.kts").write_text('rootProject.name = "host"\n')
                (host / "app/build.gradle.kts").write_text(APP)

                corrupt(host, source)

                # Snapshot existing host files (relative path -> bytes)
                snapshot = {p.relative_to(host): p.read_bytes() for p in host.rglob("*") if p.is_file()}

                with patch("integrate_autojs_engine.subprocess.check_output", return_value=PIN), \
                     patch("integrate_autojs_engine.prepare") as mock_prepare:
                    with self.assertRaisesRegex(ValueError, expected_regex):
                        main(host, source)
                    mock_prepare.assert_not_called()

                self.assertFalse((host / "autojs-engine").exists())
                # Exact bidirectional comparison of full host files mapping
                post_snapshot = {p.relative_to(host): p.read_bytes() for p in host.rglob("*") if p.is_file()}
                self.assertEqual(post_snapshot, snapshot)

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
