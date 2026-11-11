import pathlib,subprocess,sys,json,time
root=pathlib.Path.cwd();results=[]
for directory in sorted({p.parent for p in root.rglob('test_*.py') if '.git' not in p.parts}):
 t=time.monotonic();r=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(directory),'-p','test_*.py','-v'],cwd=root,capture_output=True,text=True)
 results.append(dict(directory=str(directory.relative_to(root)),returncode=r.returncode,seconds=round(time.monotonic()-t,3),stdout=r.stdout,stderr=r.stderr));print(results[-1]['directory'],r.returncode,flush=True)
pathlib.Path(__file__).with_name('regression-results.json').write_text(json.dumps(results,indent=2))
sys.exit(any(r['returncode'] for r in results))
