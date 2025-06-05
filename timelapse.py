import argparse
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta

from picamera2 import Picamera2

# Get the directory of the script to set up logging
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(script_dir, "timelapse.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # For systemd/journalctl
        logging.FileHandler(log_file),  # For logging to a file
    ],
)

# Create a logger
logger = logging.getLogger(__name__)

# Global variable for graceful shutdown
shutdown_event = False


def ensure_directory_exists(directory_path):
    """Create directory if it doesn't exist."""
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            logger.info(f"Created directory: {directory_path}")
        return True
    except OSError as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_event
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event = True


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Timelapse camera script")

    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="/home/daniel/growcam/images",
        help="Base output directory for images (default: /home/daniel/growcam/images)",
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


def main():
    args = parse_arguments()
    BASE_OUTPUT_DIR = args.output_dir
    FILE_FORMAT = args.format
    INTERVAL = args.interval
    global shutdown_event

    # Log the configuration
    logger.info(f"Configuration:")
    logger.info(f"  Output directory: {BASE_OUTPUT_DIR}")
    logger.info(f"  File format: {FILE_FORMAT}")
    logger.info(f"  Interval: {INTERVAL} minutes")

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    if not ensure_directory_exists(BASE_OUTPUT_DIR):
        return

    try:
        picam2 = Picamera2()
        camera_config = picam2.create_still_configuration()
        picam2.configure(camera_config)
        picam2.start()
        time.sleep(2)
        logger.info("Camera initialized successfully")
    except Exception as e:
        logger.error(f"Error during initialization of the camera: {e}")
        return

    try:
        logger.info(f"Start photo recording every {INTERVAL} minutes")

        start_time = datetime.now()
        next_capture_time = start_time

        while not shutdown_event:
            current_time = datetime.now()

            if current_time < next_capture_time:
                time.sleep(1)
                continue

            # Generate timestamp for the file name and the day folder
            timestamp = current_time.strftime("%Y-%m-%d_%H-%M-%S")
            day_folder = current_time.strftime("%Y-%m-%d")

            # Create day folder if it does not exist
            day_output_dir = os.path.join(BASE_OUTPUT_DIR, day_folder)
            if not ensure_directory_exists(day_output_dir):
                continue

            # File path for the picture
            file_path = os.path.join(day_output_dir, f"photo_{timestamp}.{FILE_FORMAT}")

            # Take picture
            try:
                picam2.capture_file(file_path)
                # logger.info(f"Picture taken: {file_path}")
            except Exception as e:
                logger.error(f"Error taking picture {file_path}: {e}")

            # Calculate next recording time
            next_capture_time += timedelta(minutes=INTERVAL)

            # If we are too late, take the photo NOW and calculate the next regular slot
            if next_capture_time <= datetime.now():
                # Berechne wie viele Intervalle seit Start vergangen sind
                minutes_since_start = int(
                    (datetime.now() - start_time).total_seconds() / 60
                )
                intervals_passed = (minutes_since_start // INTERVAL) + 1
                next_capture_time = start_time + timedelta(
                    minutes=intervals_passed * INTERVAL
                )
                logger.info(
                    f"Adjusting schedule: next photo at {next_capture_time.strftime('%H:%M:%S')}"
                )

    finally:
        try:
            picam2.stop()
        except:
            pass


if __name__ == "__main__":
    main()
