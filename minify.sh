#!/bin/bash

# Check if the input file is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <input_file>"
    exit 1
fi

input_file="$1"
output_file="${input_file%.txt}-min.txt"

# Read the content of the text file
typescript_code=$(cat "$input_file")

# Minify the TypeScript code
echo "$typescript_code" | \
sed '/\/\*/,/\*\//d' |  # Remove block comments
sed 's://.*$::' |       # Remove line comments
perl -pe 'next if /^$/; next if /^"/ and /"$/; s/^\s+|\s+$//g; s/\s*([\!\+\-\*\/\(\)\{\}\=\.\>\<\&\|\,\:])\s*/$1/g; if (!/[\}\)\;]\s*$/) { s/$/ /; } else { s/\s*$//; }' |  # Remove unnecessary whitespaces
tr -d '\n' |            # Remove newlines
sed 's/\s\{2,\}/ /g' > "$output_file"  # Replace multiple spaces with a single space

echo "Minified code has been saved to $output_file"
