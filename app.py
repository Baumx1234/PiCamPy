import os
import threading

from flask import Flask, Response, flash, redirect, render_template, request, url_for

from livestream import LiveStreamCamera
from timelapse import TimelapseCamera

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Required for flash messages

# Global variables for camera instance and threads
timelapse_thread = None
timelapse_instance = None
livestream_thread = None
livestream_instance = None
is_timelapse_active = False
is_livestream_active = False


@app.route("/")
def index():
    return render_template(
        "index.html",
        is_timelapse_active=is_timelapse_active,
        is_livestream_active=is_livestream_active,
    )


@app.route("/video_feed")
def video_feed():
    """Video streaming route - returns the actual stream data."""
    if not is_livestream_active or not livestream_instance:
        return "No active livestream", 404

    return Response(
        livestream_instance.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/livestream")
def livestream():
    """Video streaming page."""
    if not is_livestream_active or not livestream_instance:
        flash("No active livestream")
        return redirect(url_for("index"))

    return render_template("livestream.html", is_livestream_active=is_livestream_active)


def stop_camera(camera_type):
    """Stop the specified camera type (timelapse or livestream)."""
    global timelapse_thread, timelapse_instance, livestream_thread, livestream_instance
    global is_timelapse_active, is_livestream_active

    if camera_type == "timelapse" and is_timelapse_active:
        # Signal to end the timelapse
        timelapse_instance.shutdown_event = True

        if timelapse_thread and timelapse_thread.is_alive():
            timelapse_thread.join(timeout=2.0)

        # Reset globals
        timelapse_instance = None
        timelapse_thread = None
        is_timelapse_active = False
        flash("Timelapse stopped")
        return True

    elif camera_type == "livestream" and is_livestream_active:
        # Signal to end the livestream
        livestream_instance.shutdown_event.set()

        if livestream_thread and livestream_thread.is_alive():
            livestream_thread.join(timeout=2.0)

        # Reset globals
        livestream_instance = None
        livestream_thread = None
        is_livestream_active = False
        flash("Livestream stopped")
        return True

    return False


@app.route("/toggle_timelapse", methods=["POST"])
def toggle_timelapse():
    global timelapse_thread, timelapse_instance, is_timelapse_active

    # If timelapse is active, stop it and return
    if stop_camera("timelapse"):
        return redirect(url_for("index"))

    # If livestream is active, stop it first
    stop_camera("livestream")

    # Start timelapse
    # Read configuration parameters from form
    output_dir = request.form.get("output_dir") or os.path.join(
        os.path.expanduser("~"), "growcam", "images"
    )
    if "~" in output_dir:
        output_dir = os.path.expanduser(output_dir)

    file_format = request.form.get("file_format", "png")

    try:
        interval = int(request.form.get("interval", "5"))
    except ValueError:
        interval = 5

    # Initialize the timelapse camera
    timelapse_instance = TimelapseCamera(
        output_dir=output_dir,
        file_format=file_format,
        interval=interval,
        log_filename="timelapse.log",
        log_level="INFO",
    )

    # Start camera in a separate thread
    timelapse_thread = threading.Thread(target=timelapse_instance.run)
    timelapse_thread.daemon = True
    timelapse_thread.start()
    is_timelapse_active = True
    flash("Timelapse started")

    return redirect(url_for("index"))


@app.route("/toggle_livestream", methods=["POST"])
def toggle_livestream():
    global livestream_thread, livestream_instance, is_livestream_active

    # If livestream is active, stop it and return
    if stop_camera("livestream"):
        return redirect(url_for("index"))

    # If timelapse is active, stop it first
    stop_camera("timelapse")

    try:
        resolution_width_val = request.form.get("resolution_width") or "1024"
        resolution_height_val = request.form.get("resolution_height") or "768"
        framerate_val = request.form.get("framerate") or "15"

        resolution_width = int(resolution_width_val)
        resolution_height = int(resolution_height_val)
        framerate = int(framerate_val)
    except ValueError as e:
        flash(f"Invalid input: {e}")
        return redirect(url_for("index"))

    # Initialize livestream camera
    livestream_instance = LiveStreamCamera(
        resolution=(resolution_width, resolution_height),
        framerate=framerate,
        log_filename="livestream.log",
        log_level="INFO",
    )

    # Start in a separate thread
    livestream_thread = threading.Thread(target=livestream_instance.run)
    livestream_thread.daemon = True
    livestream_thread.start()
    is_livestream_active = True
    flash("Livestream started")

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)
