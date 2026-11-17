#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exec python3 "$base/run.py" bundled-data count10b
