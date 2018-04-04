#!/bin/bash

if [ ! -d froide ]; then
  git clone https://github.com/okfde/froide.git
else
  pushd froide
  git pull origin master
  popd
fi
