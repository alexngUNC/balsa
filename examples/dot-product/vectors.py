#!/usr/bin/env python3
"""Generate shared Breeze/HDL vectors with a host integer arithmetic oracle."""
import json
from pathlib import Path
import random
import sys


def make_vectors():
    vectors = []

    def add(a, b, category):
        assert len(a) == len(b) == 4 and all(0 <= x <= 255 for x in a + b)
        expected = sum(x * y for x, y in zip(a, b))
        assert 0 <= expected <= 260100
        command = sum(value << (8 * index) for index, value in enumerate(a + b))
        vectors.append(dict(index=len(vectors) + 1, a=a, b=b, expected=expected,
                            command=command, category=category))

    add([0]*4, [0]*4, 'zero')
    add([255]*4, [255]*4, 'maximum')
    add([1,2,3,4], [5,6,7,8], 'lane ordering')
    add([128]*4, [128]*4, 'sum above 16 bits')
    add([255,0,255,0], [0,255,0,255], 'orthogonal')
    add([170,85,170,85], [85,170,85,170], 'alternating bits')
    add([255]*4, [1]*4, 'ones')
    add([1]*4, [255]*4, 'ones swapped')
    for lane in range(4):
        for abit in range(8):
            for bbit in range(8):
                a, b = [0]*4, [0]*4
                a[lane], b[lane] = 1 << abit, 1 << bbit
                add(a, b, 'isolated lane bit pair')
        for aval in (0,1,127,128,254,255):
            for bval in (0,1,127,128,254,255):
                a, b = [0]*4, [0]*4
                a[lane], b[lane] = aval, bval
                add(a, b, 'isolated lane boundaries')
    rng = random.Random(0x573D074)
    for _ in range(128):
        a = [rng.randrange(256) for _ in range(4)]
        b = [rng.randrange(256) for _ in range(4)]
        add(a, b, 'seeded random')
        add(b, a, 'commuted random')
        add(list(reversed(a)), list(reversed(b)), 'permuted random')
    for _ in range(8):
        add([255]*4, [255]*4, 'repeated maximum')
        add([255]*4, [255]*4, 'repeated maximum')
        add([0]*4, [255]*4, 'zero after maximum')
    assert len(vectors) == 816
    return vectors


def generate(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    vectors = make_vectors()
    (directory / 'vectors.json').write_text(json.dumps(vectors, indent=2) + '\n')
    (directory / 'vectors.hex').write_text(''.join(
        '{:021x}\n'.format((v['command'] << 18) | v['expected']) for v in vectors))
    lines = ['-- Generated self-checker; expected values use Python integer multiplication.',
             'import [dot_product]', 'import [balsa.sim.sim]',
             'procedure balsa_top is',
             '  channel commands : DotOperands', '  channel results : DotSum',
             '  variable command : DotOperands', '  variable actual, expected : DotSum',
             '  variable index : 16 bits', '  variable failed, stopped : bit', 'begin',
             '  dot4 (commands, results) ||', '  begin', '    failed := 0;', '    index := 0;',
             '    loop while index < {} then'.format(len(vectors)), '      case index of']
    for index, v in enumerate(vectors):
        prefix = '        ' if index == 0 else '      | '
        fields = ', '.join(map(str, v['a'] + v['b']))
        lines.append(prefix + '{} then command := DotOperands {{{}}}; expected := {}'.format(
            index, fields, v['expected']))
    lines += ['      end;', '      commands <- command;', '      results -> actual;',
              '      if actual /= expected then failed := 1 end;',
              '      index := (index + 1 as 16 bits)', '    end;',
              '    if not failed then stopped := BalsaSimulationStop () else halt end',
              '  end', 'end']
    (directory / 'dot_test.balsa').write_text('\n'.join(lines) + '\n')
    summary = dict(transactions=len(vectors), lanes=4, operand_bits=8, result_bits=18,
                   maximum=260100, seed='0x573d074',
                   categories={category: sum(v['category'] == category for v in vectors)
                               for category in sorted({v['category'] for v in vectors})})
    (directory / 'vector-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: vectors.py OUTPUT_DIRECTORY')
    print(json.dumps(generate(sys.argv[1]), indent=2))
