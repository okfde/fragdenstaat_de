#!/bin/bash
set -ex

MAIN=fragdenstaat_de
REPOS=("froide" "froide-campaign" "froide-legalaction" "froide-food" "froide-payment" "froide-crowdfunding" "froide-govplan" "froide-fax" "froide-exam" "django-filingcabinet")
FRONTEND_DIR=("froide" "froide_food" "froide_exam" "froide_campaign" "froide_payment" "froide_legalaction" "filingcabinet")
FRONTEND=("froide" "froide_food" "froide_exam" "froide_campaign" "froide_payment" "froide_legalaction" "@okfde/filingcabinet")
FRONTEND_DEPS=("froide" "@okfde/filingcabinet")

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

setup() {

  echo "You need python3 >= 3.8 and yarn installed."

  python3 --version
  yarn --version

  if [ ! -d fds-env ]; then
    if ask "Do you want to create a virtual environment using $(python3 --version)?" Y; then
      echo "Creating virtual environment with Python: $(python3 --version)"
      python3 -m venv fds-env
    fi
  fi

  if [ ! -d fds-env ]; then
    echo "Could not find virtual environment fds-env"
  fi

  echo "Activating virtual environment..."
  source fds-env/bin/activate

  echo "Cloning / installing $MAIN"

  if [ ! -d $MAIN ]; then
    git clone git@github.com:okfde/$MAIN.git
  else
    pushd $MAIN
      git pull origin "$(git branch --show-current)"
    popd
  fi
  pip install -U pip-tools
  pip-sync $MAIN/requirements-dev.txt
  pip install -e $MAIN
  install_precommit "$MAIN"

  echo "Cloning / installing all editable dependencies..."

  for name in "${REPOS[@]}"; do
    if [ ! -d $name ]; then
      git clone git@github.com:okfde/$name.git
    else
      pushd $name
        git pull origin "$(git branch --show-current)"
      popd
    fi
    pip uninstall -y $name
    pip install -e $name
    install_precommit "$name"
  done

  echo "Installing all frontend dependencies..."

  frontend

  fds-env/bin/python fragdenstaat_de/manage.py compilemessages -l de

  echo "Done."
}

frontend() {
  for name in "${FRONTEND_DIR[@]}"; do
    pushd $(python -c "import $name as mod; print(mod.__path__[0])")/..
    yarn link
    popd
  done

  echo "Linking frontend dependencies..."

  for name in "${FRONTEND_DIR[@]}"; do
    for dep in "${FRONTEND_DEPS[@]}"; do
      if [ "$name" != "$dep" ]; then
        pushd $(python -c "import $name as mod; print(mod.__path__[0])")/..
        yarn link $dep
        popd
      fi
    done
  done

  pushd $MAIN
  for name in "${FRONTEND[@]}"; do
    yarn link $name
  done
  yarn install
  popd
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


if [[ $1 =~ ^(forall)$ ]]; then
  "$@"
elif [[ $1 =~ ^(frontend)$ ]]; then
  frontend
else
  setup
fi
