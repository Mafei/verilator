#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
"""One independent coroutine probe plus an explicitly non-candidate generated-code diagnostic."""
from pathlib import Path
import difflib
import importlib.util
import json
import os
import re
import resource
import shutil
from datetime import datetime, timezone
C=Path(__file__).resolve().parent
E=Path('/workspace/evidence/fourstate-followup-20261009/finish-controls-v1')
D=C/'noninline-v1'
assert D.exists(), 'continue only already generated first probe'
VROOT=Path('/tmp/verilator-followup-20261009')
BIN=VROOT/'bin/verilator_bin'
SOURCE=C/'noninline_finish.sv'
spec=importlib.util.spec_from_file_location('native_helpers','/workspace/icarus-acceptance-20261008/run_acceptance_v2.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def limits():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
h.no_core_files=limits
original=E/'baseline-v2-protected-after.json'
protected=json.loads(original.read_text())
oldcases={str(p):h.sha(p) for directory in [C/'reference-v1',C/'baseline-v1',C/'baseline-v2'] for p in directory.rglob('*') if p.is_file()}
protected.update(oldcases)
protected[str(SOURCE)]=h.sha(SOURCE)
protected[str(Path(__file__))]=h.sha(__file__)
assert all(h.sha(p)==value for p,value in protected.items())
assert h.sha(BIN)=='0dec37177ade528731050dba1d170e7bd0eed8e4882c2f7e0f6371454ca2efb0'
memory=h.cg_events()
env=dict(os.environ, VERILATOR_ROOT=str(VROOT), MAKEFLAGS='VM_PARALLEL_BUILDS=0')
rows=[]
def guard():
    free=os.statvfs(C).f_bavail*os.statvfs(C).f_frsize
    used=sum(p.stat().st_size for p in D.rglob('*') if p.is_file())
    assert free>=200*1024*1024 and used<20*1024*1024,(free,used)
    assert h.cg_events()==memory,'six memory-event delta: stop before next stage'
    return {'free_bytes':free,'probe_owned_bytes':used,'min_free_bytes':200*1024*1024,'max_probe_bytes':20*1024*1024}
def stage(folder,label,argv,timeout):
    guard()
    r=h.stage(folder,label,argv,timeout,env)
    rows.append(r)
    assert type(r['native_exit']) is int and not r['timed_out']
    assert r['wait4_maxrss_KiB']<=768*1024
    guard()
    return r
expected=['OBS 9 callee_before 1','FINAL 9 1 q=0']
def check(r):
    raw=Path(r['log']).read_text()
    owned=[x for x in raw.splitlines() if re.match(r'^(OBS |FINAL |UNREACHABLE)',x)]
    return {'expected':expected,'actual':owned,'strict_passed':r['native_exit']==0 and owned==expected,
            'forbidden':[x for x in raw.splitlines() if 'UNREACHABLE' in x], 'raw_sha256':h.sha(r['log'])}
result={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':h.sha(SOURCE),'unique_additional_inputs':1,
        'compiler_sha256':h.sha(BIN),'compiler_head':'5a73c185425d2e5e7d8a3b53549175f1d5e09400',
        'compiler_is_not_fresh_fdb':True,'memory_events_before':memory,'resource_before':guard(),
        'original_cases_and_source_unchanged':None,'steps':rows,'diagnostic_is_compiler_patch':False}
h.save(E/'noninline-continuation-started.json',result)
ref=D/'reference'
for label in ['compile','run']:
    row=json.loads((ref/(label+'.finished.json')).read_text()); rows.append(row)
    assert row['native_exit']==0
result['reference']=check(rows[-1])
base=D/'baseline';obj=base/'obj'
c=json.loads((base/'compile.finished.json').read_text());rows.append(c)
assert c['native_exit']==0
result['prior_native_receipts_reused_without_rerun']=3
# Check the actual emitted callee and the caller before any manual diagnostic.
functions=[]
for p in obj.glob('*.cpp'):
    text=p.read_text()
    for m in re.finditer(r'VlCoroutine\s+([A-Za-z0-9_:]*stop_now[A-Za-z0-9_]*)\([^;]*?\)\s*\{',text):
        depth=1;end=m.end()
        while depth and end<len(text):
            depth+=(text[end]=='{')-(text[end]=='}');end+=1
        body=text[m.start():end]
        if 'VL_FINISH_MT(' in body:
            functions.append((p,m.start(),end,m.group(1),body))
assert len(functions)==1,'pragma did not form exactly one separate callee; stop rather than fake probe'
p,start,end,name,body=functions[0]
callers=[]
for q in obj.glob('*.cpp'):
    for line_no,line in enumerate(q.read_text().splitlines(),1):
        if 'co_await ' in line and name.split('::')[-1]+'(' in line:
            callers.append({'path':str(q),'line':line_no,'text':line})
assert len(callers)==1,'no unique co_await caller; diagnostic not authorized'
assert body.count('VL_FINISH_MT(')==1 and 'co_await ' in body
result['emitted_callee']={'file':str(p),'name':name,'body':body,'sha256':h.sha(p),'callers':callers}
b=stage(base,'build',['/usr/bin/make','-C',str(obj),'-f','Vt.mk','-j1','VM_PARALLEL_BUILDS=0'],60)
assert b['native_exit']==0
r=stage(base,'run',[str(obj/'Vt'),'+verilator+quiet'],10)
result['baseline']=check(r)
result['baseline']['binary_sha256']=h.sha(obj/'Vt')
assert len(list(obj.rglob('*.gch')))==0
# Copy only generated source/Makefile inputs; leave the original model untouched.
diag=D/'diagnostic-generated-only';diag.mkdir();dobj=diag/'obj';dobj.mkdir()
for q in obj.iterdir():
    if q.is_file() and q.suffix in ('.cpp','.h','.mk'):
        shutil.copy2(q,dobj/q.name)
q=dobj/p.name
old=q.read_text()
assert old==p.read_text()
match=re.search(r'VL_FINISH_MT\([^;]*\);',body)
assert match
at=start+match.end()
new=old[:at]+'\n    co_return;  // diagnostic only: not compiler/candidate output\n'+old[at:]
q.write_text(new)
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/'+p.name,tofile='diagnostic/'+p.name))
(diag/'generated-only.patch').write_text(patch)
# Generated Makefiles encode the original absolute model directory. Bind ONLY this
# diagnostic copy's output directory; compiler and SV inputs stay untouched.
for m in dobj.glob('*.mk'):
    content=m.read_text()
    m.write_text(content.replace(str(obj),str(dobj)))
result['diagnostic_modifications']={'generated_only_patch':str(diag/'generated-only.patch'),'patch_sha256':h.sha(diag/'generated-only.patch'),
                                  'only_semantic_change':'co_return after unique independent callee VL_FINISH_MT',
                                  'makefile_path_binding_only':True,'source_changed':False,'not_a_candidate':True}
b=stage(diag,'build',['/usr/bin/make','-C',str(dobj),'-f','Vt.mk','-j1','VM_PARALLEL_BUILDS=0'],60)
assert b['native_exit']==0
r=stage(diag,'run',[str(dobj/'Vt'),'+verilator+quiet'],10)
result['diagnostic']=check(r)
result['diagnostic']['binary_sha256']=h.sha(dobj/'Vt')
assert len(list(dobj.rglob('*.gch')))==0
result['original_cases_and_source_unchanged']=all(h.sha(p)==v for p,v in protected.items())
assert result['original_cases_and_source_unchanged']
result['protected_count']=len(protected)
result['memory_events_after']=h.cg_events();result['resource_after']=guard()
result['native_steps_count']=len(rows)
result['native_steps_all_int_zero']=all(type(s['native_exit']) is int and s['native_exit']==0 for s in rows)
result['gch_count']=0
result['strict_gate_exit']=0 if all(result[x]['strict_passed'] for x in ['reference','baseline','diagnostic']) else 1
h.save(E/'noninline-continuation-result.json',result)
print(json.dumps({k:result[k] for k in ['reference','baseline','diagnostic','native_steps_count','strict_gate_exit']},indent=2),flush=True)
raise SystemExit(result['strict_gate_exit'])
