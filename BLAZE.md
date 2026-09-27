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

Manifest changes in this worktree:

- `pixi.toml`: `preview` gains `pixi-build-blaze`.
- `lib/pixi.toml`: `BUILD_TESTING` is now `ON`. Tests are cached actions in
  the same build graph, so they no longer need a separate Debug build tree.

## Changing the build: `[package.steps]`

The backend's build steps are named `configure`, `compile`, `install` and
`in-build-tests`. An entry in `[package.steps]` with one of those names
replaces the step. Any other entry is a new step, placed with `required-by`.
Steps are part of the package, so they change its build string.

```toml
# lib/pixi.toml: strict-warnings package build, keeping the backend's arguments
[package.steps.configure]
cmd = "{{ default.cmd }} -DADJACENT_STRICT_WARNINGS=ON"

# a generated header, produced before configure (declares inputs/outputs)
[package.steps.codegen]
cmd = "python tools/gen.py --out generated/"
inputs = ["tools/gen.py"]
outputs = ["generated/**"]
required-by = ["configure"]
```

`bpixi task explain libadjacent//configure` shows the default command, the
override and where it came from. `bpixi run libadjacent//` lists everything
and marks the steps that are overridden.

`pixi run pkg//task` takes the build and host environments from `pixi.lock`
where the package is locked. Otherwise blaze solves them, and says so.
