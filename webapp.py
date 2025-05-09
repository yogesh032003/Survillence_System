import argparse
import os
import time
import cv2
import numpy as np
import smtplib
import threading  
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from twilio.rest import Client
from flask import Flask, render_template, request, send_from_directory, Response
from werkzeug.utils import secure_filename
from ultralytics import YOLO
from datetime import datetime
import geocoder

app = Flask(__name__)

# ---------- Email Alert Configuration ----------
EMAIL_SENDER = 'Enter Email'
EMAIL_PASSWORD = 'Enter Password'
EMAIL_RECEIVER = 'Enter Receiver Email'

# ---------- Twilio SMS Configuration ----------
TWILIO_ACCOUNT_SID = 'ACCOUNT_SID'
TWILIO_AUTH_TOKEN = 'AUTH_TOKEN'
TWILIO_PHONE_NUMBER = '+PHONE_NUMBER'
DESTINATION_PHONE_NUMBER = '+DESTINATION_PHONE_NUMBER'


def get_current_location():
    try:
        g = geocoder.ip('me')
        if g.ok:
            return f"{g.city}, {g.state}, {g.country}"
    except Exception as e:
        print("Location error:", e)
    return "Unknown location"


def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def send_full_email_alert(violence_frames, video_path):
    now = get_current_time()
    location = get_current_location()

    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = "🚨 Violence Detected Alert"

    body = f"""
    Violence has been detected in the video.

    📍 Location: {location}
    🕒 Time: {now}

    Attached: key frames and a video clip.
    """
    msg.attach(MIMEText(body, 'plain'))

    for i, frame_path in enumerate(violence_frames):
        try:
            with open(frame_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="frame_{i+1}.jpg"')
                msg.attach(part)
        except Exception as e:
            print(f"Error attaching frame {frame_path}: {e}")

    try:
        if video_path and os.path.exists(video_path):
            with open(video_path, "rb") as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="violence_clip.mp4"')
                msg.attach(part)
    except Exception as e:
        print(f"Failed to attach video: {e}")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print("Email with video + frames sent!")
    except Exception as e:
        print(f"Failed to send email: {e}")


def send_sms_alert():
    now = get_current_time()
    location = get_current_location()

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"🚨 Violence detected!\n📍 {location}\n🕒 {now}",
            from_=TWILIO_PHONE_NUMBER,
            to=DESTINATION_PHONE_NUMBER
        )
        print("SMS alert sent! SID:", message.sid)
    except Exception as e:
        print(f"Failed to send SMS: {e}")


def send_alerts_async(frames, video_path):
    def task():
        send_full_email_alert(frames, video_path)
        send_sms_alert()
    threading.Thread(target=task).start()


@app.route("/")
def hello_world():
    return render_template('index.html')


def clear_output_video():
    output_path = os.path.join(os.path.dirname(__file__), 'output.mp4')
    if os.path.exists(output_path):
        os.remove(output_path)
        print("Cleared existing output.mp4")


clear_output_video()


@app.route("/", methods=["GET", "POST"])
def predict_img():
    violence_detected = False

    if request.method == "POST":
        if 'file' in request.files:
            f = request.files['file']
            basepath = os.path.dirname(__file__)
            upload_folder = os.path.join(basepath, 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, f.filename)
            f.save(filepath)

            file_extension = f.filename.rsplit('.', 1)[1].lower()
            model = YOLO('violence.pt')  # Class 0 = nonviolence, Class 1 = violence

            if file_extension == 'jpg':
                img = cv2.imread(filepath)
                results = model(img, save=True)
                boxes = results[0].boxes

                if boxes is not None and boxes.cls.shape[0] > 0:
                    for class_id in boxes.cls:
                        if int(class_id) == 1:
                            violence_detected = True
                            send_alerts_async([], '')  # Send image-based alert
                            break

                return render_template("index.html", violence_detected=violence_detected)

            elif file_extension == 'mp4':
                cap = cv2.VideoCapture(filepath)
                frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)

                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                output_path = os.path.join(basepath, 'output.mp4')
                out = cv2.VideoWriter(output_path, fourcc, 30.0, (frame_width, frame_height))

                violence_clip_path = os.path.join(basepath, 'violence_clip.mp4')
                if os.path.exists(violence_clip_path):
                    os.remove(violence_clip_path)

                clip_writer = None
                temp_frame_folder = os.path.join(basepath, 'violence_frames')
                os.makedirs(temp_frame_folder, exist_ok=True)
                for file in os.listdir(temp_frame_folder):
                    os.remove(os.path.join(temp_frame_folder, file))

                violence_frame_paths = []
                consecutive_violence_frames = 0
                threshold_consecutive = 5
                frame_count = 0
                violence_clip_saved = False

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    frame_count += 1

                    results = model(frame, save=True)
                    boxes = results[0].boxes

                    is_violence_frame = False
                    if boxes is not None and boxes.cls.shape[0] > 0:
                        for class_id in boxes.cls:
                            if int(class_id) == 1:
                                is_violence_frame = True
                                break

                    if is_violence_frame:
                        if clip_writer is None:
                            clip_writer = cv2.VideoWriter(violence_clip_path, fourcc, fps, (frame_width, frame_height))
                        clip_writer.write(frame)
                        consecutive_violence_frames += 1

                        if consecutive_violence_frames <= threshold_consecutive:
                            frame_path = os.path.join(temp_frame_folder, f"violence_frame_{frame_count}.jpg")
                            cv2.imwrite(frame_path, frame)
                            violence_frame_paths.append(frame_path)
                    else:
                        if consecutive_violence_frames >= threshold_consecutive and not violence_clip_saved:
                            violence_clip_saved = True
                            if clip_writer:
                                clip_writer.release()
                            send_alerts_async(violence_frame_paths, violence_clip_path)
                            violence_detected = True

                        consecutive_violence_frames = 0
                        clip_writer = None
                        violence_frame_paths = []

                    res_plotted = results[0].plot()
                    out.write(res_plotted)

                cap.release()
                out.release()

                return render_template("index.html", violence_detected=violence_detected, video=True)

    return render_template("index.html")


@app.route('/<path:filename>')
def display(filename):
    folder_path = 'runs/detect'
    subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    latest_subfolder = max(subfolders, key=lambda x: os.path.getctime(os.path.join(folder_path, x)))
    directory = os.path.join(folder_path, latest_subfolder)

    files = os.listdir(directory)
    if not files:
        return "No files found"

    latest_file = files[0]
    file_extension = latest_file.rsplit('.', 1)[1].lower()

    if file_extension == 'jpg':
        return send_from_directory(directory, latest_file)

    return "Invalid file format"


def get_frame():
    video = cv2.VideoCapture('output.mp4')
    while True:
        success, image = video.read()
        if not success:
            break
        _, jpeg = cv2.imencode('.jpg', image)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
        time.sleep(0.1)


@app.route("/video_feed")
def video_feed():
    return Response(get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flask app exposing YOLO models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    args = parser.parse_args()
    app.run(host="0.0.0.0", port=args.port, debug=True)
