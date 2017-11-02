#!/bin/bash

if [ ! -d froide ]; then
  git clone https://github.com/okfde/froide.git
else
  pushd froide
  git pull origin master
  popd
fi

tmux new-session -d 'docker-compose up'
tmux split-window -h 'cd froide && \
npm install -g yarn && \
yarn install && \
npm run dev'
tmux -2 attach-session -d
