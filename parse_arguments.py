import argparse
import os


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Timelapse camera script")

    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=os.path.join(os.path.expanduser("~"), "growcam", "images"),
        help="Base output directory for images (default: ~/growcam/images)",
    )

    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["png", "jpg", "jpeg"],
        default="png",
        help="Image file format (default: png)",
    )

    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=1,
        help="Interval between photos in minutes (default: 5)",
    )

    return parser.parse_args()
