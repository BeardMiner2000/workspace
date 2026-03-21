#!/bin/bash

# Grant Accessibility Permission to StillMode
# This opens System Settings to the Accessibility pane

echo "🌙 Still Mode — Accessibility Permission Setup"
echo ""
echo "Still Mode needs permission to hide other apps while you focus."
echo "System Settings will open to the Accessibility page."
echo ""
echo "Steps:"
echo "  1. Click the 🔒 lock (if locked)"
echo "  2. Click the ➕ button"
echo "  3. Navigate to: ~/Library/Developer/Xcode/DerivedData/"
echo "  4. Find: StillMode-biajbqnduufjnwdzfpdbdllcwylf/Build/Products/Debug/"
echo "  5. Select 'StillMode.app' and click 'Open'"
echo ""
echo "Opening System Settings..."
sleep 1

# Open System Settings to Privacy & Security > Accessibility
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"

echo ""
echo "Once you've added StillMode to Accessibility, press Enter here to test it."
read -p "Ready? > "

# Kill and relaunch StillMode
echo "Relaunching Still Mode..."
killall StillMode 2>/dev/null
sleep 1

APP_PATH="/Users/jl/Library/Developer/Xcode/DerivedData/StillMode-biajbqnduufjnwdzfpdbdllcwylf/Build/Products/Debug/StillMode.app"
if [ -d "$APP_PATH" ]; then
    open "$APP_PATH"
    echo "✅ Launched! Look for 🌙 in your menubar (top right)."
else
    echo "❌ App not found. Did you build it?"
fi
