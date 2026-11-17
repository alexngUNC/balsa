"""Finite single-command coverage for legal decade states, plus sequences."""
import json
from pathlib import Path

UP = (1, 2, 3, 4, 5, 6, 7, 8, 9, 0)
DOWN = (9, 0, 1, 2, 3, 4, 5, 6, 7, 8)


def generate(directory):
    vectors = []
    state = None

    def add(data, mode, direction, phase):
        nonlocal state
        previous = state
        if mode == 'load':
            assert data in range(10)
            state = data
        else:
            assert previous is not None and data in range(16)
            state = (UP if direction == 'up' else DOWN)[previous]
        command = (int(direction == 'up') << 5) | (int(mode == 'count') << 4) | data
        vectors.append(dict(index=len(vectors) + 1, previous=previous, data=data,
                            mode=mode, direction=direction, packed_command=command,
                            expected=state, phase=phase))

    # All 10 prior states x 10 legal load values x both direction bits.
    for previous in range(10):
        for direction in ('down', 'up'):
            for data in range(10):
                add(previous, 'load', 'down', 'load setup')
                add(data, 'load', direction, 'load cross')

    # Count ignores the entire data nibble, including bit patterns 10 through 15.
    for previous in range(10):
        for direction in ('down', 'up'):
            for data in range(16):
                add(previous, 'load', 'up', 'count setup')
                add(data, 'count', direction, 'count cross')

    add(0, 'load', 'up', 'sequence setup')
    for direction in ('up', 'down'):
        for _ in range(30):
            add(0, 'count', direction, 'repeated count')
    for index in range(40):
        add(15, 'count', 'up' if index % 2 == 0 else 'down', 'alternating count')
    for direction in ('down', 'up'):
        for data in range(10):
            for _ in range(2):
                add(data, 'load', direction, 'repeated load')

    loads = {(v['previous'], v['data'], v['direction']) for v in vectors
             if v['previous'] is not None and v['mode'] == 'load'}
    counts = {(v['previous'], v['data'], v['direction']) for v in vectors
              if v['mode'] == 'count'}
    assert len(vectors) == 1181 and len(loads) == 200 and len(counts) == 320
    directory = Path(directory)
    (directory / 'expanded-vectors.hex').write_text(''.join(
        '{:03x}\n'.format((v['packed_command'] << 4) | v['expected']) for v in vectors))
    (directory / 'expanded-vectors.json').write_text(json.dumps(vectors, indent=2) + '\n')
    summary = dict(transactions=len(vectors), load_transition_bins=len(loads),
                   count_transition_bins=len(counts),
                   note='Planned stimulus coverage; actual checked coverage is reported by the SV bench.',
                   excluded='Load data 10–15; state outside 0–9; arbitrary unbounded command sequences.')
    (directory / 'expanded-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(generate(__import__('sys').argv[1] if len(__import__('sys').argv) == 2 else Path(__file__).resolve().parent / 'generated'), indent=2))
