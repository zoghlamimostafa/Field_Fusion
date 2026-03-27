#!/usr/bin/env python3
"""
Generate a seed pitch-calibration profile from the first frame of a video.
The output JSON can be edited manually and will be picked up by the main pipeline.
"""

import argparse
import os
import cv2

from pitch_detector import PitchDetector


def main():
    parser = argparse.ArgumentParser(description='Generate a seed pitch calibration profile.')
    parser.add_argument('video_path', help='Path to the input video')
    parser.add_argument(
        '--output-profile',
        help='Output JSON profile path. Defaults to calibration_profiles/<video_name>.json',
    )
    parser.add_argument(
        '--preview-image',
        help='Optional preview image path. Defaults to outputs/<video_name>_calibration_preview.jpg',
    )
    args = parser.parse_args()

    video_name = os.path.splitext(os.path.basename(args.video_path))[0]
    output_profile = args.output_profile or os.path.join('calibration_profiles', f'{video_name}.json')
    preview_image = args.preview_image or os.path.join('outputs', f'{video_name}_calibration_preview.jpg')

    capture = cv2.VideoCapture(args.video_path)
    success, frame = capture.read()
    capture.release()

    if not success or frame is None:
        raise RuntimeError(f'Could not read first frame from {args.video_path}')

    detector = PitchDetector()
    profile = detector.build_calibration_profile(frame, video_path=args.video_path)
    detector.save_calibration_profile(profile, output_profile)

    os.makedirs(os.path.dirname(preview_image), exist_ok=True)
    preview = detector.draw_named_points(frame, profile.get('image_points', {}))
    cv2.imwrite(preview_image, preview)

    print(f'Saved calibration profile: {output_profile}')
    print(f'Saved preview image: {preview_image}')
    print('Detected points:')
    for key, point in profile.get('image_points', {}).items():
        print(f'  {key}: {point}')


if __name__ == '__main__':
    main()
