"""Convert pinned AutoJs app to an isolated library compile probe.
No original Application/service/provider is registered. Not host-integrated.
Run only in a disposable copy; retains upstream dependencies for first diagnostics.
"""
import argparse, hashlib, json
from pathlib import Path
from verify_autojs_bridge import verify
PIN = 'ed3eb10e88db5a8425fd94bdddefa4176e5e1c94'
CONFIG = '''
android {
    namespace = "org.autojs.autojs6"
    compileSdk = 36
    defaultConfig {
        minSdk = 26
        buildConfigField("int", "VERSION_CODE", "3804")
        buildConfigField("String", "VERSION_NAME", "\\\"6.7.0-fusion-probe\\\"")
        buildConfigField("String", "VERSION_DATE", "\\\"pinned-source\\\"")
        buildConfigField("String", "VSCODE_EXT_REQUIRED_VERSION", "\\\"1.0.13\\\"")
        buildConfigField("boolean", "isInrt", "false")
        buildConfigField("String", "CHANNEL", "\\\"app\\\"")
        buildConfigField("String", "APPLICATION_ID", "\\\"org.autojs.autojs6\\\"")
        javaCompileOptions.annotationProcessorOptions.arguments(mapOf(
            "resourcePackageName" to "org.autojs.autojs6",
            "androidManifestFile" to "$projectDir/src/main/AndroidManifest.xml"
        ))
    }
    sourceSets.getByName("main") {
        java.exclude("com/stardust/**")
        assets.srcDirs("src/main/assets", "src/main/assets-app")
    }
    buildFeatures { aidl = true; viewBinding = true; buildConfig = true }
    compileOptions { isCoreLibraryDesugaringEnabled = true }
    buildTypes { debug { isMinifyEnabled = false }; release { isMinifyEnabled = false } }
    lint { abortOnError = true }
}
'''
def prepare(root):
    app = root / 'app'
    marker = root / 'fusion-library-probe.json'
    if marker.exists(): raise ValueError('Already prepared')
    gradle = app / 'build.gradle.kts'
    source = gradle.read_text()
    if source.count('\nandroid {') != 1: raise ValueError('Unexpected Gradle anchor')
    prefix = source.split('\nandroid {', 1)[0]
    for old in ('id("com.android.application")', '    id("org.autojs.build.signs")\n', 'utils.registerTemplateApkCopy(project)'):
        if prefix.count(old) != 1: raise ValueError('Missing Gradle anchor: '+old)
    prefix = prefix.replace('id("com.android.application")', 'id("com.android.library")')
    prefix = prefix.replace('    id("org.autojs.build.signs")\n', '').replace('utils.registerTemplateApkCopy(project)', '')
    bridge = app / 'src/main/java/org/autojs/autojs/core/accessibility/AccessibilityBridgeImpl.java'
    patched, report = verify(bridge.read_bytes())
    log_page = app / 'src/main/java/org/autojs/autojs/ui/log/LogBottomSheet.kt'
    log_source = log_page.read_text()
    if log_source.count('AutoJs.getInstance()') != 2:
        raise ValueError('Unexpected LogBottomSheet singleton anchors')
    log_patched = log_source.replace('AutoJs.getInstance()', 'AutoJs.instance')
    # Preserve original metadata as evidence, never import upstream component registrations.
    manifest = app / 'src/main/AndroidManifest.xml'
    original = manifest.read_bytes()
    (root / 'fusion-original-manifest.xml').write_bytes(original)
    gradle.write_text(prefix + '\n' + CONFIG)
    bridge.write_text(patched)
    log_page.write_text(log_patched)
    manifest.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application /></manifest>\n')
    report.update(stage='library-compile-probe; no host integration', originalManifestSha256=hashlib.sha256(original).hexdigest())
    marker.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();prepare(a.root)
