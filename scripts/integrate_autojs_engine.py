"""Preserve pinned AutoJs settings in a composite source Library build."""
from pathlib import Path
import argparse, shutil, subprocess, re, tomllib
from prepare_autojs_library import prepare, PIN

def main(host, autojs):
    host, autojs = host.resolve(), autojs.resolve()
    actual = subprocess.check_output(['git', '-C', str(autojs), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != PIN:
        raise ValueError('Unexpected AutoJs revision: ' + actual)
    out = host / 'autojs-engine'
    if out.exists():
        raise ValueError('Refusing to overwrite engine build')
    shutil.copytree(autojs, out, ignore=shutil.ignore_patterns('.git', '.gradle', '__pycache__'))
    # A source package is literally org/autojs/build: never exclude that name.
    for source in (autojs / 'build-logic').rglob('*.kt'):
        copied = out / source.relative_to(autojs)
        if not copied.is_file() or copied.read_bytes() != source.read_bytes():
            raise ValueError('Build plugin source missing or changed: ' + str(source))
    catalog = tomllib.loads((host / 'gradle/libs.versions.toml').read_text())
    agp = catalog['versions']['agp']
    version_file = out / 'version.properties'
    versions, count = re.subn(r'^OVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=.*$',
        'OVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=' + agp,
        version_file.read_text(), flags=re.M)
    if count != 1:
        raise ValueError('Missing or ambiguous upstream AGP override')
    version_file.write_text(versions)
    prepare(out)
    settings = host / 'settings.gradle.kts'
    text = settings.read_text()
    if 'includeBuild("autojs-engine")' in text:
        raise ValueError('Engine already registered')
    text += '''
// Source-built Library, packaged into the host APK.
includeBuild("autojs-engine") {
    dependencySubstitution {
        substitute(module("org.agentfusion:autojs-engine")).using(project(":app"))
    }
}
'''
    settings.write_text(text)
    app = host / 'app/build.gradle.kts'
    text = app.read_text()
    marker = 'dependencies {'
    if marker not in text:
        raise ValueError('Host dependencies anchor missing')
    app.write_text(text.replace(marker, marker + '\n    implementation("org.agentfusion:autojs-engine:1.0")', 1))
    print('AUTOJS_COMPOSITE_LIBRARY_STAGED', PIN)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('host', type=Path)
    p.add_argument('autojs', type=Path)
    a = p.parse_args()
    main(a.host, a.autojs)
