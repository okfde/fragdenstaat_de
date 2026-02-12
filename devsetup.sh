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

ask() {
    # https://djm.me/ask
    local prompt default reply

    if [ "${2:-}" = "Y" ]; then
        prompt="Y/n"
        default=Y
    elif [ "${2:-}" = "N" ]; then
        prompt="y/N"
        default=N
    else
        prompt="y/n"
        default=
    fi

    while true; do

        # Ask the question (not using "read -p" as it uses stderr not stdout)
        echo -n "$1 [$prompt] "

        # Read the answer (use /dev/tty in case stdin is redirected from somewhere else)
        read reply </dev/tty

        # Default?
        if [ -z "$reply" ]; then
            reply=$default
        fi

        # Check if the reply is valid
        case "$reply" in
            Y*|y*) return 0 ;;
            N*|n*) return 1 ;;
        esac

    done
}

install_precommit() {
  local repo_dir="$1"
  if [ -e "$repo_dir/.pre-commit-config.yaml" ]; then
    pushd "$repo_dir"
    pre-commit install
    popd
  fi
}

venv() {
  echo "You need python >= 3.10, uv and pnpm installed."

  python3 --version
  pnpm --version
  uv --version

  if [ ! -d fds-env ]; then
    if ask "Do you want to create a virtual environment using $(python3 --version)?" Y; then
      echo "Creating virtual environment with uv and $(python3 --version)"
      uv venv fds-env
    fi
  fi

  if [ ! -d fds-env ]; then
    echo "Could not find virtual environment fds-env"
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
  # Check if running in Docker environment
  if $DOCKER; then
      uv pip install \
      --no-cache \
      --system \
      -r ./requirements-dev.txt

    for name in "${REPOS[@]}"; do
      uv pip install --system -e "./$name" --config-setting editable_mode=compat
    done
  else
    source fds-env/bin/activate
    echo "Installing $MAIN..."

    uv pip install -r $MAIN/requirements-dev.txt
    install_precommit "$MAIN"

    echo "Cloning / installing all editable dependencies..."
    for name in "${REPOS[@]}"; do
      uv pip install -e "./$name" --config-setting editable_mode=compat
      install_precommit "$name"
    done
  fi
}


dockerized() {
  pull
  docker compose build
  docker compose run --rm django python manage.py migrate --skip-checks
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

  # Add a Docker-specific override
  if $DOCKER; then
    MAIN="."
  fi

  # Setup main project and link dependencies
  pushd "$MAIN"
  pnpm install
  for name in "${FRONTEND[@]}"; do
    pnpm link --global "$name"
  done
  popd
}

upgrade_frontend_repos() {
  pnpm update "${FRONTEND[@]}"
}

messages() {
  fds-env/bin/python fragdenstaat_de/manage.py compilemessages -l de -i node_modules
}

forall() {
  echo "Executing '$@' in all repos"
  pushd $MAIN
    "$@"
  popd

  for name in "${REPOS[@]}"; do
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
  venv
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
