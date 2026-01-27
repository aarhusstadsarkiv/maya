#!/bin/sh

# This script upgrades the module to the latest tag, unless the latest tag is already checked out.
# Usage: bin/upgrade.sh

# Fetch tags from the origin
git fetch --tags

# Get the latest tag
install_tag=$(git describe --tags `git rev-list --tags --max-count=1`)

# Check if latest tag is empty
if [ -z "$install_tag" ]; then
    echo "No tags found in the repository."
    exit 1
fi

# if first argument is not empty, use it as the tag to install
if [ ! -z "$1" ]; then
    install_tag=$1
fi

# Get the current checked out tag
current_tag=$(git describe --tags)

# Check if the current tag is the latest
if [ "$current_tag" = "$install_tag" ]; then
    echo "Latest tag ($install_tag) is already checked out."
    exit 0
fi

echo "Upgrading to the latest tag: $install_tag"

# Upgrade the repo and checkout the latest tag
git checkout -f main
git pull
git checkout $install_tag

# Activate virtual environment and install requirements
.venv/bin/uv sync

echo "Maya has been successfully upgraded to the latest tag."
