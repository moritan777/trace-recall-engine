#!/usr/bin/env python3
"""Build the self-contained AIKanojyo Trace Memory integration package."""
from __future__ import annotations
import datetime as dt, json, os, re, shutil, subprocess, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/'integration_packages'/'aikanojyo_trace_memory'
SNAP=PKG/'source_snapshots'
DIST=ROOT/'dist'
ZIP=DIST/'AIKanojyo_Trace_Memory_Integration_Package_v1.zip'
ZIP_ROOT='AIKanojyo_Trace_Memory_Integration_Package_v1'
DOCS=[
'README.md','COPY_TO_AIKANOJYO_CODEX.md','00_EXECUTIVE_SUMMARY.md','01_ARCHITECTURE.md','02_DATA_MODEL.md','03_EXTRACTION_PIPELINE.md','04_RECALL_PIPELINE.md','05_WORKING_MEMORY_AND_PROMPT.md','06_SHADOW_MODE_PLAN.md','07_MIGRATION_AND_STORAGE_PLAN.md','08_PORTING_MAP_PYTHON_TO_CSHARP.md','09_VALIDATION_PLAN.md','10_KNOWN_LIMITATIONS.md','11_DO_NOT_PORT.md','12_IMPLEMENTATION_ORDER.md','13_CODE_REFERENCE_INDEX.md','14_DECISION_LOG.md','15_ACCEPTANCE_CRITERIA.md']
SNAPS={
'extractor_contract.py.txt':('src/trace_recall/extractors/base.py',None,'Extractor contract, normalization, dedupe, JSON helper.'),
'local_rule_extractor.py.txt':('src/trace_recall/extractors/local_rule.py',None,'Deterministic local-rule extraction implementation.'),
'japanese_trace_tokenizer.py.txt':('src/trace_recall/extractors/japanese_trace_tokenizer.py',None,'Japanese trace tokenizer primary and diagnostic alternate spans.'),
'candidate_span_generator.py.txt':('src/trace_recall/extractors/candidate_span_generator.py',None,'Diagnostic candidate span generation.'),
'participant_reference.py.txt':('src/threaded_concept_memory_probe.py',(717,765),'Participant reference normalization only.'),
'trace_store_schema.sql.txt':('src/threaded_concept_memory_probe.py',(281,716),'SQLite store schema, repository boundary, vocabulary cache, fatigue exposure storage.'),
'recall_core.py.txt':('src/threaded_concept_memory_probe.py',(767,1007),'Raw activation core from entry words through activated words/threads.'),
'gate_and_fatigue.py.txt':('src/threaded_concept_memory_probe.py',(1009,1234),'ActivationGate, fatigue suppression, ThreadGroup grouping.'),
'working_memory_builder.py.txt':('src/threaded_concept_memory_probe.py',(145,279),'Working-memory dataclasses and gated DTOs.'),
'prompt_formatter.py.txt':('src/threaded_concept_memory_probe.py',(1266,1398),'Prompt formatter views and response prompt construction.'),
'diagnostics_contracts.py.txt':('src/threaded_concept_memory_probe.py',(1399,1468),'Console diagnostics for raw activation, gate, fatigue, and WM candidate.')
}
def commit(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def now(): return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def read_range(path,rng):
    lines=(ROOT/path).read_text(encoding='utf-8').splitlines()
    if rng is None: return '\n'.join(lines)+'\n', f'1-{len(lines)}'
    a,b=rng; return '\n'.join(lines[a-1:b])+'\n', f'{a}-{b}'
def snapshot():
    SNAP.mkdir(parents=True,exist_ok=True); c=commit(); t=now()
    for out,(src,rng,purpose) in SNAPS.items():
        body,lr=read_range(Path(src),rng)
        header=f'''SOURCE SNAPSHOT
Repository: Threaded_Concept_Memory_Probe
Commit: {c}
Original Path: {src}
Original Line Range: {lr}
Generated At: {t}
Source Language: Python
Purpose: {purpose}
Do not edit this snapshot as source of truth.

'''
        (SNAP/out).write_text(header+body,encoding='utf-8')
def manifest():
    data={"package_name":"AIKanojyo Trace Memory Integration Package","package_version":"1.0.0","source_repository":"Threaded_Concept_Memory_Probe","source_commit":commit(),"generated_at_utc":now(),"status":"experimental","target":"AIKanojyo","default_integration_mode":"shadow","production_default_enabled":False,"documents":DOCS,"source_snapshots":sorted(SNAPS),"verified_components":["Word/Thread/word_threads schema","count-mode independent threads","raw activation Word->Thread->Word","ActivationGate bounds","conversation exposure fatigue","threadgroup prompt view","recall-state prompt view","edge prompt view"],"experimental_components":["LocalRuleTraceExtractor","JapaneseTraceTokenizer","CandidateSpanGenerator diagnostics","mixed-script promotion when explicitly enabled"],"not_for_porting":["Oracle Evaluation","Oracle Replay","Core Benchmark runner","Generalization fixture","Holdout fixture","Sensitivity runner","CSV report generator","Markdown benchmark generator","Python CLI","Expected Word labels","Replay Strategy","Candidate Oracle","Research Logger full implementation"],"known_limitations":["Generalization performance drops","not a general Japanese segmenter","participant references are incomplete","negation/correction/tense are not fully modeled","mixed-script promotion has limited dataset-level gain","terminal-boundary candidates are diagnostic only","word traces can reconstruct meaning incorrectly","not proven superior to existing AIKanojyo memory","not validated in AIKanojyo","500T fixture is synthetic","not proven in real lover-style conversations"]}
    (PKG/'package_manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def validate():
    missing=[d for d in DOCS if not (PKG/d).exists()]+[f'source_snapshots/{s}' for s in SNAPS if not (SNAP/s).exists()]
    if missing: raise SystemExit('missing: '+', '.join(missing))
    json.loads((PKG/'package_manifest.json').read_text(encoding='utf-8'))
    bad=[]
    for p in PKG.rglob('*'):
        if p.is_file() and re.search(r'(sk-[A-Za-z0-9]{20,}|BEGIN PRIVATE KEY)',p.read_text(encoding='utf-8',errors='ignore'),re.I): bad.append(str(p))
        if p.suffix in {'.db','.sqlite','.sqlite3'} or '__pycache__' in p.parts or p.name=='.git': bad.append(str(p))
    if bad: raise SystemExit('forbidden: '+', '.join(bad))
def zipit():
    DIST.mkdir(exist_ok=True)
    if ZIP.exists(): ZIP.unlink()
    with zipfile.ZipFile(ZIP,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PKG.rglob('*')):
            if p.is_file(): z.write(p, Path(ZIP_ROOT)/p.relative_to(PKG))
    with zipfile.ZipFile(ZIP) as z:
        bad=[n for n in z.namelist() if any(x in n for x in ['.git','__pycache__']) or n.endswith(('.db','.sqlite','.sqlite3'))]
        if bad: raise SystemExit('bad zip: '+', '.join(bad))
def main(): snapshot(); manifest(); validate(); zipit(); print(ZIP)
if __name__=='__main__': main()
