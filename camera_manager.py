import os
import threading

from livestream import LiveStreamCamera
from timelapse import TimelapseCamera


class CameraManager:
    def __init__(self):
        # Global variables for camera instance and threads
        self.timelapse_thread = None
        self.timelapse_instance = None
        self.livestream_thread = None
        self.livestream_instance = None
        self.is_timelapse_active = False
        self.is_livestream_active = False

    def start_timelapse(self, output_dir=None, file_format="png", interval=5):
        """Start timelapse with given parameters."""
        if not output_dir:
            output_dir = os.path.join(os.path.expanduser("~"), "growcam", "images")

        if "~" in output_dir:
            output_dir = os.path.expanduser(output_dir)

        # Initialize the timelapse camera
        self.timelapse_instance = TimelapseCamera(
            output_dir=output_dir,
            file_format=file_format,
            interval=interval,
            log_filename="timelapse.log",
            log_level="INFO",
        )

        # Start camera in a separate thread
        self.timelapse_thread = threading.Thread(target=self.timelapse_instance.run)
        self.timelapse_thread.daemon = True
        self.timelapse_thread.start()
        self.is_timelapse_active = True
        return "Timelapse started"

    def stop_timelapse(self):
        """Stop the timelapse."""
        if not self.is_timelapse_active or not self.timelapse_instance:
            return "No active timelapse"

        # Signal to end the timelapse
        self.timelapse_instance.shutdown_event = True

        if self.timelapse_thread and self.timelapse_thread.is_alive():
            self.timelapse_thread.join(timeout=2.0)

        # Reset globals
        self.timelapse_instance = None
        self.timelapse_thread = None
        self.is_timelapse_active = False
        return "Timelapse stopped"

    def start_livestream(
        self, resolution_width=1024, resolution_height=768, framerate=15
    ):
        """Start livestream with given parameters."""
        # Initialize livestream camera
        self.livestream_instance = LiveStreamCamera(
            resolution=(resolution_width, resolution_height),
            framerate=framerate,
            log_filename="livestream.log",
            log_level="INFO",
        )

        # Start in a separate thread
        self.livestream_thread = threading.Thread(target=self.livestream_instance.run)
        self.livestream_thread.daemon = True
        self.livestream_thread.start()
        self.is_livestream_active = True
        return "Livestream started"

    def stop_livestream(self):
        """Stop the livestream."""
        if not self.is_livestream_active or not self.livestream_instance:
            return "No active livestream"

        # Signal to end the livestream
        self.livestream_instance.shutdown_event.set()

        if self.livestream_thread and self.livestream_thread.is_alive():
            self.livestream_thread.join(timeout=2.0)

        # Reset globals
        self.livestream_instance = None
        self.livestream_thread = None
        self.is_livestream_active = False
        return "Livestream stopped"

    def stop_all_cameras(self):
        """Stop all active cameras."""
        messages = []
        if self.is_timelapse_active:
            messages.append(self.stop_timelapse())
        if self.is_livestream_active:
            messages.append(self.stop_livestream())
        return messages
