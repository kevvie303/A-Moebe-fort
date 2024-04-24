import os
from pytube import YouTube
import subprocess

def download_video(url):
    yt = YouTube(url)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=".")
    return out_file

def convert_to_ogg(file_path):
    ogg_file_path = file_path.replace(".mp4", ".ogg")
    subprocess.run(['ffmpeg', '-i', file_path, '-c:a', 'libvorbis', ogg_file_path])
    os.remove(file_path)  # Remove the original download
    return ogg_file_path

def main(url):
    print("Downloading video...")
    video_file = download_video(url)
    print("Converting to OGG...")
    ogg_file = convert_to_ogg(video_file)
    print(f"Conversion complete. File saved as {ogg_file}")

def initialize(url="https://www.youtube.com/watch?v=example"):
    main(url)