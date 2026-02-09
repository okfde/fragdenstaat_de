#!/bin/bash
set -e

# macOS's System Integrity Protection purges the environment variables controlling
# `dyld` when launching protected processes (https://developer.apple.com/library/archive/documentation/Security/Conceptual/System_Integrity_Protection_Guide/RuntimeProtections/RuntimeProtections.html#//apple_ref/doc/uid/TP40016462-CH3-SW1)
# This causes macOS to remove the DYLD_ env variables when running this script, so we have to set them again
if [ !  -z "${FRAGDENSTAAT_DYLD_LIBRARY_PATH:-}" ]; then
    export LD_LIBRARY_PATH=${FRAGDENSTAAT_DYLD_LIBRARY_PATH:-}:${LD_LIBRARY_PATH:-}
    export DYLD_LIBRARY_PATH=$LD_LIBRARY_PATH:${DYLD_LIBRARY_PATH:-}
fi

MAIN=fragdenstaat_de
REPOS=("froide" "froide-campaign" "froide-legalaction" "froide-food" "froide-payment" "froide-crowdfunding" "froide-govplan" "froide-fax" "froide-exam" "django-filingcabinet" "froide-evidencecollection")
FRONTEND=("froide" "froide_food" "froide_exam" "froide_campaign" "froide_payment" "froide_legalaction" "@okfde/filingcabinet")
FRONTEND_DIR=("froide" "froide-food" "froide-exam" "froide-campaign" "froide-payment" "froide-legalaction" "django-filingcabinet")
FROIDE_PEERS=("froide-campaign" "froide-food") # these have peer-dependencies on froide

ALL=("$MAIN" "${REPOS[@]}")

PYTHON_VERSION="3.14"

if [[ $(basename "$PWD") == "$MAIN" ]]; then
  # make sure we're starting from the main project's parent dir,
  # even when executed from main project
  cd ..
fi

check_versions() {
  echo "You need python, uv and pnpm 9 installed."

  uv --version >> /dev/null

  if [[ "$(pnpm --version)" != 9.* ]]; then
    echo You need to have pnpm v9 installed.
  fi
}

pull() {
  echo "Cloning / installing $MAIN"

  if [ ! -d $MAIN ]; then
    git clone git@github.com:okfde/$MAIN.git
  else
    pushd $MAIN
      git pull origin --autostash "$(git branch --show-current)"
    popd
  fi

  for name in "${REPOS[@]}"; do
    if [ ! -d $name ]; then
      git clone git@github.com:okfde/$name.git
    else
      pushd $name
        git pull origin --autostash "$(git branch --show-current)"
      popd
    fi
  done
}

dependencies() {
  echo "Creating virtual environments and installing dependencies..."

  if ! command -v prek > /dev/null 2>&1; then
    echo "prek is not installed. Run `uv tool install prek` to fix this. Make sure `$(uv tool dir)` is in your \$PATH. If it is not, run `uv run update-shell`."
  fi

  for name in "${ALL[@]}"; do
    pushd "$name"
    
    if [ ! -d ".venv" ]; then
      uv venv -p "$PYTHON_VERSION"
    fi

    uv sync --all-extras
    source .venv/bin/activate

    if [[ $name == "froide" ]]; then
      uv pip install -e ../django-filingcabinet
    fi

    if [[ $name == "$MAIN" ]]; then
      for project in "${REPOS[@]}"; do
        uv pip install -e "../$project" --config-setting editable_mode=compat
      done
    fi

    if [ -e ".pre-commit-config.yaml" ]; then
      prek install
    fi
    popd
  done
}

upgrade_backend_repos() {
  pushd $MAIN
  set -x
  uv sync ${REPOS[@]/#/--upgrade-package }
  popd
}

frontend() {
  pnpm_version=$(pnpm --version)

  if [[ $pnpm_version != 9.15* ]]; then
    echo "You need to have pnpm@^9.15 installed"
    exit 1
  fi

  echo "Installing frontend dependencies..."

  # we need to link globally since local linking adjusts the lockfile

  # Install and link all frontend packages
  for name in "${FRONTEND_DIR[@]}"; do
    pushd "$name"
    pnpm link --global
    pnpm install
    popd
  done

 # Link froide peer dependencies
  for name in "${FROIDE_PEERS[@]}"; do
    pushd "$name"
    pnpm link --global "froide"
    popd
  done

  # Setup main project and link dependencies
  pushd "$MAIN"
  pnpm install
  for name in "${FRONTEND[@]}"; do
    pnpm link --global "$name"
  done
  popd
}

upgrade_frontend_repos() {
  pushd "$MAIN"
  pnpm update "${FRONTEND[@]}"
  popd
}

messages() {
  pushd "$MAIN"
  source .venv/bin/activate
  python fragdenstaat_de/manage.py compilemessages -l de -i node_modules
  popd
}

forall() {
  echo "Executing '$@' in all repos"

  for name in "${ALL[@]}"; do
    pushd $name
      "$@"
    popd
  done
}

help() {
  echo "Available commands:"
  echo "setup: setup / update all repos"
  echo "forall: run command in all repos"
}


if [ -z "$1" ]; then
  check_versions
  pull
  dependencies
  frontend
  messages
  
  echo "Done!"
else
  if [[ $(type -t "$1") == function ]]; then
    "$@"
  else
    help
    exit 1
  fi
fi
