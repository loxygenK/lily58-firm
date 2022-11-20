#!/bin/env bash

function _link() {
  local qmkhome=$(bash -c 'source <(qmk env) && echo $QMK_HOME')
  if [ -z "$qmkhome" ]; then
    echo "Could not identify QMK_HOME - is QMK installed to your system?"
    return 1
  fi
  echo "🔭 QMK HOME is at $qmkhome"

  local linkdest="$qmkhome/keyboards/lily58/keymaps/loxygenK"
  echo "️🔗 Linking using symbolic link to $linkdest"

 # TODO: Check if something already exists at the destination
 ln -s $(pwd) $linkdest

  echo "✅ Okay! Now you can do some flashing."
}

_link
