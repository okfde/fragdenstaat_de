#!/bin/bash
# Exit on errors
set -e

# On macOS with Homebrew, auto-detect GeoDjango libraries (GDAL, GEOS)
if [ "$(uname)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
  for pkg in gdal geos imagemagick; do
    prefix=$(brew --prefix "$pkg" 2>/dev/null || true)
    if [ -n "$prefix" ] && [ -d "$prefix/lib" ]; then
      # Append this lib dir to DYLD path container
      if [ -z "${FRAGDENSTAAT_DYLD_LIBRARY_PATH:-}" ]; then
        export FRAGDENSTAAT_DYLD_LIBRARY_PATH="$prefix/lib"
      else
        export FRAGDENSTAAT_DYLD_LIBRARY_PATH="$FRAGDENSTAAT_DYLD_LIBRARY_PATH:$prefix/lib"
      fi
      echo "Auto-added $prefix/lib to FRAGDENSTAAT_DYLD_LIBRARY_PATH"
      # Export direct Django env var so ctypes can find the right dylib
      case "$pkg" in
        gdal)
          libfile="$prefix/lib/libgdal.dylib"
          export GDAL_LIBRARY_PATH="$libfile"
          echo "Auto-set GDAL_LIBRARY_PATH=$libfile"
          ;;
        geos)
          libfile="$prefix/lib/libgeos_c.dylib"
          export GEOS_LIBRARY_PATH="$libfile"
          echo "Auto-set GEOS_LIBRARY_PATH=$libfile"
          ;;
        imagemagick)
          # Set MAGICK_HOME so wand.api can locate its libraries
          export MAGICK_HOME="$prefix"
          echo "Auto-set MAGICK_HOME=$prefix"
          ;;
      esac
    fi
  done
fi

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
  # Check for GDAL system library (needed for GIS support)
  if ! command -v gdalinfo >/dev/null 2>&1; then
    echo "Error: GDAL not found. Please install GDAL (e.g. 'brew install gdal' or 'sudo apt-get install libgdal-dev gdal-bin')."
    exit 1
  fi
  # If installed via Homebrew, point Django at the dylib
  if command -v brew >/dev/null 2>&1; then
    # brew --prefix gdal may return Cellar path; lib is in lib/
    _prefix=$(brew --prefix gdal 2>/dev/null || true)
    if [ -n "$_prefix" ]; then
      _lib="$_prefix/lib/libgdal.dylib"
      if [ -f "$_lib" ]; then
        export GDAL_LIBRARY_PATH="$_lib"
        echo "Using GDAL_LIBRARY_PATH=$_lib"
      fi
    fi
  fi

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
      git pull origin "$(git branch --show-current)"
    popd
  fi

  for name in "${REPOS[@]}"; do
    if [ ! -d $name ]; then
      git clone git@github.com:okfde/$name.git
    else
      pushd $name
        git pull origin "$(git branch --show-current)"
      popd
    fi
  done
}

dependencies() {
  source fds-env/bin/activate
  echo "Installing $MAIN..."

  uv pip install -r $MAIN/requirements-dev.txt
  install_precommit "$MAIN"

  echo "Cloning / installing all editable dependencies..."

  for name in "${REPOS[@]}"; do
    uv pip install -e "./$name" --config-setting editable_mode=compat
    install_precommit "$name"
  done
}
frontend() {
  echo "Installing frontend dependencies..."

  safe_global_link () {
    # $1 = directory of the package     (e.g. froide-food)
    # $2 = optional target to link to   (e.g. froide)
    local pkg_dir=$1
    shift

    # Figure out the package name from package.json
    local pkg_name
    pkg_name=$(jq -r .name <"$pkg_dir/package.json")

    # If it's already linked globally - unlink first
    if pnpm ls -g --depth -1 | grep -q " $pkg_name@"; then
      echo "Unlinking previously linked $pkg_name"
      pnpm unlink --global "$pkg_name" || true
    fi

    # Skip linking if the peer target is the same as this package directory
    if [ "$#" -gt 0 ] && [ "$(cd \"$pkg_dir\" && pwd -P)" = "$(cd \"$1\" && pwd -P)" ]; then
      echo "  $pkg_name already provides peer \"$1\" - skipping"
      return 0
    fi

    echo "Linking $pkg_name globally"
    (cd "$pkg_dir" && pnpm link --global "$@")
  }

  # ---- Step 1 - link everything globally --------------------------------
  for dir in "${FRONTEND_DIR[@]}"; do
    safe_global_link "$dir"
  done

  for dir in "${FROIDE_PEERS[@]}"; do
    safe_global_link "$dir" "froide"
  done

  # ---- Step 2 - install local deps ---------------------------------------
  for dir in "${FRONTEND_DIR[@]}"; do
    (cd "$dir" && pnpm install)
  done

  # ---- Step 3 - install root deps and link frontend packages into main workspace ----
  (cd "$MAIN" && pnpm install && \
    for name in "${FRONTEND[@]}"; do \
      if [ -L node_modules/"$name" ]; then \
        echo "  $name already linked - skipping"; \
      else \
        pnpm link "$name"; \
      fi; \
    done \
  )
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
