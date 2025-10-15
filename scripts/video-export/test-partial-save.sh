#!/bin/bash
# Test script to verify partial video save feature
# Runs export for 10 seconds then triggers graceful shutdown

echo "========================================"
echo "Testing Partial Video Save (10 seconds)"
echo "========================================"
echo ""

# Clean up any running processes
pkill -f "slidev.*3030" 2>/dev/null
pkill -f "export.*FEN_GDC" 2>/dev/null
sleep 1

# Start the export in background
cd /Users/cjohndesign/dev/FEN
npm run export-video FEN_GDC 2>&1 | tee /tmp/partial-test.log &
EXPORT_PID=$!

echo "Export started (PID: $EXPORT_PID)"
echo "Recording for 10 seconds..."
echo ""

# Wait 10 seconds
for i in {10..1}; do
  echo -ne "\rStopping in $i seconds... "
  sleep 1
done
echo ""
echo ""

# Send SIGINT to trigger graceful shutdown
echo "Sending SIGINT to trigger graceful shutdown..."
kill -INT $EXPORT_PID

# Wait for shutdown to complete
echo "Waiting for graceful shutdown to complete..."
wait $EXPORT_PID 2>/dev/null

echo ""
echo "========================================"
echo "Checking results..."
echo "========================================"
echo ""

# Check if partial video was saved
echo "Partial videos in exports/videos/:"
ls -lh exports/videos/*PARTIAL*.webm 2>/dev/null | tail -3

echo ""
echo "Latest video file:"
LATEST_VIDEO=$(ls -t exports/videos/*PARTIAL*.webm 2>/dev/null | head -1)
if [ -n "$LATEST_VIDEO" ]; then
  echo "  File: $LATEST_VIDEO"
  echo "  Size: $(du -h "$LATEST_VIDEO" | cut -f1)"
  echo ""
  
  # Check if video is playable
  echo "Checking video properties with ffprobe:"
  ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$LATEST_VIDEO" 2>&1
  
  echo ""
  echo "✓ Partial save test complete!"
  echo ""
  echo "To play the video:"
  echo "  open \"$LATEST_VIDEO\""
else
  echo "✗ No partial video found!"
  echo ""
  echo "Last 20 lines of log:"
  tail -20 /tmp/partial-test.log
fi

echo ""

