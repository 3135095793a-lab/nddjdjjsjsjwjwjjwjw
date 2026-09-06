"""Fetch or read exact pinned source and verify bridge patch; NOT Android compilation."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
from patch_autojs_bridge import transform
PIN = 'ed3eb10e88db5a8425fd94bdddefa4176e5e1c94'
SOURCE_PATH = 'app/src/main/java/org/autojs/autojs/core/accessibility/AccessibilityBridgeImpl.java'
EXPECTED = 'e19eaaf136a1367a89923621053b65aed890e557ae2b1d52ca9766accafb8079'

def verify(data):
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED:
        raise ValueError('Pinned source hash mismatch')
    source = data.decode('utf-8')
    patched = transform(source)
    for anchor in ('mA11yTool.ensureService();', 'AccessibilityService.Companion.getInstance()',
                   'mA11yTool.stopService(true);'):
        if source.count(anchor) != 1 or patched.count(anchor) != 1:
            raise ValueError('Service behavior anchor mismatch')
    return patched, {'stage': 'source-transform-only; NOT Android compiled',
                     'upstreamCommit': PIN, 'sourcePath': SOURCE_PATH,
                     'sourceSha256': digest,
                     'patchedSha256': hashlib.sha256(patched.encode()).hexdigest()}

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh output directory')
    if args.source:
        data = args.source.read_bytes()
    else:
        url = 'https://api.github.com/repos/SuperMonster003/AutoJs6/contents/' + SOURCE_PATH + '?ref=' + PIN
        with urlopen(Request(url, headers={'User-Agent': 'AgentFusion-source-verifier'}), timeout=40) as response:
            payload = json.load(response)
        if payload.get('encoding') != 'base64':
            raise ValueError('Unexpected API encoding')
        data = base64.b64decode(payload['content'])
    patched, report = verify(data)
    args.output.mkdir(parents=True)
    (args.output / 'AccessibilityBridgeImpl.java').write_text(patched)
    (args.output / 'verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
