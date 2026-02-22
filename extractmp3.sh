#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <input_file> <start_time> <duration> <output_file>"
    echo "Example: $0 song.mp3 00:01:20 30 snippet.mp3"
    exit 1
fi

# Assign parameters to readable variables
INPUT_FILE=$1
START_TIME=$2
DURATION=$3
OUTPUT_FILE=$4

# Execute FFmpeg
ffmpeg -i "$INPUT_FILE" -ss "$START_TIME" -to "$DURATION" -c copy "$OUTPUT_FILE"

echo "Done! Segment saved to $OUTPUT_FILE"