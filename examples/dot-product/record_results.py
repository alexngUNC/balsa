#!/usr/bin/env python3
"""Accept only completed Breeze/HDL checks and record exact input/log hashes."""
import hashlib
import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()
generated = root / 'generated'
manifest = json.loads((generated / 'manifest.json').read_text())
for name, expected_hash in manifest['files'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected_hash, 'Changed input: ' + name
assert 'BalsaSimulationStop called' in (generated / 'breeze.log').read_text()
assert 'PASS: 816 dot-product transactions in Breeze' in (root / 'logs/breeze-suite.log').read_text()
vectors = json.loads((generated / 'vectors.json').read_text())
assert len(vectors) == 816
scenarios = {}
tool_versions = set()
for mode in ('baseline', 'delayed', 'negative-mismatch', 'negative-stall'):
    log = root / 'runs' / mode / 'console.log'
    text = log.read_text()
    status = int((log.parent / 'exit-status.txt').read_text())
    tool = re.search(r'TOOL:\s*xrun(?:\(64\))?\s+(\S+)', text)
    assert tool, 'Missing actual simulator version in ' + mode
    tool_versions.add(tool.group(1))
    coverage = None
    checks = re.findall(r'^CHECK: transaction=(\d+) result=(\d+)$', text, re.M)
    if mode in ('baseline', 'delayed'):
        assert status == 0
        assert [(int(i), int(value)) for i, value in checks] == [(v['index'], v['expected']) for v in vectors]
        assert 'PASS: dot-product structural Verilog checked 816 transactions (' + mode + ')' in text
        assert not re.search(r'FAIL:|not correctly initialised|\*[EF],', text)
        match = re.search(r'^COVERAGE: bit_pairs=(\d+)/256 boundaries=(\d+)/144 '
                          r'maxima=(\d+) wide=(\d+) repeats=(\d+) cleared=(\d+)$', text, re.M)
        assert match, 'Missing actual checked coverage'
        coverage = dict(zip(('bit_pairs', 'boundaries', 'maxima', 'wide_results',
                             'repeated_commands', 'zero_after_maximum'), map(int, match.groups())))
        assert coverage['bit_pairs'] == 256 and coverage['boundaries'] == 144
        assert coverage['maxima'] > 0 and coverage['wide_results'] > 0
        assert coverage['repeated_commands'] >= 8 and coverage['zero_after_maximum'] >= 8
        verdict = 'functional simulation passed'
    else:
        assert status not in (0, 124, 137)
        marker = ('FAIL: injected expected-value mismatch actual=0 expected=1'
                  if mode == 'negative-mismatch' else 'FAIL: timeout waiting result request low')
        assert marker in text and 'PASS: dot-product structural Verilog' not in text
        if mode == 'negative-stall': assert 'INJECT: withholding result acknowledgement' in text
        verdict = 'checker detected intended injected fault'
    scenarios[mode] = dict(exit_code=status, verdict=verdict, checked_transactions=len(checks),
                           coverage=coverage, log=str(log.relative_to(root)),
                           log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
assert len(tool_versions) == 1, 'Mixed simulator versions in the result set'
evidence = dict(tool='Xcelium ' + next(iter(tool_versions)), technology='example/four_b_rb',
                circuit='four-element unsigned 8-bit dot product, 18-bit full-precision sum',
                breeze_transactions=len(vectors), breeze_stop_marker=True,
                scenarios=scenarios, manifest=manifest,
                breeze_log_sha256=hashlib.sha256((generated / 'breeze.log').read_bytes()).hexdigest(),
                limits='Directed and seeded-random functional coverage; no exhaustive input, formal, or physical timing proof.')
(root / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
print('RECORDED: matching 816-vector Breeze and Xcelium checks plus checker fault detection')
