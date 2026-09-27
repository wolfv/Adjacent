# Adjacent on pixi + rattler-blaze (experimental)

This worktree builds Adjacent with pixi's embedded rattler-blaze engine; see
`~/Programs/rattler-blaze/pixi/README.md`. The build backends only emit a
recipe. Pixi builds it, and every compile, link and CTest test is its own
cached action.

```bash
alias bpixi='WORKSPACE=$PWD ~/Programs/rattler-blaze/pixi/pixi.sh'

bpixi run //                     # list package targets and tasks
bpixi run //build                # libadjacent + adjacent-python, one graph
bpixi run libadjacent//test      # 32 CTest tests, each a cached action
bpixi run adjacent-python//test  # tests/ against the installed package
bpixi run //lint                 # clang-format (per file, cached) + ruff
bpixi run //fmt                  # clang-format -i + ruff format
bpixi install                    # pixi's own install, packages built by blaze
```

Default tasks come from the backends:

- `lint-cpp` / `fmt-cpp`: clang-format, added because of the repository's
  `.clang-format`.
- `lint-py` / `fmt-py`: ruff.
- `lint` and `fmt`: aliases for the tasks above.

A task with the same name in `[package.tasks]` replaces the default.
`default-tasks = false` in `[package.build.config]` turns the defaults off.

The only manifest change is in `lib/pixi.toml`: `BUILD_TESTING` is now `ON`.
Tests are cached actions in the same build graph, so they no longer need a
separate Debug build tree.
