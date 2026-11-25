#!/bin/sh
exec python "$(dirname "$0")/stub_claude.py" "$@"
