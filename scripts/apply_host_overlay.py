"""Apply the initial host overlay, not a completed AutoJs6 integration.
Requires a clean checkout of pinned Operit. No downloads or credentials.
"""
import argparse
import pathlib
import subprocess
import shutil

PIN = 'f323d6c50fa661837fad06d4618462861779b562'

def transform(text):
    replacements = {
        'applicationId = "com.ai.assistance.operit"': 'applicationId = "com.agentfusion.mobile"',
        'resValue("string", "app_name", "Operit Debug")': 'resValue("string", "app_name", "AgentFusion Dev")',
        'resValue("string", "app_name", "Operit Clone")': 'resValue("string", "app_name", "AgentFusion Clone Dev")',
    }
    for old in replacements:
        if text.count(old) != 1:
            raise ValueError('Unexpected upstream anchor: ' + old)
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def apply(root, project):
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if head != PIN:
        raise ValueError('Upstream SHA mismatch')
    status = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True)
    if status.strip():
        raise ValueError('Apply only to a clean upstream checkout')
    gradle = root / 'app/build.gradle.kts'
    text = transform(gradle.read_text())
    sources = [project / 'fusion-core/src/com/agentfusion/core' / name
               for name in ('TaskRuntime.java', 'TaskProgress.java')]
    target_dir = root / 'app/src/main/java/com/agentfusion/core'
    if any(not source.is_file() or (target_dir / source.name).exists() for source in sources):
        raise ValueError('Missing source or target collision')
    target_dir.mkdir(parents=True, exist_ok=True)
    for source in sources:
        shutil.copyfile(source, target_dir / source.name)
    ui_source = project / 'fusion-ui/src/main/kotlin/com/agentfusion/mobile/tasks/TaskProgressPanel.kt'
    ui_target = root / 'app/src/main/java/com/agentfusion/mobile/tasks/TaskProgressPanel.kt'
    if not ui_source.is_file() or ui_target.exists():
        raise ValueError('Missing UI source or target collision')
    ui_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ui_source, ui_target)
    gradle.write_text(text)
    print('Host overlay applied: com.agentfusion.mobile.debug; core source included but not invoked.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('upstream', type=pathlib.Path)
    args = parser.parse_args()
    apply(args.upstream.resolve(), pathlib.Path(__file__).resolve().parents[1])
