"""Preserve pinned AutoJs settings in a composite source Library build."""
from pathlib import Path
import argparse, os, shutil, subprocess, re, tempfile, tomllib
from prepare_autojs_library import prepare, PIN

BC_VERSION = '1.78'
BC_DEPENDENCIES = (
    ('bcprov-jdk15to18', 'bcprov-jdk18on'),
    ('bcpkix-jdk15to18', 'bcpkix-jdk18on'),
    ('bcutil-jdk15to18', 'bcutil-jdk18on'),
)


def transform_bouncycastle_dependencies(autojs_root: Path, host_app_text: str) -> str:
    parser = autojs_root / 'modules/apk-parser/build.gradle.kts'
    if not parser.is_file():
        raise ValueError('Missing AutoJs apk-parser build.gradle.kts')
    parser_text = parser.read_text()
    old_parser = '''    implementation(libs.bcprov.jdk15on)
    implementation(libs.bcpkix.jdk15on)'''
    new_parser = '''    implementation("org.bouncycastle:bcprov-jdk18on:1.78")
    implementation("org.bouncycastle:bcpkix-jdk18on:1.78")'''
    if 'bcprov-jdk18on:1.78' in parser_text or 'bcpkix-jdk18on:1.78' in parser_text:
        raise ValueError('AutoJs apk-parser BouncyCastle strategy already applied')
    if parser_text.count(old_parser) != 1:
        raise ValueError('Missing or ambiguous apk-parser BouncyCastle anchors')
    transformed_parser = parser_text.replace(old_parser, new_parser, 1)

    marker = '    configurations.all {\n'
    if host_app_text.count(marker) != 1:
        raise ValueError('Missing or ambiguous host configuration strategy anchor')
    if 'bcutil-jdk15to18' in host_app_text:
        raise ValueError('Host BouncyCastle strategy already applied')
    host_block = '''    configurations.all {\n        exclude(group = "org.bouncycastle", module = "bcprov-jdk15to18")\n        exclude(group = "org.bouncycastle", module = "bcpkix-jdk15to18")\n        exclude(group = "org.bouncycastle", module = "bcutil-jdk15to18")\n    }\n\n    // Use one JDK 18 BouncyCastle family for AutoJs apk-parser and PDFBox.\n    implementation("org.bouncycastle:bcpkix-jdk18on:1.78")\n    implementation("org.bouncycastle:bcutil-jdk18on:1.78")'''
    start = host_app_text.index(marker)
    end = host_app_text.index('\n\n', start)
    original_block = host_app_text[start:end]
    if 'bcprov-jdk15to18' not in original_block:
        raise ValueError('Missing existing host BouncyCastle exclusion')
    transformed_host = host_app_text[:start] + host_block + host_app_text[end:]
    parser.write_text(transformed_parser)
    return transformed_host


def align_catalog(text: str, app_text: str) -> str:

    catalog = tomllib.loads(text)
    dep = catalog.get("libraries", {}).get("desugar-jdk", {})
    if (dep.get("group"), dep.get("name"), dep.get("version")) != (
        "com.android.tools", "desugar_jdk_libs", {"ref": "desugar"}):
        raise ValueError("Unexpected desugar catalog reference")
    if len(re.findall(r"^\s*coreLibraryDesugaring\(libs\.desugar\.jdk\)\s*$", app_text, re.M)) != 1:
        raise ValueError("Missing or ambiguous host desugar dependency")
    version = catalog.get("versions", {}).get("desugar")
    if version not in ("2.0.4", "2.1.5"):
        raise ValueError("Unexpected desugar version: " + str(version))
    section = re.search(r"^\s*\[versions\][^\n]*\n(?P<body>.*?)(?=^\s*\[|\Z)", text, re.M | re.S)
    if section is None:
        raise ValueError("Missing versions section")
    body, count = re.subn(r'^(\s*desugar\s*=\s*)"[^" ]+"', r'\g<1>"2.1.5"', section['body'], flags=re.M)
    if count != 1:
        raise ValueError("Ambiguous desugar version anchor")
    result = text[:section.start("body")] + body + text[section.end("body"): ]
    expected = tomllib.loads(text)
    expected["versions"]["desugar"] = "2.1.5"
    if tomllib.loads(result) != expected:
        raise ValueError("Unexpected catalog changes")
    return result

