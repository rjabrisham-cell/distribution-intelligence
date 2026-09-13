"""Run on the Windows host only, after a verified backup and successful migration.

Exclusive output creation protects against accidental regeneration. A failure
preserves the file for explicit operator recovery; never automatically replace it.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
from app.core.demo_code_format import ALPHABET, access_hash


def main():
    target = Path(r'D:\DIP_Secrets\DIP_demo_access_codes.txt')
    if target.exists():
        raise RuntimeError('Code file already exists; regeneration refused')
    target.parent.mkdir(parents=True, exist_ok=True)
    alphabet = ALPHABET
    codes = set()
    while len(codes) < 1000:
        codes.add(''.join(secrets.choice(alphabet) for _ in range(8)))
    with target.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(sorted(codes))+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    hashes = [access_hash(c) for c in codes]
    result = subprocess.run(['docker','exec','-i','distribution_backend','python','-m','app.services.demo_code_provision'], input=json.dumps(hashes), text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Provisioning failed; preserve existing file; no automatic retry')
    print('Registered: 1000; file: '+str(target))


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        # Only fixed operational messages; never print subprocess diagnostics.
        print('Provisioning stopped; no automatic overwrite or retry')
        raise SystemExit(1) from None
