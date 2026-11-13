"""Verify preserved repository files, evidence hashes, input-only requests and pending forms."""
import json,pathlib,hashlib
import run,package

def main():
 for name,digest in json.loads((run.OUT/'preservation-baseline.json').read_text()).items():
  assert run.sha((run.ROOT/name).read_bytes())==digest,name
 package.main()
 forms=json.loads((run.OUT/'human-response-forms.json').read_text())
 for f in forms:
  assert f['user_final_judgment'] is None and f['approve_for_development_gold'] is None and f['counterargument_response'] is None
 audit=json.loads((run.OUT/'temporary-audit.json').read_text())['preserved_failure']
 assert run.sha((run.ROOT/audit['path']).read_bytes())==audit['sha256']
 manifest=run.OUT/'artifact-manifest.json'
 if manifest.exists():
  for name,digest in json.loads(manifest.read_text()).items():assert run.sha((run.OUT/name).read_bytes())==digest,name
 print('Preserved tracked files, prior failure, request isolation, hashes, quotes and pending human fields: PASS')
if __name__=='__main__':main()
