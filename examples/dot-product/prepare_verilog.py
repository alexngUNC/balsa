#!/usr/bin/env python3
"""Map an already Breeze-tested circuit and audit its structural dependencies."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
source = Path(__file__).resolve().parent
generated = root / 'generated'
logs = root / 'logs'
logs.mkdir(exist_ok=True)
home = Path(subprocess.check_output(['balsa-config', '-d'], text=True).strip())
models = home / 'share/tech/example/example-cells.v'
shutil.copy2(str(models), str(generated / 'example-cells.v'))
with (logs / 'netlist.log').open('w') as log:
    subprocess.run(['balsa-netlist', '--simulation-initialise', '-X',
                    'example/four_b_rb', '-n', 'verilog', 'dot_product.breeze'],
                   cwd=str(generated), stdout=log, stderr=subprocess.STDOUT,
                   check=True, timeout=120)
netlist = (generated / 'dot_product.v').read_text()
top = netlist.split('module Balsa_dot4 (', 1)[1].split('endmodule', 1)[0]
for declaration in ('input activate_0r;', 'output activate_0a;',
                    'output operands_0r;', 'input operands_0a;',
                    'input [63:0] operands_0d;', 'output result_0r;',
                    'input result_0a;', 'output [17:0] result_0d;', 'input initialise;'):
    assert declaration in top, 'Unexpected generated interface: ' + declaration
definitions = set(re.findall(r'^module\s+(\w+)', netlist, re.M))
model_definitions = set(re.findall(r'^(?:module|primitive)\s+(\w+)', models.read_text(), re.M))
instances = set(re.findall(r'^\s*(\w+)\s+I\d+\s*\(', netlist, re.M))
unresolved = instances - definitions - model_definitions
assert not unresolved, 'Unresolved cells: ' + str(unresolved)
audit = dict(top='Balsa_dot4', technology='example/four_b_rb',
             generated_modules=sorted(definitions),
             required_external_cells=sorted(instances - definitions), unresolved=[])
(generated / 'cell-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
paths = [source / name for name in ('dot_product.balsa', 'vectors.py', 'test.sh',
                                  'dot_product_tb.sv', 'verify.sh', 'prepare_verilog.py', 'record_results.py')]
paths += [generated / name for name in ('dot_product.v', 'dot_test.balsa',
                                       'vectors.json', 'vectors.hex', 'example-cells.v')]
paths += [home / 'share/scheme' / name for name in ('misc.scm', 'gen.scm')]
manifest = dict(technology='example/four_b_rb',
                source_revision=subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
                source_status=subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True),
                files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(generated / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('PREPARED: dot-product structural netlist and resolved static cell names')
