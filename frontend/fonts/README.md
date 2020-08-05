# Optimize font for web

We are using the font Inter by [Rasmus Andersson](https://rsms.me/) licensed under the [SIL OpenFont License 1.1](https://choosealicense.com/licenses/ofl-1.1/).

This script builds it for our needs. Do this:

1. Create a Python3 virtualenv and install dependencies from `requirements.txt`
2. Make sure the latest font via npm is installed in `../../node_modules/inter-ui`
3. Run script which will create subsets by unicode range in woff/woff2 in the `inter` directory.
