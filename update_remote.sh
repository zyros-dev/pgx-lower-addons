#!/bin/bash

set -e

cd "$(dirname "$0")"

timestamp=$(date '+%Y-%m-%d %H:%M:%S')

git add .
git commit -m "Update: $timestamp"
git push

echo "Pushed to remote at $timestamp"
