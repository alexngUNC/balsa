#!/usr/bin/env python3
"""Small sequential boundary matrix with separate signedness per operand."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('BALSA_COMPARE_TEST_DIR') or tempfile.mkdtemp(prefix='balsa-mixed-boundaries-')).resolve()
print('Boundary artifacts:', ROOT, flush=True)
if '--results-only' in sys.argv:
    saved = json.loads((ROOT / 'results.json').read_text())
    failed = sum(row['verdict'] == 'FAIL' for row in saved)
    print('Saved matrix has', failed, 'failing configurations.')
    raise SystemExit(1 if failed else 0)
if hasattr(os, 'sched_getaffinity'):
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
HOME = Path(subprocess.check_output(['balsa-config', '-d'], text=True).strip())
source = (SOURCE / 'compare8.balsa').read_text()
output_root = ROOT
requested_case = os.environ.get('MIXED_CASE_FILTER')
results = []

def execute(arguments, directory, log_name):
    log = directory / log_name
    with log.open('w') as output:
        process = subprocess.run(arguments, cwd=str(directory), stdout=output,
                                 stderr=subprocess.STDOUT, timeout=90)
    (directory / (log_name + '.status')).write_text(str(process.returncode) + '\n')
    return process.returncode, log.read_text()

for aw, bw in ((8, 8), (4, 8), (8, 4)):
    for a_signed in (False, True):
        b_signed = a_signed if os.environ.get('MIXED_SIGN_MODE') == 'controls' else not a_signed
        label = ('s' if a_signed else 'u') + str(aw) + '_' + ('s' if b_signed else 'u') + str(bw)
        if requested_case and label != requested_case:
            continue
        data = []
        a_values = sorted({0, 1, (1 << (aw-1))-1, 1 << (aw-1), (1 << (aw-1))+1, (1 << aw)-2, (1 << aw)-1})
        b_values = sorted({0, 1, (1 << (bw-1))-1, 1 << (bw-1), (1 << (bw-1))+1, (1 << bw)-2, (1 << bw)-1})
        for a in a_values:
            for b in b_values:
                av = a - (1 << aw) if a_signed and a >= (1 << (aw-1)) else a
                bv = b - (1 << bw) if b_signed and b >= (1 << (bw-1)) else b
                expected = int(av < bv) | (int(av <= bv) << 1) | (int(av > bv) << 2) | (int(av >= bv) << 3)
                data.append(dict(index=len(data)+1, a=av, b=bv, packed=(b << aw) | a, expected=expected))
        for encoding in ('bundled-data', 'dual-rail'):
            directory = output_root / 'runs' / encoding / label
            directory.mkdir(parents=True, exist_ok=True)
            a_type = str(aw) + (' signed bits' if a_signed else ' bits')
            b_type = str(bw) + (' signed bits' if b_signed else ' bits')
            design = source.replace('a : Byte; b : Byte', 'a : ' + a_type + '; b : ' + b_type)
            (directory / 'compare8.balsa').write_text(design)
            (directory / 'vectors.json').write_text(json.dumps(data, indent=2) + '\n')
            (directory / 'vectors.hex').write_text(''.join(format((v['packed'] << 4) | v['expected'], 'x') + '\n' for v in data))
            lines = ['import [compare8]', 'import [balsa.sim.sim]', 'procedure balsa_top is',
                     'channel commands : Pair', 'channel results : Flags', 'variable actual : Flags',
                     'variable failed,stopped : bit', 'begin compare8(commands,results) || begin failed := 0;']
            for v in data:
                lines.append('commands <- Pair {' + str(v['a']) + ', ' + str(v['b']) + '}; results -> actual; if (actual as 4 bits) /= ' + str(v['expected']) + ' then failed := 1 end;')
            lines.append('if not failed then stopped := BalsaSimulationStop () else halt end end end')
            (directory / 'test.balsa').write_text('\n'.join(lines) + '\n')
            for name in ('compare8', 'test'):
                status, log = execute(['balsa-c', '-b', name + '.balsa'], directory, name + '-compile.log')
                assert status == 0, log[-1500:]
            status, log = execute(['breeze-sim', '--stop-at-time=1000000', 'test'], directory, 'breeze.log')
            assert status == 0 and 'BalsaSimulationStop called' in log, log[-1500:]
            technology = 'example/' + ('four_b_rb' if encoding == 'bundled-data' else 'dual_b')
            status, log = execute(['balsa-netlist', '--simulation-initialise', '-X', technology, '-n', 'verilog', 'compare8.breeze'], directory, 'generation.log')
            assert status == 0, log[-1500:]
            text = (directory / 'compare8.v').read_text().replace('module Balsa_compare8 (', 'module RawCompare (')
            (directory / 'netlist.v').write_text(text)
            wrapper = 'module CompareAdapter(input activate,initialise,output ir,input ia,input ['+str(aw+bw-1)+':0] id,output orq,input oa,output [3:0] od);\n'
            if encoding == 'bundled-data':
                wrapper += 'RawCompare raw(.activate_0r(activate),.activate_0a(),.initialise(initialise),.command_0r(ir),.command_0a(ia),.command_0d(id),.result_0r(orq),.result_0a(oa),.result_0d(od));\n'
            else:
                wrapper += 'wire ['+str(aw+bw-1)+':0] a0=ia?~id:0,a1=ia?id:0; wire [3:0] r0,r1; reg valid=0;reg [3:0] value=0;assign orq=valid;assign od=value;\n'
                wrapper += 'RawCompare raw(.activate_0r(activate),.activate_0a(),.initialise(initialise),.command_0r(ir),.command_0a0d(a0),.command_0a1d(a1),.result_0r0d(r0),.result_0r1d(r1),.result_0a(oa));\n'
                wrapper += 'always @(r0 or r1) begin if(activate && ((r0&r1)!==0 || (^r0)===1\'bx || (^r1)===1\'bx)) $fatal(1,"FAIL: illegal rails"); if((r0|r1)===0) valid=0;else if((&(r0^r1))===1 && !valid) begin value=r1;valid=1;end end\n'
            (directory / 'adapter.sv').write_text(wrapper + 'endmodule\n')
            shutil.copy2(HOME / 'share/tech/example/example-cells.v', directory / 'cells.v')
            arguments = [os.environ.get('XRUN','xrun'), '-64bit', '-sv', '-top', 'mixed_tb',
                         '+define+balsa_simulate', '+define+balsa_init_time=20', '+define+AW='+str(aw), '+define+BW='+str(bw),
                         'cells.v', 'netlist.v', 'adapter.sv', str(SOURCE/'boundary_tb.sv'),
                         '+VECTORS='+str(directory/'vectors.hex'), '+N='+str(len(data))]
            status, log = execute(arguments, directory, 'simulation.log')
            failures = re.findall(r'^MISMATCH (\d+) actual=([01xz]+) expected=([01]+)$', log, re.M)
            checked = re.search(r'^CHECKED (\d+) FAILURES (\d+)$', log, re.M)
            assert checked and int(checked[1]) == len(data), log[-2000:]
            verdict = 'PASS' if status == 0 and not failures and 'PASS: mixed-sign boundary comparisons' in log else 'FAIL'
            results.append(dict(case=label, encoding=encoding, verdict=verdict, pairs=len(data), failures=len(failures),
                                first_failures=[dict(vector=data[int(i)-1], actual=a, expected=e) for i,a,e in failures[:3]],
                                log=str((directory/'simulation.log').relative_to(ROOT)), exit_code=status,
                                log_sha256=hashlib.sha256((directory/'simulation.log').read_bytes()).hexdigest()))
            (output_root/'results.json').write_text(json.dumps(results, indent=2)+'\n')
            print(encoding, label, verdict, 'pairs='+str(len(data)), 'failures='+str(len(failures)), flush=True)

if not results:
    raise SystemExit('No matching boundary configurations were selected')

# Keep a failing matrix visible to shell scripts after all configurations finish.
raise SystemExit(1 if any(row['verdict'] == 'FAIL' for row in results) else 0)
