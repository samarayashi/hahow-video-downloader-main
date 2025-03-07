import requests
import yaml
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """配置類別，用於存儲所有設定參數"""
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
        self.api_base_url = f'https://api.sat.cool/api/v2/classroom/{config.course_num}'
        self.vimeo_api_url = f'{self.api_base_url}/vimeo'
        self.headers = self._init_headers()
    
    def _init_headers(self) -> Dict:
        """初始化請求頭"""
        return {
            'authorization': self.config.auth_token,
            'accept': 'application/json, text/plain, */*',
            'origin': 'https://sat.cool',
            'referer': 'https://sat.cool/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
        }
    
    def get_course_data(self) -> Dict:
        """獲取課程完整數據"""
        logger.info(f"正在獲取課程 {self.config.course_num} 的數據...")
        response = requests.get(self.api_base_url, headers=self.headers)
        
        if response.status_code != 200:
            logger.error(f"獲取課程數據失敗: {response.status_code} - {response.text}")
            raise Exception(f"獲取課程數據失敗: {response.status_code}")
        
        data = response.json()
        if not data.get('success'):
            logger.error(f"API返回錯誤: {data.get('message', '未知錯誤')}")
            raise Exception(f"API返回錯誤: {data.get('message', '未知錯誤')}")
        
        logger.info(f"成功獲取課程數據")
        return data['data']
    
    def get_video_data(self, part_id: str) -> Dict:
        """獲取影片詳細數據
        
        Args:
            part_id: 課程章節部分ID
        
        Returns:
            影片詳細數據
        """
        logger.info(f"正在獲取影片 {part_id} 的數據...")
        url = f"{self.vimeo_api_url}?course_chapter_part_id={part_id}"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            logger.error(f"獲取影片數據失敗: {response.status_code} - {response.text}")
            raise Exception(f"獲取影片數據失敗: {response.status_code}")
        
        data = response.json()
        if not data.get('success'):
            logger.error(f"API返回錯誤: {data.get('message', '未知錯誤')}")
            raise Exception(f"API返回錯誤: {data.get('message', '未知錯誤')}")
        
        logger.info(f"成功獲取影片 {part_id} 的數據")
        return data['data']

class CourseParser:
    """課程內容解析器"""
    
    @staticmethod
    def format_course_structure(course_data: Dict) -> str:
        """格式化課程結構為易讀的文本
        
        Args:
            course_data: 課程數據
            
        Returns:
            格式化後的課程結構文本
        """
        course_info = course_data.get('course', {})
        teacher = course_data.get('teacher', {})
        chapters = course_data.get('chapters', [])
        
        lines = []
        lines.append(f"課程名稱: {course_info.get('name', '未知')}")
        lines.append(f"講師: {teacher.get('nick_name', '未知')}")
        lines.append("")
        
        for chapter in chapters:
            lines.append(f"{chapter.get('name')} (總時長: {chapter.get('total_duration')} 秒)")
            
            for part in chapter.get('course_chapter_parts', []):
                lines.append(f"  {part.get('name')} ({part.get('duration')} 秒)")
                lines.append(f"  影片ID: {part.get('id')}")
                
                # 列出課程材料
                materials = part.get('materials', [])
                if materials:
                    lines.append(f"  課程材料:")
                    for material in materials:
                        lines.append(f"    - {material.get('name')}: {material.get('file_url')}")
            
            lines.append("")
        
        return "\n".join(lines)

