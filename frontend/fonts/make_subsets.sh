#!/bin/bash

set -ex

PATH_TO_FONT="../../node_modules/inter-ui/Inter (web)"

GOOGLE_LATIN="U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"
GOOGLE_LATIN_EXT="U+0100-024F, U+0259, U+1E00-1EFF, U+2020, U+20A0-20AB, U+20AD-20CF, U+2113, U+2C60-2C7F, U+A720-A7FF"

# Our subset
LATIN="U+0000-007a,U+00A0-00FF,U+2010-2027,U+20AC,U+2192,U+2764"
LATIN_EXT="U+0100-024F,U+0259,U+1E00-1EFF,U+2020,U+20A0-20AB,U+20AD-20CF,U+2113,U+2C60-2C7F,U+A720-A7FF"

# Check layout features on https://wakamaifondue.com/
# https://rsms.me/inter/lab/?feat-cv05=1&feat-cv07=1&feat-tnum=1
ADD_LAYOUT_FEATURES="cv05,cv07,tnum"

SUBSETS=( "$LATIN" "$LATIN_EXT" )
SUBSET_NAMES=("latin" "latin-ext")
FORMATS=( "woff" "woff2" )
STYLES=("Regular" "Italic" "SemiBold" "Bold")

for format in "${FORMATS[@]}"
do
for style in "${STYLES[@]}"
do
for subsetindex in ${!SUBSETS[*]}
do

subset=${SUBSETS[$subsetindex]}
subset_name=${SUBSET_NAMES[subsetindex]}

pyftsubset "${PATH_TO_FONT}/Inter-$style.woff" \
    --unicodes="${subset}" \
    --flavor="${format}" \
    --layout-features+="${ADD_LAYOUT_FEATURES}" \
    --output-file="inter/Inter-${style}-${subset_name}.${format}"

done
done
done
