import os

from flask import Flask, Response, flash, redirect, render_template, request, url_for

from camera_manager import CameraManager

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Create camera manager instance
camera_manager = CameraManager()


@app.route("/")
def index():
    return render_template(
        "index.html",
        is_timelapse_active=camera_manager.is_timelapse_active,
        is_livestream_active=camera_manager.is_livestream_active,
    )


@app.route("/video_feed")
def video_feed():
    """Video streaming route - returns the actual stream data."""
    if (
        not camera_manager.is_livestream_active
        or not camera_manager.livestream_instance
    ):
        return "No active livestream", 404

    return Response(
        camera_manager.livestream_instance.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/livestream")
def livestream():
    """Video streaming page."""
    if (
        not camera_manager.is_livestream_active
        or not camera_manager.livestream_instance
    ):
        flash("No active livestream")
        return redirect(url_for("index"))

    return render_template(
        "livestream.html", is_livestream_active=camera_manager.is_livestream_active
    )


@app.route("/toggle_timelapse", methods=["POST"])
def toggle_timelapse():
    # If timelapse is active, stop it
    if camera_manager.is_timelapse_active:
        message = camera_manager.stop_timelapse()
        flash(message)
        return redirect(url_for("index"))

    # Stop livestream if active
    if camera_manager.is_livestream_active:
        message = camera_manager.stop_livestream()
        flash(message)

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

    # Start timelapse
    message = camera_manager.start_timelapse(output_dir, file_format, interval)
    flash(message)
    return redirect(url_for("index"))


@app.route("/toggle_livestream", methods=["POST"])
def toggle_livestream():
    # If livestream is active, stop it
    if camera_manager.is_livestream_active:
        message = camera_manager.stop_livestream()
        flash(message)
        return redirect(url_for("index"))

    # Stop timelapse if active
    if camera_manager.is_timelapse_active:
        message = camera_manager.stop_timelapse()
        flash(message)

    # Get form parameters
    try:
        resolution_width = int(request.form.get("resolution_width") or "1024")
        resolution_height = int(request.form.get("resolution_height") or "768")
        framerate = int(request.form.get("framerate") or "15")
    except ValueError as e:
        flash(f"Invalid input: {e}")
        return redirect(url_for("index"))

    # Start livestream
    message = camera_manager.start_livestream(
        resolution_width, resolution_height, framerate
    )
    flash(message)
    return redirect(url_for("index"))


if __name__ == "__main__":
    camera_manager.start_timelapse()
    app.run(host="0.0.0.0", debug=True, port=5000)