class CourseDataCollector:
    """課程資料收集器，負責獲取和處理課程資訊"""
    
    def __init__(self, config: Config, client: SATCourseClient):
        self.config = config
        self.client = client
        self.base_path = Path(config.base_path)
    
    def process_course_content(self) -> Dict:
        """處理課程內容，根據配置決定行為"""
        if not self.config.fetch_course_content_json and self.config.download_from_existed_json:
            return self._load_json()
        
        course_data = self.client.get_course_data()
        
        if self.config.fetch_course_content_json:
            course_data = self._enrich_with_video_resources(course_data)
            self._save_json(course_data)
        
        return course_data
    
    def _load_json(self) -> Dict:
        """從JSON檔案讀取課程資料"""
        json_path = self.base_path / self.config.existed_json_name
        if not json_path.exists():
            raise FileNotFoundError(f"找不到指定的 JSON 檔案：{json_path}")
        
        logger.info(f"從已存在的 JSON 檔案讀取課程資料：{json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _enrich_with_video_resources(self, course_data: Dict) -> Dict:
        """豐富課程資料，添加影片資源資訊"""
        logger.info("開始獲取每個影片的資源資訊...")
        
        enriched_data = {
            'course_info': course_data,
            'videos_resources': {}
        }
        
        chapters = course_data.get('chapters', [])
        total_videos = sum(len(chapter.get('course_chapter_parts', [])) for chapter in chapters)
        processed_count = 0
        
        for chapter in chapters:
            chapter_name = chapter.get('name', 'Unknown Chapter')
            for part in chapter.get('course_chapter_parts', []):
                processed_count += 1
                part_id = part.get('id')
                part_name = part.get('name', f"Part_{processed_count}")
                
                if not part_id:
                    logger.warning(f"部分 {part_name} 沒有ID，跳過")
                    continue
                
                logger.info(f"獲取影片資源 ({processed_count}/{total_videos}): {part_name}")
                
                try:
                    video_data = self.client.get_video_data(part_id)
                    enriched_data['videos_resources'][part_id] = {
                        'chapter_name': chapter_name,
                        'part_name': part_name,
                        'resources': video_data
                    }
                except Exception as e:
                    logger.error(f"獲取影片 {part_name} 資源資訊時出錯: {str(e)}")
                    enriched_data['videos_resources'][part_id] = {
                        'chapter_name': chapter_name,
                        'part_name': part_name,
                        'resources': None,
                        'error': str(e)
                    }
        
        return enriched_data
    
    def _save_json(self, data: Dict):
        """保存數據到JSON文件"""
        course_name = self._get_course_name(data)
        course_name = FileUtils.sanitize_filename(course_name)
        
        output_dir = self.base_path / f"course_{self.config.course_num}"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        json_path = output_dir / f"{course_name}_resources.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"課程數據已保存到: {json_path}")
        self._create_course_structure(data, output_dir)
    
    def _create_course_structure(self, data: Dict, output_dir: Path):
        """創建課程結構文件"""
        structure_text = CourseParser.format_course_structure(
            data.get('course_info', data)
        )
        structure_path = output_dir / "course_structure.txt"
        
        with open(structure_path, 'w', encoding='utf-8') as f:
            f.write(structure_text)
        
        logger.info(f"課程結構已保存到: {structure_path}")
    
    def _get_course_name(self, data: Dict) -> str:
        """從數據中獲取課程名稱"""
        if 'course_info' in data:
            course_info = data['course_info']
        else:
            course_info = data
        
        if 'course' in course_info and 'name' in course_info['course']:
            return course_info['course']['name']
        return "unknown_course"

class CourseContentDownloader:
    """課程內容下載器，負責下載影片和字幕"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_path = Path(config.base_path)
    
    def download(self, course_data: Dict):
        """下載課程內容"""
        if not course_data:
            logger.error("無課程數據可下載")
            return
        
        course_info = course_data.get('course_info', course_data)
        videos_resources = course_data.get('videos_resources', {})
        course_name = self._get_course_name(course_info)
        
        logger.info(f"開始下載課程: {course_name}")
        course_dir = self._prepare_course_directory()
        
        self._process_chapters(course_info.get('chapters', []), course_dir, videos_resources)
        logger.info(f"課程 {course_name} 下載完成")
    
    def _process_chapters(self, chapters: List[Dict], course_dir: Path, videos_resources: Dict):
        """處理所有章節的下載"""
        for chapter_idx, chapter in enumerate(chapters, 1):
            chapter_name = chapter.get('name', f"Chapter_{chapter_idx}")
            chapter_dir = self._create_chapter_directory(course_dir, chapter_idx, chapter_name)
            
            logger.info(f"處理章節 {chapter_idx}/{len(chapters)}: {chapter_name}")
            self._process_chapter_parts(chapter, chapter_dir, videos_resources)
    
    def _process_chapter_parts(self, chapter: Dict, chapter_dir: Path, videos_resources: Dict):
        """處理章節中的所有部分"""
        parts = chapter.get('course_chapter_parts', [])
        for part_idx, part in enumerate(parts, 1):
            part_id = part.get('id')
            if not part_id:
                continue
            
            video_resources = videos_resources.get(str(part_id), {}).get('resources')
            if not video_resources:
                continue
            
            self._download_part_content(part, part_idx, video_resources, chapter_dir)
    
    def _download_part_content(self, part: Dict, part_idx: int, video_resources: Dict, chapter_dir: Path):
        """下載單個部分的內容（影片和字幕）"""
        part_name = part.get('name', f"Part_{part_idx}")
        video_url = self._get_video_url(video_resources)
        
        if video_url:
            self._download_video(video_url, part_idx, part_name, chapter_dir)
            self._download_subtitles(video_resources, part_idx, part_name, chapter_dir)
    
    def _get_video_url(self, video_resources: Dict) -> Optional[str]:
        """獲取最適合的影片URL"""
        video_links = {
            file_info['rendition']: file_info['link']
            for file_info in video_resources.get('files', [])
            if file_info.get('rendition') and file_info.get('link')
        }
        
        if not video_links:
            return None
        
        # 優先使用指定畫質
        if self.config.desired_quality in video_links:
            return video_links[self.config.desired_quality]
        
        # 其次使用自適應畫質
        if 'adaptive' in video_links:
            logger.info("    使用 adaptive 畫質")
            return video_links['adaptive']
        
        # 最後選擇中間畫質
        return self._select_middle_quality(video_links)
    
    def _select_middle_quality(self, video_links: Dict) -> str:
        """選擇中間畫質"""
        qualities = [q for q in video_links.keys() if q != 'adaptive']
        if not qualities:
            return None
        
        try:
            qualities.sort(key=lambda x: int(x.replace('p', '')))
            mid_quality = qualities[len(qualities) // 2]
            logger.info(f"    使用中間畫質: {mid_quality}")
            return video_links[mid_quality]
        except (ValueError, TypeError):
            quality = qualities[0]
            logger.warning(f"    無法解析畫質數值，使用畫質: {quality}")
            return video_links[quality]
    
    def _download_video(self, video_url: str, part_idx: int, part_name: str, chapter_dir: Path):
        """下載影片"""
        video_filename = f"{part_idx:02d}_{FileUtils.sanitize_filename(part_name)}.mp4"
        video_path = chapter_dir / video_filename
        
        if video_path.exists():
            logger.info(f"    影片已存在: {video_filename}")
            return
        
        logger.info(f"    下載影片: {video_filename}")
        self._download_file(video_url, video_path)
    
    def _download_subtitles(self, video_resources: Dict, part_idx: int, part_name: str, chapter_dir: Path):
        """下載字幕"""
        for subtitle in video_resources.get('texttracks', []):
            if subtitle.get('type') != 'subtitles':
                continue
            
            lang = subtitle.get('language', 'unknown')
            subtitle_url = subtitle.get('link')
            if not subtitle_url:
                continue
            
            subtitle_filename = f"{part_idx:02d}_{FileUtils.sanitize_filename(part_name)}_{lang}.vtt"
            subtitle_path = chapter_dir / subtitle_filename
            
            if not subtitle_path.exists():
                logger.info(f"    下載字幕: {subtitle_filename}")
                self._download_file(subtitle_url, subtitle_path)
    
    def _download_file(self, url: str, path: Path) -> bool:
        """下載文件的通用方法"""
        try:
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                
                if total_size > 0:
                    logger.info(f"    文件大小: {total_size / (1024 * 1024):.2f} MB")
                
                with open(path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            return True
        except Exception as e:
            logger.error(f"下載文件時出錯: {str(e)}")
            if path.exists():
                path.unlink()
            return False
    
    def _prepare_course_directory(self) -> Path:
        """準備課程下載目錄"""
        course_dir = self.base_path / f"course_{self.config.course_num}" / "videos"
        course_dir.mkdir(exist_ok=True, parents=True)
        return course_dir
    
    def _create_chapter_directory(self, course_dir: Path, chapter_idx: int, chapter_name: str) -> Path:
        """創建章節目錄"""
        chapter_dir = course_dir / f"{chapter_idx:02d}_{FileUtils.sanitize_filename(chapter_name)}"
        chapter_dir.mkdir(exist_ok=True, parents=True)
        return chapter_dir
    
    def _get_course_name(self, course_info: Dict) -> str:
        """獲取課程名稱"""
        if 'course' in course_info and 'name' in course_info['course']:
            return course_info['course']['name']
        return "unknown_course"

class FileUtils:
    """文件操作工具類"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名，移除不合法字符"""
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename

class CourseInfoDisplay:
    """課程資訊顯示器，負責格式化和顯示課程資訊"""
    
    @staticmethod
    def display_course_info(course_data: Dict):
        """顯示課程基本資訊
        
        Args:
            course_data: 課程資料字典
        """
        if 'course_info' not in course_data:
            logger.warning("無法顯示課程資訊：資料結構不完整")
            return
            
        course_info = course_data['course_info']
        course_name = course_info.get('course', {}).get('name', '未知課程')
        chapters = course_info.get('chapters', [])
        
        # 顯示基本資訊
        logger.info("\n=== 課程資訊 ===")
        logger.info(f"課程名稱: {course_name}")
        logger.info(f"章節數量: {len(chapters)}")
        
        # 計算總影片數
        total_videos = sum(len(chapter.get('course_chapter_parts', [])) for chapter in chapters)
        logger.info(f"影片總數: {total_videos}")
        
        # 顯示影片資源資訊
        if 'videos_resources' in course_data:
            videos_resources = course_data['videos_resources']
            total_resources = len(videos_resources)
            success_resources = sum(1 for v in videos_resources.values() if v.get('resources') is not None)
            logger.info("\n=== 影片資源資訊 ===")
            logger.info(f"總資源數: {total_resources}")
            logger.info(f"成功獲取: {success_resources}")
            logger.info(f"失敗數量: {total_resources - success_resources}")
        
        logger.info("=" * 30)

def downloader():
    """主函數"""
    try:
        # 載入配置
        config = Config.from_yaml('config.yaml')
        logger.info(f"已載入配置，課程編號: {config.course_num}")
        
        # 初始化客戶端和下載器
        client = SATCourseClient(config)
        collector = CourseDataCollector(config, client)
        downloader = CourseContentDownloader(config)
        
        # 處理課程內容
        course_data = collector.process_course_content()
        
        # 顯示課程資訊
        CourseInfoDisplay.display_course_info(course_data)
        
        # 根據配置決定是否下載
        if config.download_from_fetch_dict or config.download_from_existed_json:
            logger.info("開始下載課程內容...")
            downloader.download(course_data)
        else:
            logger.info("根據配置，不下載課程內容")
        
        logger.info("處理完成")
        
    except Exception as e:
        logger.error(f"發生錯誤: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    downloader()