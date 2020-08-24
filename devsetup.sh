#!/bin/bash
set -ex

MAIN=fragdenstaat_de
REPOS=("froide" "froide-campaign" "froide-legalaction" "froide-food" "froide-payment" "froide-crowdfunding" "froide-fax" "froide-exam" "django-filingcabinet")
FRONTEND_DIR=("froide" "froide_food" "froide_campaign" "froide_payment" "filingcabinet")
FRONTEND=("froide" "froide_food" "froide_campaign" "froide_payment" "@okfde/filingcabinet")

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
    git pull
  popd
fi
pip install -U -r $MAIN/requirements-dev.txt
pip install -e $MAIN

echo "Cloning / installing all editable dependencies..."

for name in "${REPOS[@]}"; do
  if [ ! -d $name ]; then
    git clone git@github.com:okfde/$name.git
  else
    pushd $name
      git pull origin master
    popd
  fi
  pip uninstall -y $name
  pip install -e $name
done

echo "Installing all frontend dependencies..."

for name in "${FRONTEND_DIR[@]}"; do
  pushd $(python -c "import $name as mod; print(mod.__path__[0])")/..
  yarn install
  yarn link
  popd
done

echo "Linking frontend dependencies..."

pushd $MAIN
for name in "${FRONTEND[@]}"; do
  yarn link $name
done
yarn install
popd
