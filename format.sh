#!/usr/bin/env bash
set -euo pipefail

clang-format -i -style=file lib/src/*.cpp lib/tests/*.cpp lib/include/*.hpp python/src/*.cpp
