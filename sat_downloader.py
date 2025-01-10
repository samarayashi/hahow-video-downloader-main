import requests
from requests.utils import cookiejar_from_dict
from bs4 import BeautifulSoup
import json
import os
import urllib.request
import yaml
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Config:
    """配置類別，用於存儲所有設定參數"""
    cookies_string: str
    course_num: int
    auth_token: str
    fetch_course_content_json: bool
    download_from_fetch_dict: bool
    download_from_existed_json: bool
    existed_json_name: str
    desired_quality: str
    base_path: str

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'Config':
        """從YAML檔案讀取配置"""
        with open(yaml_path, 'r', encoding='utf-8') as file:
            config_data = yaml.safe_load(file)
            return cls(
                cookies_string=config_data['cookies_string'],
                course_num=config_data['course']['course_num'],
                auth_token=config_data['auth']['token'],
                fetch_course_content_json=config_data['fetch_course_content_json'],
                download_from_fetch_dict=config_data['download_from_fetch_dict'],
                download_from_existed_json=config_data['download_from_existed_json'],
                existed_json_name=config_data['existed_json_name'],
                desired_quality=config_data['desired_quality'],
                base_path=config_data['base_path']
            )

class SATCourseClient:
    """SAT課程API客戶端"""
    def __init__(self, config: Config):
        self.config = config
        self.base_url = f'https://sat.cool/classroom/{config.course_num}'
        self.api_url = f'https://api.sat.cool/api/v2/classroom/{config.course_num}/vimeo'
        self.session = self._init_session()

    def _init_session(self) -> requests.Session:
        """初始化請求session"""
        session = requests.Session()
        cookies_dict = {
            key.strip(): value.strip() 
            for key, value in (cookie.split('=', 1) 
            for cookie in self.config.cookies_string.split(';'))
        }
        session.cookies = cookiejar_from_dict(cookies_dict)
        return session

    def get_course_html(self) -> str:
        """獲取課程HTML內容"""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/125.0.0.0'
        }
        response = self.session.get(self.base_url, headers=headers)
        response.raise_for_status()
        return response.text

    def get_video_data(self, chapter_id: str) -> Dict:
        """獲取視頻詳細資訊"""
        headers = {'Authorization': f'Bearer {self.config.auth_token}'}
        response = self.session.get(
            f"{self.api_url}?course_chapter_part_id={chapter_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

class CourseParser:
    """課程內容解析器"""
    @staticmethod
    def parse_course_content(html_content: str) -> Dict:
        """解析課程HTML內容"""
        soup = BeautifulSoup(html_content, 'html.parser')
        course_name = soup.select_one('.classroom-top-wrap a')
        course_name = course_name.get_text(strip=True) if course_name else '未知課程'

        chapters = []
        for chapter in soup.select('div[role="tablist"] .el-collapse-item'):
            chapter_data = {
                'chapter_title': chapter.select_one('.classroom-chapter-list__collapse-title').get_text(strip=True),
                'sub_chapters': [
                    {
                        'title': sub.select_one('.classroom-chapter-list__title').get_text(strip=True),
                        'id': sub.get('data-chapter-part')
                    }
                    for sub in chapter.select('[data-chapter-part]')
                ]
            }
            chapters.append(chapter_data)

        return {'course_name': course_name, 'chapters': chapters}

class CourseDownloader:
    """課程下載器"""
    def __init__(self, config: Config, client: SATCourseClient):
        self.config = config
        self.client = client

    def process_course_content(self) -> Dict:
        """處理課程內容並組織成JSON格式"""
        html_content = self.client.get_course_html()
        course_content = CourseParser.parse_course_content(html_content)
        return self._organize_course_data(course_content)

    def _organize_course_data(self, course_content: Dict) -> Dict:
        """組織課程資料"""
        organized_data = {
            'course_name': course_content['course_name'],
            'chapters': []
        }

        for chapter in course_content['chapters']:
            print(f"正在處理json_章節: {chapter['chapter_title']}")
            chapter_data = {
                'chapter_title': chapter['chapter_title'],
                'sub_chapters': []
            }

            for sub_chapter in chapter['sub_chapters']:
                video_data = self.client.get_video_data(sub_chapter['id'])
                if video_data.get('success'):
                    print(f"正在處理json_小節: {sub_chapter['title']}")
                    sub_chapter_data = {
                        'title': sub_chapter['title'],
                        'video_links': {
                            file['rendition']: file['link']
                            for file in video_data['data'].get('files', [])
                        },
                        'subtitle_links': {
                            track['language']: track['link']
                            for track in video_data['data'].get('texttracks', [])
                            if track['type'] == 'subtitles'
                        }
                    }
                    chapter_data['sub_chapters'].append(sub_chapter_data)

            organized_data['chapters'].append(chapter_data)
        
        print("json資料處理完成，正在保存...")
        self._save_json(organized_data)
        return organized_data

    def _save_json(self, data: Dict):
        """保存課程資料為JSON檔案"""
        filename = f"{data['course_name']}_video_resources.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"課程資料已保存至: {filename}")

    def download_content(self, course_data: Dict):
        """下載課程內容"""
        course_path = os.path.join(self.config.base_path, course_data['course_name'])
        os.makedirs(course_path, exist_ok=True)

        for chapter in course_data['chapters']:
            chapter_path = os.path.join(course_path, chapter['chapter_title'])
            os.makedirs(chapter_path, exist_ok=True)

            for sub_chapter in chapter['sub_chapters']:
                sub_path = os.path.join(chapter_path, sub_chapter['title'])
                os.makedirs(sub_path, exist_ok=True)

                # 下載影片
                if self.config.desired_quality in sub_chapter['video_links']:
                    video_url = sub_chapter['video_links'][self.config.desired_quality]
                    video_path = os.path.join(sub_path, f"{sub_chapter['title']}_{self.config.desired_quality}.mp4")
                    urllib.request.urlretrieve(video_url, video_path)
                    print(f"已下載影片: {video_path}")

                # 下載字幕
                for lang, subtitle_url in sub_chapter['subtitle_links'].items():
                    subtitle_path = os.path.join(sub_path, f"{sub_chapter['title']}_{lang}.vtt")
                    urllib.request.urlretrieve(subtitle_url, subtitle_path)
                    print(f"已下載字幕: {subtitle_path}")

def downloader():
    """主程式入口"""
    # 讀取配置
    config = Config.from_yaml('config.yaml')
    client = SATCourseClient(config)
    downloader = CourseDownloader(config, client)

    # 根據配置執行不同操作
    if config.fetch_course_content_json:
        course_data = downloader.process_course_content()
        if config.download_from_fetch_dict:
            downloader.download_content(course_data)

    if config.download_from_existed_json:
        with open(config.existed_json_name, 'r', encoding='utf-8') as f:
            existed_data = json.load(f)
            downloader.download_content(existed_data)