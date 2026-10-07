#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
bob=${BOB:-bob}

test_inheritance()
{
    output=$(cd "$script_dir/inheritance" && "$bob" show config-inheritance-observe --format flat)
    if printf '%s\n' "$output" | grep -q '^buildVars.LEFT_ONLY='; then
        echo "Config from left leaked through right" >&2
        exit 1
    fi
    printf '%s\n' "$output" | grep -Fx 'buildVars.RIGHT_ONLY=right'
}

test_range()
{
    error=$(mktemp)
    trap 'rm -f "$error"' EXIT HUP INT TERM
    if (cd "$script_dir/range" && "$bob" show range --format yaml) > /dev/null 2> "$error"; then
        echo "Out-of-range Config default was accepted" >&2
        exit 1
    fi
    grep -F "Config: RANGE: '11' is above allowed range [1 - 10]" "$error"
    (cd "$script_dir/range" && "$bob" show -D RANGE=10 range --format yaml) > /dev/null
}

test_inheritance
test_range
