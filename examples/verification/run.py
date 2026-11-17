#!/usr/bin/env python3
"""Run identical functional benches against bundled-data or dual-rail netlists."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE.parent
encoding, circuit = sys.argv[1:3]
assert encoding in ('bundled-data', 'dual-rail') and circuit in ('count10b', 'dot-product')
root = Path(os.environ.get('VERIFY_OUTPUT_ROOT', tempfile.mkdtemp(prefix='balsa-encodings-'))) / encoding / circuit
root.mkdir(parents=True, exist_ok=True)
gen = root / 'generated'
gen.mkdir(exist_ok=True)
technology = 'example/' + ('dual_b' if encoding == 'dual-rail' else 'four_b_rb')

def execute(args, cwd, log, timeout=180):
    with log.open('w') as stream:
        result = subprocess.run(args, cwd=str(cwd), stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    return result.returncode

if circuit == 'count10b':
    source = EXAMPLES / 'tutorial/count10b'
    stem, top, bench_top, inp, out, iw, ow = 'count10b', 'Balsa_updown10', 'count10b_tb', 'in__sigs', 'count', 6, 4
    bench = HERE / 'bundled-data/count10b/bench.sv'
    for name in ('count10b.balsa', 'counter_test.balsa', 'test.sh'):
        shutil.copy2(source / name, gen / name)
    pairs = re.findall(r'commands <- In_bundle\s*\{(\d+),\s*(load|count),\s*(up|down)\};\s*results -> actual;\s*if actual /= (\d+) then', (source/'counter_test.balsa').read_text())
    assert len(pairs) == 10
    (gen/'vectors.hex').write_text(''.join('{:03x}\n'.format((((int(d=='up')<<5)|(int(m=='count')<<4)|int(a))<<4)|int(e)) for a,m,d,e in pairs))
    helper = HERE/'bundled-data/count10b/expanded_vectors.py'
    subprocess.run([sys.executable, str(helper), str(gen)], check=True, stdout=subprocess.DEVNULL)
    assert execute(['sh', str(gen/'test.sh')], gen, root/'breeze.log') == 0
    scenarios = ['baseline','delayed','expanded','expanded-delayed','negative-mismatch','negative-stall']
else:
    source = EXAMPLES/'dot-product'
    stem, top, bench_top, inp, out, iw, ow = 'dot_product','Balsa_dot4','dot_product_tb','operands','result',64,18
    bench = source/'dot_product_tb.sv'
    environment = dict(os.environ, BALSA_TEST_DIR=str(gen))
    with (root/'breeze.log').open('w') as log:
        subprocess.run(['sh', str(source/'test.sh')], env=environment, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    scenarios = ['baseline','delayed','negative-mismatch','negative-stall']
assert 'BalsaSimulationStop called' in (root/'breeze.log').read_text()
assert execute(['balsa-c','-b',stem+'.balsa'], gen, root/'compile.log') == 0
assert execute(['balsa-netlist','--simulation-initialise','-X',technology,'-n','verilog',stem+'.breeze'],gen,root/'generation.log') == 0
home = Path(subprocess.check_output(['balsa-config','-d'],text=True).strip())
shutil.copy2(home/'share/tech/example/example-cells.v',gen/'example-cells.v')
netlist = gen/(stem+'.v')
files = [gen/'example-cells.v',netlist,bench]
if encoding == 'dual-rail':
    text = netlist.read_text()
    assert 'input [{}:0] {}_0a0d;'.format(iw-1,inp) in text
    netlist.write_text(text.replace('module '+top+' (','module DualDUT ('))
    init = circuit == 'dot-product'
    wrapper = '''`timescale 1ns/1ps
module TOP(input activate_0r, output activate_0a,
 output INP_0r, input INP_0a, input [IW:0] INP_0d,
 output reg OUT_0r=0, input OUT_0a, output reg [OW:0] OUT_0d=0 INITPORT);
wire [IW:0] a0 = INP_0a ? ~INP_0d : 0;
wire [IW:0] a1 = INP_0a ? INP_0d : 0;
wire [OW:0] r0,r1;
reg [OW:0] saved0,saved1;
DualDUT raw(.activate_0r(activate_0r),.activate_0a(activate_0a),
 .INP_0r(INP_0r),.INP_0a0d(a0),.INP_0a1d(a1),
 .OUT_0r0d(r0),.OUT_0r1d(r1),.OUT_0a(OUT_0a) INITCONNECT);
// Completion detection retains request until every output bit is spacer.
always @(r0 or r1) begin
 if (activate_0r === 1) begin
  if ((^r0) === 1'bx || (^r1) === 1'bx) $fatal(1,"FAIL: unknown dual rail");
  if ((r0 & r1) !== 0) $fatal(1,"FAIL: illegal dual-rail 11 code");
  if (OUT_0r && !OUT_0a && (r0 !== saved0 || r1 !== saved1))
    $fatal(1,"FAIL: dual-rail data withdrawn before acknowledgement");
 end
 if ((r0 | r1) === 0) OUT_0r = 0;
 else if ((&(r0 ^ r1)) === 1 && !OUT_0r) begin
  OUT_0d = r1; saved0=r0; saved1=r1; OUT_0r=1;
 end
end
endmodule
'''
    for key,value in [('INITPORT',', input initialise' if init else ''),('INITCONNECT',',.initialise(initialise)' if init else ''),('TOP',top),('INP',inp),('OUT',out),('IW',str(iw-1)),('OW',str(ow-1))]:
        wrapper=wrapper.replace(key,value)
    (gen/'adapter.sv').write_text(wrapper)
    files.append(gen/'adapter.sv')

results = {}
for scenario in scenarios:
    run = root/'runs'/scenario
    run.mkdir(parents=True,exist_ok=True)
    vector = gen/('expanded-vectors.hex' if scenario.startswith('expanded') else 'vectors.hex')
    count = len(vector.read_text().splitlines())
    options=[]
    if scenario in ('delayed','expanded-delayed'): options.append('+DELAYED')
    if scenario.startswith('expanded'): options.append('+REQUIRE_COVERAGE')
    if scenario=='negative-mismatch': options.append('+BAD_EXPECTED')
    if scenario=='negative-stall': options.append('+STALL_OUTPUT')
    status=execute([os.environ.get('XRUN','xrun'),'-64bit','-sv','-top',bench_top,
                    '+define+balsa_simulate','+define+balsa_init_time=20','-l','xrun.log']+
                   [str(f) for f in files]+['+VECTORS='+str(vector),'+NUM_VECTORS='+str(count),'+SCENARIO='+scenario]+options,
                   run,run/'console.log')
    log=(run/'console.log').read_text()
    (run/'exit-status.txt').write_text(str(status)+'\n')
    if scenario.startswith('negative'):
        marker='FAIL: injected expected-value mismatch' if scenario=='negative-mismatch' else 'FAIL: timeout waiting '+out+' request low'
        assert status not in (0,124,137) and marker in log, log[-3000:]
    else:
        label='count10b' if circuit=='count10b' else 'dot-product'
        assert status==0 and 'PASS: '+label+' structural Verilog checked '+str(count)+' transactions ('+scenario+')' in log,log[-3000:]
        assert len(re.findall(r'^CHECK:',log,re.M))==count
        assert not re.search(r'FAIL:|not correctly initialised|\*[EF],',log)
        if scenario.startswith('expanded'): assert 'load=200/200 count=320/320' in log
        if circuit=='dot-product': assert 'bit_pairs=256/256 boundaries=144/144' in log
    results[scenario]=dict(exit_code=status,accepted=True,log_sha256=hashlib.sha256((run/'console.log').read_bytes()).hexdigest())
    print('PASS:',encoding,circuit,scenario,flush=True)
evidence=dict(encoding=encoding,technology=technology,circuit=circuit,scenarios=results,
              hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[gen/'vectors.hex']})
(root/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
print('Evidence:',root,flush=True)
