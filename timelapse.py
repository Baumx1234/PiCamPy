import os
import time
from datetime import datetime, timedelta

from picamera2 import Picamera2

from util_functions import setup_logging


class TimelapseCamera:
    def __init__(self, output_dir, file_format, interval, log_filename, log_level):
        self.output_dir = output_dir
        self.file_format = file_format
        self.interval = interval
        self.shutdown_event = False
        self.picam2 = None
        self.start_time = None

        # Setup logging
        self.logger = setup_logging(log_filename, log_level)

        # Log configuration
        self.logger.info("Configuration:")
        self.logger.info(f"  Output directory: {self.output_dir}")
        self.logger.info(f"  File format: {self.file_format}")
        self.logger.info(f"  Interval: {self.interval} minutes")

    def ensure_directory_exists(self, directory_path):
        """Create directory if it doesn't exist."""
        try:
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
                self.logger.info(f"Created directory: {directory_path}")
            return True
        except OSError as e:
            self.logger.error(f"Error creating directory {directory_path}: {e}")
            return False

    def initialize_camera(self):
        """Initialize the camera."""
        try:
            self.picam2 = Picamera2()
            camera_config = self.picam2.create_still_configuration()
            self.picam2.configure(camera_config)
            self.picam2.start()
            time.sleep(2)
            self.logger.info("Camera initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during initialization of the camera: {e}")
            return False

    def take_photo(self, file_path):
        """Take a photo and save it to the specified path."""
        try:
            self.picam2.capture_file(file_path)
            self.logger.info(f"Picture taken: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error taking picture {file_path}: {e}")
            return False

    def calculate_next_capture_time(self, current_next_time):
        """Calculate the next capture time, handling schedule adjustments."""
        next_time = current_next_time + timedelta(minutes=self.interval)

        # If we are too late, calculate the next regular slot
        if next_time <= datetime.now():
            minutes_since_start = int(
                (datetime.now() - self.start_time).total_seconds() / 60
            )
            intervals_passed = (minutes_since_start // self.interval) + 1
            next_time = self.start_time + timedelta(
                minutes=intervals_passed * self.interval
            )
            self.logger.info(
                f"Adjusting schedule: next photo at {next_time.strftime('%H:%M:%S')}"
            )

        return next_time

    def run(self):
        """Main execution loop."""
        # Ensure output directory exists
        if not self.ensure_directory_exists(self.output_dir):
            return False

        # Initialize camera
        if not self.initialize_camera():
            return False

        try:
            self.logger.info(f"Start photo recording every {self.interval} minutes")

            self.start_time = datetime.now()
            next_capture_time = self.start_time

            while not self.shutdown_event:
                current_time = datetime.now()

                if current_time < next_capture_time:
                    time.sleep(1)
                    continue

                # Generate timestamp for the file name and the day folder
                timestamp = current_time.strftime("%Y-%m-%d_%H-%M-%S")
                day_folder = current_time.strftime("%Y-%m-%d")

                # Create day folder if it does not exist
                day_output_dir = os.path.join(self.output_dir, day_folder)
                if not self.ensure_directory_exists(day_output_dir):
                    continue

                # File path for the picture
                file_path = os.path.join(
                    day_output_dir, f"photo_{timestamp}.{self.file_format}"
                )

                # Take picture
                self.take_photo(file_path)

                # Calculate next recording time
                next_capture_time = self.calculate_next_capture_time(next_capture_time)
        finally:
            self.cleanup()
        return True

    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Shutting down gracefully...")
        try:
            if self.picam2:
                self.picam2.stop()
                self.picam2.close()
                self.picam2 = None
        except Exception as e:
            self.logger.error(f"Error stopping camera: {e}")
