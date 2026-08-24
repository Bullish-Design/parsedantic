{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = [ 
    pkgs.git 
    pkgs.uv
    ];

  # https://devenv.sh/languages/
  # languages.rust.enable = true;
  languages = {
      python = {
          enable = true;
          version = "3.13";
          venv.enable = true;
          uv.enable = true;
        };
    };

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/scripts/
  scripts.hello.exec = ''
    echo hello from $GREET
  '';

  enterShell = ''
    hello
    git --version
  '';

  # devman — the automation plane (CONCEPT.md §5). `base` alone: this repository
  # ships no scheduled work and writes none of its own files.
  devman = {
    enable = true;
    project = "parsedantic";
    groups = [ "base" ];
  };

  # https://devenv.sh/tasks/
  #
  # base's two names. The group file names a task and never a tool or its
  # arguments, so what each one IS lives here.
  #
  # `base:test` IS NOT `devenv test`. `enterTest` below is still the devenv
  # template's default — it greps `git --version` — so `devenv test` exits 0
  # having tested nothing, which is what PROPOSAL.md §12's fourth rule forbids
  # shipping as a default. The suite is `tests/`, and `pytest` runs it.
  tasks = {
    # `uv run --extra dev`, not a bare `pytest`. This project keeps pytest in
    # `[project.optional-dependencies].dev`, and devenv's venv installs only the
    # base dependencies — a bare `pytest` is `command not found` inside the
    # shell. `uv run --extra dev` resolves the group and runs the suite.
    "parsedantic:lint".exec = "ruff check .";
    "parsedantic:test".exec = "uv run --extra dev pytest";

    "base:check".after = [ "parsedantic:lint" ];
    "base:test".after = [ "parsedantic:test" ];
  };

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
  '';

  # https://devenv.sh/pre-commit-hooks/
  # pre-commit.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
