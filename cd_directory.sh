#!/bin/bash

# Usage: source script.sc filename

if [ -z "$1" ]; then
    echo "Usage: source script.sc <filename>"
    return 1
fi

filename="$1"

# Find the first match (you can modify to get more specific if needed)
found_path=$(find . -type f -name "$filename" -print -quit)

if [ -z "$found_path" ]; then
    echo "File '$filename' not found."
    return 1
else
    dir_path=$(dirname "$found_path")
    echo "Changing directory to: $dir_path"
    cd "$dir_path"
fi
