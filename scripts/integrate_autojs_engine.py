"""Create the host-side :autojs-engine module from the pinned AutoJs6 app.
This is intentionally deterministic and keeps the engine namespace separate.
"""
from pathlib import Path
import argparse, shutil
PIN='ed3eb10e88db5a8425fd94bdddefa4176e5e1c94'
def main(host, autojs):
    out=host/'autojs-engine'
    if out.exists(): shutil.rmtree(out)
    shutil.copytree(autojs/'app', out, ignore=shutil.ignore_patterns('build','.gradle'))
    g=out/'build.gradle.kts'; s=g.read_text()
    s=s.replace('id("com.android.application")','id("com.android.library")')
    s=s.replace('    id("org.autojs.build.signs")\n','')
    s=s.replace('utils.registerTemplateApkCopy(project)','')
    s=s.replace('applicationId = globalApplicationId','')
    s=s.replace('applicationId globalApplicationId','')
    s=s.replace('namespace = globalApplicationId','namespace = "org.autojs.autojs6"')
    g.write_text(s)
    manifest=out/'src/main/AndroidManifest.xml'
    if manifest.exists():
        text=manifest.read_text()
        text=text.replace('package="org.autojs.autojs6"','')
        manifest.write_text(text)
    settings=host/'settings.gradle.kts'; text=settings.read_text()
    if 'include(":autojs-engine")' not in text: text += '\ninclude(":autojs-engine")\n'
    settings.write_text(text)
    app=host/'app/build.gradle.kts'; text=app.read_text()
    if 'implementation(project(":autojs-engine"))' not in text:
        marker='dependencies {'
        text=text.replace(marker, marker+'\n    implementation(project(":autojs-engine"))',1)
    app.write_text(text)
    print('AUTOJS_ENGINE_STAGED', PIN, sum(1 for p in out.rglob('*') if p.is_file()))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('host',type=Path);p.add_argument('autojs',type=Path);a=p.parse_args();main(a.host,a.autojs)