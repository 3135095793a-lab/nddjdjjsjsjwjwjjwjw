"""Verify actual APK manifest and signature; not a runtime compatibility test."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

root = Path(sys.argv[1])
apks = sorted((root / 'app/build/outputs/apk/debug').rglob('*.apk'))
if not apks:
    raise SystemExit('No debug APK produced')
tools = Path(os.environ['ANDROID_HOME']) / 'build-tools/35.0.0'
records = []
for apk in apks:
    badging = subprocess.check_output([str(tools / 'aapt'), 'dump', 'badging', str(apk)], text=True)
    match = re.search(r"^package: name='([^']+)'", badging, re.M)
    if not match or match.group(1) != 'com.agentfusion.mobile.debug':
        raise SystemExit('Wrong APK applicationId: ' + str(apk))
    subprocess.run([str(tools / 'apksigner'), 'verify', str(apk)], check=True)
    digest = hashlib.sha256()
    with apk.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    records.append({'file': apk.name, 'applicationId': match.group(1), 'sha256': digest.hexdigest(), 'bytes': apk.stat().st_size})
report = root / 'build-diagnostics/host-apk-check.json'
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps({'stage': 'host-only; no AutoJs6 integration', 'apks': records}, indent=2))
print(report.read_text())