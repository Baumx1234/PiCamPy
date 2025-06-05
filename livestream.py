import argparse
import logging
import signal
import sys
import threading
import time

import cv2
from flask import Flask, Response
from picamera2 import Picamera2

from util_functions import setup_logging


class LiveStreamCamera:
    def __init__(
        self, resolution, framerate, ip_address, port, log_filename, log_level
    ):
        self.resolution = resolution
        self.framerate = framerate
        self.ip_address = ip_address
        self.port = port
        self.picam2 = None
        self.shutdown_event = threading.Event()
        self.logger = setup_logging(log_filename, log_level)
        self.app = Flask(__name__)

        # Register signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

        self.setup_routes()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()

    def setup_routes(self):
        """Register Flask routes."""

        @self.app.route("/")
        def index():
            return Response(
                self.generate_frames(),
                mimetype="multipart/x-mixed-replace; boundary=frame",
            )

    def initialize_camera(self):
        """Initialize the camera with the specified resolution and framerate."""
        try:
            self.picam2 = Picamera2()
            camera_config = self.picam2.create_preview_configuration(
                {
                    "size": self.resolution,
                    "format": "RGB888",
                },
                controls={"FrameRate": self.framerate},
            )
            self.picam2.configure(camera_config)
            self.picam2.start()
            time.sleep(2)
            return True
        except Exception as e:
            self.logger.error(f"Error initializing camera: {e}")
            return False

    def generate_frames(self):
        """Generate video frames for streaming."""
        while not self.shutdown_event.is_set():
            try:
                frame = self.picam2.capture_array()
                _, buffer = cv2.imencode(".jpg", frame)
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                )
                time.sleep(0.01)
            except Exception as e:
                self.logger.error(f"Error generating frame: {e}")
                break

    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Shutting down gracefully...")
        try:
            if self.picam2:
                self.picam2.stop()
                self.logger.info("Camera stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping camera: {e}")

    def run(self):
        """Run the Flask application."""
        if not self.initialize_camera():
            return False

        try:
            self.logger.info(
                f"Starting livestream server on http://{self.ip_address}:{self.port}"
            )

            # Start Flask in a separate thread
            server_thread = threading.Thread(
                target=self.app.run,
                kwargs={
                    "host": self.ip_address,
                    "port": self.port,
                    "debug": False,
                    "threaded": True,
                    "use_reloader": False,
                },
            )
            server_thread.daemon = True
            server_thread.start()

            # Wait for shutdown signal
            while not self.shutdown_event.is_set():
                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error running the application: {e}")
            return False
        finally:
            self.cleanup()
        return True


def parse_arguments():
    """Parse command line arguments for livestream script."""
    parser = argparse.ArgumentParser(description="Livestream camera script")

    parser.add_argument(
        "--resolution",
        "-r",
        type=str,
        default="1024x768",
        help="Camera resolution as WIDTHxHEIGHT (default: 1024x768)",
    )

    parser.add_argument(
        "--framerate",
        "-fps",
        type=int,
        default=15,
        help="Camera framerate (default: 15)",
    )

    parser.add_argument(
        "--ip-address",
        "-ip",
        type=str,
        default="0.0.0.0",
        help="IP address to bind the Flask server (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=5000,
        help="Port for the Flask server (default: 5000)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    return parser.parse_args()


def parse_resolution(resolution_str):
    """Parse resolution string like '1024x768' to tuple (1024, 768)."""
    try:
        width, height = resolution_str.split("x")
        return (int(width), int(height))
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid resolution format: {resolution_str}. Use WIDTHxHEIGHT (e.g., 1024x768)"
        )


def main():
    args = parse_arguments()

    # Parse resolution string to tuple
    resolution = parse_resolution(args.resolution)
    log_level = getattr(logging, args.log_level.upper())

    camera = LiveStreamCamera(
        resolution=resolution,
        framerate=args.framerate,
        ip_adress=args.ip_address,
        port=args.port,
        log_filename="livestream.log",
        log_level=log_level,
    )
    success = camera.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
