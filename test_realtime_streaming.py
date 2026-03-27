#!/usr/bin/env python3
"""
Test Real-time Streaming - Quick Demo
Tunisia Football AI Level 3 SaaS

Tests the real-time streaming processor with a video file (simulating live stream)
"""

import sys
import time
from realtime_stream_processor import RealtimeStreamProcessor


def main():
    print("=" * 80)
    print("🇹🇳 Tunisia Football AI - Real-time Streaming Test")
    print("=" * 80)

    # Create processor
    print("\n1️⃣ Creating real-time processor...")
    processor = RealtimeStreamProcessor(fps=25)

    # Get source from command line or use default
    if len(sys.argv) > 1:
        source = sys.argv[1]
    else:
        # Default to video file (simulates stream)
        source = "input_videos/08fd33_4.mp4"
        print(f"   Using default video file: {source}")

    # Connect to stream
    print(f"\n2️⃣ Connecting to source: {source}")
    if not processor.connect_stream(source):
        print("❌ Failed to connect")
        return 1

    # Set up callbacks for real-time feedback
    alert_count = [0]  # Use list to modify in closure

    def on_alert(alert):
        alert_count[0] += 1
        priority_icon = "🔴" if alert.priority.value == 3 else "🟠" if alert.priority.value == 2 else "🟡"
        print(f"\n{priority_icon} ALERT #{alert_count[0]}: {alert.title}")
        print(f"   {alert.description}")
        print(f"   💡 {alert.recommendation}")

    def on_metrics(metrics):
        # Print metrics every 100 frames
        if metrics['frame_number'] % 100 == 0:
            print(f"\n📊 Frame {metrics['frame_number']}: "
                  f"{metrics['fps']:.1f} FPS, "
                  f"{metrics['players_tracked']} players, "
                  f"{'✅ Calibrated' if metrics['calibrated'] else '⏳ Calibrating...'}")

    processor.on_alert_generated = on_alert
    processor.on_metrics_updated = on_metrics

    # Start processing
    print("\n3️⃣ Starting real-time processing...")
    print("   📹 Processing frames...")
    print("   🚨 Alerts will appear as they're generated")
    print("   Press Ctrl+C to stop\n")

    processor.start_processing()

    try:
        # Process for 30 seconds or until stream ends
        start = time.time()
        while processor.is_running and (time.time() - start) < 30:
            time.sleep(0.5)

            # Get latest frame
            latest = processor.get_latest_frame()
            if latest and latest.frame_number % 250 == 0:
                print(f"\n⏱️  {time.time() - start:.1f}s elapsed...")

    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")

    # Stop processing
    print("\n4️⃣ Stopping processor...")
    processor.stop_processing()

    # Print final statistics
    print("\n" + "=" * 80)
    print("📊 FINAL STATISTICS")
    print("=" * 80)

    stats = processor.export_stream_stats()

    print(f"\n⏱️  Duration: {stats['streaming']['duration_seconds']:.1f}s")
    print(f"🎬 Frames Processed: {stats['streaming']['frames_processed']}")
    print(f"⚡ Average FPS: {stats['streaming']['average_fps']:.1f}")
    print(f"📐 Calibration: {'✅ Done' if stats['streaming']['calibrated'] else '❌ Not done'}")

    print(f"\n🚨 Total Alerts Generated: {alert_count[0]}")

    print(f"\n⚙️  Performance:")
    print(f"   Average processing: {stats['performance']['average_processing_ms']:.1f}ms/frame")
    print(f"   Max processing: {stats['performance']['max_processing_ms']:.1f}ms/frame")

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
