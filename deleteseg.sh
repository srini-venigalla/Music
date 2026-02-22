#!/bin/bash

# Function to convert HH:MM:SS to total seconds
to_seconds() {
    echo "$1" | awk -F: '{ print ($1 * 3600) + ($2 * 60) + $3 }'
}

INPUT=$1
# Convert inputs to raw numbers (e.g., 189 and 194)
START_SEC=$(to_seconds "$2")
END_SEC=$(to_seconds "$3")
OUTPUT=$4

# Now we pass raw numbers, which FFmpeg loves
ffmpeg -i "$INPUT" -filter_complex \
"[0:a]atrim=end=$START_SEC,asetpts=PTS-STARTPTS[a]; \
 [0:a]atrim=start=$END_SEC,asetpts=PTS-STARTPTS[b]; \
 [a][b]concat=n=2:v=0:a=1[out]" \
 -map "[out]" "$OUTPUT"

echo "Success! The segment between $2 and $3 has been removed."