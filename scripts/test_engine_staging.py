"""Regression: build is also a legitimate Kotlin package directory."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrate_autojs_engine import main, PIN

class StagingTest(unittest.TestCase):
    def test_plugin_sources_and_composite_dependency_survive(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            host, source = root/'host', root/'source'
            (host/'app').mkdir(parents=True)
            (host/'gradle').mkdir()
            (host/'gradle/libs.versions.toml').write_text('[versions]\nagp = "8.13.2"\n')
            source.mkdir()
            (source/'version.properties').write_text('OVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=NONE\n')
            (host/'settings.gradle.kts').write_text('rootProject.name = "host"\n')
            (host/'app/build.gradle.kts').write_text('dependencies {\n}\n')
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
            with patch('integrate_autojs_engine.subprocess.check_output', return_value=PIN):
                with self.assertRaises(ValueError):
                    main(host, source)

if __name__ == '__main__':
    unittest.main()
