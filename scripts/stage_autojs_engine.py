"""Stage pinned AutoJs6 sources as an isolated host module input.
The CI workflow copies this staged tree into :autojs-engine before Gradle.
"""
from pathlib import Path
import argparse, hashlib, json, shutil
PIN = "ed3eb10e88db5a8425fd94bdddefa4176e5e1c94"
SKIP = {"build", ".gradle", ".git"}
def copy_tree(src, dst):
    for item in src.iterdir():
        if item.name in SKIP: continue
        target = dst / item.name
        if item.is_dir(): shutil.copytree(item, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*SKIP))
        elif item.is_file(): target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(item, target)
def stage(source, output):
    if output.exists(): shutil.rmtree(output)
    output.mkdir(parents=True)
    app = source / "app"
    for name in ("src", "libs"):
        copy_tree(app / name, output / name)
    for name in ("gradle", "build-logic", "gradle.properties", "gradlew", "gradlew.bat", "settings.gradle.kts", "build.gradle.kts", "version.properties"):
        item = source / name
        if item.is_dir(): copy_tree(item, output / item.name)
        elif item.exists(): shutil.copy2(item, output / item.name)
    marker = {"stage":"autojs-engine-source", "upstreamCommit":PIN, "files":sum(1 for p in output.rglob('*') if p.is_file())}
    (output / "fusion-engine-source.json").write_text(json.dumps(marker, indent=2))
    print(json.dumps(marker))
if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("source", type=Path); p.add_argument("output", type=Path); a=p.parse_args(); stage(a.source, a.output)
