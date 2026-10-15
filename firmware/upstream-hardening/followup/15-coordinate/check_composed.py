#!/usr/bin/env python3
"""Pin and check the reviewed coordinate + query12 + flow16 composition.
No enumeration, building, hardware operations, or source writes.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'firmware/upstream-hardening/build/final-33a'
CAND=ROOT/'artifacts/private/astra-root-domain-flow-measure'
CHANGED={
 'src/abs_encoder.c':'0fa218deffe16bdf1ad08c6cf06f34db034742c60f98d27c407960e94cef17c2',
 'src/abs_encoder.h':'222b4fd167e64def7a9421dfe452c2bddd071c6cd2116c7914c70fab611c31f7',
 'src/emount.c':'f76801a1bd5cf625e5c34af06eb65baf7564bcbe9a0f36c62a44102df40c734b',
 'src/main.c':'bcb017f2f0741d33c9a4514f5640f35451f65a2e8c53b504d4075e951153888b',
}
manifest=json.loads((BASE/'manifest.json').read_text())
assert len(manifest['sources'])==46
for name,digest in manifest['sources'].items():
 assert hashlib.sha256((BASE/name).read_bytes()).hexdigest()==digest,name
 assert hashlib.sha256((CAND/name).read_bytes()).hexdigest()==CHANGED.get(name,digest),name

def function(source,signature):
 start=source.index(signature+'\n{')
 end=source.index('\n}',start)+2
 return source[start:end]
base=(BASE/'src/main.c').read_text()
cand=(CAND/'src/main.c').read_text()
worker_signature='static void focus_answer_queries(void)'
oldworker=function(base,worker_signature)
newworker=function(cand,worker_signature)
assert 'for (uint8_t budget = 0; budget < EM_QUERY_Q; budget++)' in newworker
assert 'uint16_t operand, value;' in newworker
assert newworker.count('motor_is_inhibited()')==2
assert 'uint32_t session = em_session_generation();' in newworker
assert 'session == em_session_generation()' in newworker
assert 'value = focus_distance_code(focus_em06_to_counts(operand),' in newworker
assert 'value = focus_counts_to_em06(focus_counts_for_code(operand,' in newworker
for forbidden in ('abs_encoder_','focus_pred_','focus_run(','focus_exec(','servo_', 'millis('):
 assert forbidden not in newworker,forbidden
oldpump=function(base,'static void pump(int32_t pos)')
newpump=function(cand,'static void pump(int32_t pos)')
addition='''\t/* Operand-only optical conversions need no encoder origin. Keep the
\t * bounded worker outside g_homed so homing can answer them too. */
\tfocus_answer_queries();
'''
assert newpump.replace(addition,'')==oldpump
# Entire main other than the reviewed worker/pump additions is byte-identical.
assert cand.replace(newworker,oldworker).replace(newpump,oldpump)==base
em=(CAND/'src/emount.c').read_text()
old='if (em_shutdown_requested() || !g_query_n) {'
new='''/* The only answer producer is the foreground query worker. Its pure
\t * conversion cannot consume another answer slot before publication. */
\tif (em_shutdown_requested() || !g_query_n || g_ans_n >= EM_QUERY_Q) {'''
assert em.replace(new,old)==(BASE/'src/emount.c').read_text()
enc=(CAND/'src/abs_encoder.c').read_text()
old='''\t/* Never wrap the software coordinate into an unrelated target. */
\tif ((d > 0 && g_track > INT32_MAX - d) ||
\t    (d < 0 && g_track < INT32_MIN - d)) {'''
new='''\t/* Check capacity before addition. Both bounds are representable for
\t * every 14-bit shortest difference, even if g_track is corrupted. */
\tif (g_track > ENC_TRACK_LIMIT - d ||
\t    g_track < -ENC_TRACK_LIMIT - d) {'''
assert enc.replace(new,old)==(BASE/'src/abs_encoder.c').read_text()
assert '#define ENC_TRACK_LIMIT 65536' in (CAND/'src/abs_encoder.h').read_text()
print(json.dumps({'reviewed_composition':str(CAND.relative_to(ROOT)),
 'frozen_sources_verified':46,'unchanged_source_files':42,
 'changed_source_sha256':CHANGED,
 'main_numeric_functions':'unchanged byte-for-byte',
 'servo_predictor_maps_distance_packets':'unchanged byte-for-byte',
 'worker':'same bounded pure conversions, no coordinate/target/predictor mutation',
 'result':'PASS: prior numeric invariant proofs apply to exact composition'},indent=2))
