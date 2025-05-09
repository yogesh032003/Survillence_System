# 🛡️ Intelligent Video Surveillance System

An advanced AI-powered surveillance system for real-time threat detection, anomaly recognition, and actionable alerts using YOLOv9 and Flask. Designed to help ensure safety and quick response in sensitive environments using real-time video feeds from webcams, IP cameras, or uploaded media.

## 🚀 Features

- 🎥 **Real-time Object & Threat Detection** using YOLOv9
- 📹 **Supports Webcam, RTSP (IP Cameras), Image & Video Uploads**
- 🧠 **Violence Detection Meter**: Triggers alerts only when continuous violence is detected for 5 seconds
- 📊 **Analytics Dashboard**: Live statistics with total scans, defected detections, OK status, and auto-updating charts
- 💾 **Short Clip Storage**: Saves short video clips of detection events
- 🔐 **User Authentication System** with role management (admin, viewer)
- 🌐 **Cloud Upload Option** for detected events
- 📍 **Geo-Tagged Alerts with Timestamps**
- 🔔 **Real-Time Notifications** and configurable alert thresholds
- ⚙️ **Modular Flask Structure** for scalability and clean codebase
- 📁 **Session Persistence** using Redis or FileStorage

---

## 🛠️ Tech Stack

- **Backend**: Flask, OpenCV, YOLOv9
- **Frontend**: HTML, CSS, JavaScript (Chart.js for graphs)
- **Authentication**: Flask Sessions
- **Database**: Redis or Local FileSystem for storing sessions & event logs
- **Visualization**: Chart.js for dynamic analytics
- **Deployment**: Localhost / Cloud-Ready

---

## 📦 Setup Instructions

```bash
# 1. Clone the repository
git clone https://github.com/your-username/Survillence_System.git
cd Survillence-System

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies

# 4. Run the Flask server
python webapp.py
