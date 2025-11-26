#!/bin/bash

set -e

# Our subset
LATIN="U+0000-007a,U+00A0-00FF,U+2010-2027,U+20AC,U+2190-2199,U+2764"
LATIN_EXT="U+0100-024F,U+0259,U+1E00-1EFF,U+2020,U+20A0-20AB,U+20AD-20CF,U+2113,U+2C60-2C7F,U+A720-A7FF"

# Check layout features on https://wakamaifondue.com/
# https://rsms.me/inter/lab/?feat-cv05=1&feat-cv07=1&feat-tnum=1
INTER_LAYOUT_FEATURES="calt,cv05,cv07,tnum,ss03"

SUBSETS=( "$LATIN" "$LATIN_EXT" )
SUBSET_NAMES=("latin" "latin-ext")

for subsetindex in ${!SUBSETS[*]}
do

subset=${SUBSETS[$subsetindex]}
subset_name=${SUBSET_NAMES[subsetindex]}

pyftsubset "InterVariable.ttf" \
    --unicodes="$subset" \
    --flavor="woff2" \
    --layout-features="$INTER_LAYOUT_FEATURES" \
    --output-file="inter/inter-$subset_name.woff2"

pyftsubset "InterVariable-Italic.ttf" \
    --unicodes="$subset" \
    --flavor="woff2" \
    --layout-features="$ADD_LAYOUT_FEATURES" \
    --output-file="inter/inter-italic-$subset_name.woff2"

pyftsubset "stixtwo.woff2" \
    --unicodes="$subset" \
    --flavor="woff2" \
    --output-file="stixtwo/stixtwo-$subset_name.woff2"

pyftsubset "stixtwo-italic.woff2" \
    --unicodes="$subset" \
    --flavor="woff2" \
    --output-file="stixtwo/stixtwo-italic-$subset_name.woff2"

# überbrückungsfonds fonts. make sure to place ttf files in folder!

pyftsubset "Gregory-Grotesk-Condensed-xBold.ttf" \
    --unicodes="$subset" \
    --flavor="woff2" \
    --output-file="gregory-grotesk/gregory-grotesk-condensed-xbold-$subset_name.woff2"

pyftsubset "Gregory-Grotesk-Compressed-xBold.ttf" \
    --unicodes="$subset" \
    --flavor="woff2" \
    --output-file="gregory-grotesk/gregory-grotesk-compressed-xbold-$subset_name.woff2"

done

