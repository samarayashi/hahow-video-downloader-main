from sat_downloader import downloader as sat_downloader
from hahow_downloader import VideoDownloader as hahow_downloader
from config import global_config
if __name__ == "__main__":
    # 下載 hahow 的影片
    if global_config.get("course_url"):
        downloader = VideoDownloader()
        downloader.download_course_videos()
        
    # 下載 sat 的影片
    if global_config.get("cookies_string"):
        sat_downloader()