def main(host, autojs):
    host, autojs = host.resolve(), autojs.resolve()
    actual = subprocess.check_output(['git', '-C', str(autojs), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != PIN:
        raise ValueError('Unexpected AutoJs revision: ' + actual)
    out = host / 'autojs-engine'
    if out.exists():
        raise ValueError('Refusing to overwrite engine build')
    catalog_path = host / "gradle/libs.versions.toml"
    if not catalog_path.is_file():
        raise ValueError("Missing host libs.versions.toml")
    app = host / "app/build.gradle.kts"
    if not app.is_file():
        raise ValueError("Missing host app/build.gradle.kts")
    settings = host / "settings.gradle.kts"
    if not settings.is_file():
        raise ValueError("Missing host settings.gradle.kts")
    app_text = app.read_text()
    settings_text = settings.read_text()
    aligned_catalog = align_catalog(catalog_path.read_text(), app_text)
    agp = tomllib.loads(aligned_catalog)["versions"]["agp"]
    marker = "dependencies {"
    if app_text.count(marker) != 1:
        raise ValueError("Missing or ambiguous dependencies anchor in app/build.gradle.kts")
    if 'includeBuild("autojs-engine")' in settings_text or 'org.agentfusion:autojs-engine' in app_text:
        raise ValueError("Engine already registered")
    upstream_version_file = autojs / "version.properties"
    if not upstream_version_file.is_file():
        raise ValueError("Missing upstream version.properties")
    if len(re.findall(r"^OVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=.*$", upstream_version_file.read_text(), re.M)) != 1:
        raise ValueError("Missing or ambiguous upstream AGP override in version.properties")

    settings_result = settings_text + '''
// Source-built Library, packaged into the host APK.
includeBuild("autojs-engine") {
    dependencySubstitution {
        substitute(module("org.agentfusion:autojs-engine")).using(project(":app"))
    }
}
'''
    composite_host_app = app_text.replace(
        marker, marker + '\n    implementation("org.agentfusion:autojs-engine:1.0")', 1
    )
    staging = Path(tempfile.mkdtemp(prefix='.autojs-engine-', dir=host))
    try:
        shutil.rmtree(staging)
        shutil.copytree(autojs, staging, ignore=shutil.ignore_patterns('.git', '.gradle', '__pycache__'))
        transformed_host_app = transform_bouncycastle_dependencies(staging, app_text)
        composite_host_app = transformed_host_app.replace(
            marker, marker + '\n    implementation("org.agentfusion:autojs-engine:1.0")', 1
        )
        # A source package is literally org/autojs/build: never exclude that name.
        for source in (autojs / 'build-logic').rglob('*.kt'):
            copied = staging / source.relative_to(autojs)
            if not copied.is_file() or copied.read_bytes() != source.read_bytes():
                raise ValueError('Build plugin source missing or changed: ' + str(source))
        version_file = staging / 'version.properties'
        versions, count = re.subn(r'^OVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=.*$',
            'OVERRIDDEN_ANDROID_GRADLE_PLUGIN_VERSION=' + agp,
            version_file.read_text(), flags=re.M)
        if count != 1:
            raise ValueError('Missing or ambiguous upstream AGP override')
        version_file.write_text(versions)
        prepare(staging)
        os.replace(staging, out)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    catalog_path.write_text(aligned_catalog)
    settings.write_text(settings_result)
    app.write_text(composite_host_app)
    print('AUTOJS_COMPOSITE_LIBRARY_STAGED', PIN)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('host', type=Path)
    p.add_argument('autojs', type=Path)
    a = p.parse_args()
    main(a.host, a.autojs)
