import threading
import time

import cv2
from picamera2 import Picamera2

from util_functions import setup_logging


class LiveStreamCamera:
    def __init__(self, resolution, framerate, log_filename, log_level):
        self.resolution = resolution
        self.framerate = framerate
        self.picam2 = None
        self.shutdown_event = threading.Event()
        self.logger = setup_logging(log_filename, log_level)
        # For thread safety when accessing frames
        self.frame_lock = threading.Lock()
        self.latest_frame = None

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
            self.logger.info(
                f"Camera initialized with resolution {self.resolution} at {self.framerate} FPS"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error initializing camera: {e}")
            return False

    def get_frame(self):
        """Get the latest frame as JPEG bytes."""
        with self.frame_lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame

    def generate_frames(self):
        """Generate video frames for streaming."""
        while not self.shutdown_event.is_set():
            frame_data = self.get_frame()
            if frame_data is None:
                time.sleep(0.01)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_data + b"\r\n"
            )

    def capture_frames(self):
        """Continually capture frames from camera."""
        while not self.shutdown_event.is_set():
            try:
                frame = self.picam2.capture_array()
                _, buffer = cv2.imencode(".jpg", frame)
                with self.frame_lock:
                    self.latest_frame = buffer.tobytes()
            except Exception as e:
                self.logger.error(f"Error capturing frame: {e}")
                time.sleep(0.1)  # Avoid tight loop on error

    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Shutting down gracefully...")
        try:
            if self.picam2:
                self.picam2.stop()
                self.picam2.close()
                self.picam2 = None
                self.logger.info("Camera stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping camera: {e}")

    def run(self):
        """Run the frame capture loop."""
        if not self.initialize_camera():
            self.logger.error("Failed to initialize camera")
            return False

        try:
            self.logger.info("Starting frame capture")
            self.capture_frames()
        except Exception as e:
            self.logger.error(f"Error in frame capture loop: {e}")
            return False
        finally:
            self.cleanup()
        return True
