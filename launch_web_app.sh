#!/bin/bash
# Tunisia Football AI - Web Application Launcher
# Quick start script for the Gradio web interface

echo "=================================================================="
echo "🇹🇳 TUNISIA FOOTBALL AI - WEB APPLICATION 🇹🇳"
echo "=================================================================="
echo ""

# Activate virtual environment
source venv/bin/activate

# Check if model is cached
if [ ! -d "$HOME/.cache/huggingface/hub/models--uisikdag--yolo-v8-football-players-detection" ]; then
    echo "📥 First run: Downloading football model from HuggingFace..."
    echo "   This may take a few minutes..."
fi

echo "🚀 Starting web interface..."
echo "🌐 Access URL: http://localhost:7862"
echo ""
echo "📊 Features:"
echo "   ✓ Upload match videos"
echo "   ✓ Real-time analysis with football AI"
echo "   ✓ Player/goalkeeper/referee detection"
echo "   ✓ Speed & distance metrics"
echo "   ✓ Team heatmaps"
echo "   ✓ Pass/shot detection"
echo "   ✓ Download reports (JSON/CSV/HTML)"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================================================="
echo ""

python gradio_complete_app.py
