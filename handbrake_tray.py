
import os
import time
import subprocess
from pathlib import Path
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from win10toast import ToastNotifier

WATCH_FOLDER = Path("C:/HANDBRAKE/MKV")
OUTPUT_FOLDER = Path("C:/HANDBRAKE/MP4")
ARCHIVE_FOLDER = Path("C:/HANDBRAKE/ARCHIVE")
LOG_FILE = Path("C:/HANDBRAKE/log.txt")

notifier = ToastNotifier()

def log(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def notify(title, msg):
    notifier.show_toast(title, msg, duration=5, threaded=True)

def run_handbrake(input_file: Path):
    filename = input_file.stem
    output_file = OUTPUT_FOLDER / f"{filename}.mp4"
    archive_file = ARCHIVE_FOLDER / input_file.name

    if output_file.exists():
        log(f"SKIPPED: {input_file.name} — MP4 already exists")
        return

    try:
        result = subprocess.run([
            "HandBrakeCLI",
            "-i", str(input_file),
            "-o", str(output_file),
            "--encoder", "nvenc_h264",
            "--encoder-preset", "slow",
            "-q", "21",
            "-B", "160",
            "--optimize",
            "--subtitle", "1",
            "--subtitle-burned",
            "--markers"
        ], capture_output=True, text=True)

        if result.returncode == 0 and output_file.exists():
            input_file.rename(archive_file)
            log(f"SUCCESS: Converted {input_file.name} and moved to ARCHIVE")
            notify("HandBrake Tray", f"✅ {filename} converted.")
        else:
            log(f"ERROR: Failed to convert {input_file.name}\n{result.stderr}")
            notify("HandBrake Tray", f"❌ {filename} failed to convert.")
    except Exception as e:
        log(f"EXCEPTION: {input_file.name} - {e}")
        notify("HandBrake Tray", f"⚠️ Error: {filename}")

class MKVHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(".mkv"):
            print(f"[DEBUG] New MKV file detected: {event.src_path}")
            time.sleep(5)
            run_handbrake(Path(event.src_path))


def create_icon_image():
    img = Image.new("RGB", (64, 64), "black")
    d = ImageDraw.Draw(img)
    d.rectangle([16, 16, 48, 48], fill="red")
    return img

def tray_app():
    icon = Icon("HandBrakeTray")
    icon.icon = create_icon_image()
    icon.menu = Menu(MenuItem("Exit", lambda icon, item: icon.stop()))
    icon.title = "HandBrake Watcher"

    def start_observer():
        event_handler = MKVHandler()
        observer = Observer()
        observer.schedule(event_handler, str(WATCH_FOLDER), recursive=False)
        observer.start()
        log("Tray app started and watching for new MKV files.")
        try:
            while observer.is_alive():
                time.sleep(1)
        finally:
            observer.stop()
            observer.join()

    Thread(target=start_observer, daemon=True).start()
    icon.run()

if __name__ == "__main__":
    for folder in [WATCH_FOLDER, OUTPUT_FOLDER, ARCHIVE_FOLDER]:
        os.makedirs(folder, exist_ok=True)
    tray_app()
