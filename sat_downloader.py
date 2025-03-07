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
    def format_duration(seconds: int) -> str:
        """將秒數格式化為分鐘和秒"""
        if not seconds:
            return "無時長資訊"
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}分{remaining_seconds}秒"
    
    @staticmethod
    def format_course_structure(course_data: Dict) -> str:
        """格式化課程結構為易讀的文本
        
        Args:
            course_data: 課程數據
            
        Returns:
            格式化後的課程結構文本
        """
        course_name = course_data.get('course_name', '未知課程')
        chapters = course_data.get('chapters', [])
        
        lines = []
        lines.append(f"課程名稱: {course_name}")
        lines.append("")
        
        total_duration = 0
        for chapter in chapters:
            chapter_title = chapter.get('chapter_title', '')
            chapter_duration = chapter.get('chapter_duration', 0)
            sub_chapters = chapter.get('sub_chapters', [])
            
            # 計算章節總時長
            chapter_total_duration = sum(sub.get('duration', 0) for sub in sub_chapters if 'error' not in sub)
            total_duration += chapter_total_duration
            
            lines.append(f"{chapter_title} (總時長: {CourseParser.format_duration(chapter_total_duration)})")
            
            for sub_chapter in sub_chapters:
                title = sub_chapter.get('title', '')
                duration = sub_chapter.get('duration', 0)
                
                if 'error' in sub_chapter:
                    lines.append(f"  {title} (獲取資訊失敗)")
                else:
                    lines.append(f"  {title} (時長: {CourseParser.format_duration(duration)})")
                
                # 列出課程材料
                materials = sub_chapter.get('materials', [])
                if materials:
                    lines.append(f"  課程材料:")
                    for material in materials:
                        lines.append(f"    - {material.get('name')}: {material.get('url')}")
            
            lines.append("")
        
        lines.append(f"課程總時長: {CourseParser.format_duration(total_duration)}")
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
        
        # 建立新的資料結構
        enriched_data = {
            'course_name': course_data.get('course', {}).get('name', 'unknown_course'),
            'chapters': []
        }
        
        chapters = course_data.get('chapters', [])
        total_videos = sum(len(chapter.get('course_chapter_parts', [])) for chapter in chapters)
        processed_count = 0
        
        for chapter in chapters:
            chapter_data = {
                'chapter_title': chapter.get('name', 'Unknown Chapter'),
                'chapter_duration': chapter.get('duration', 0),  # 添加章節時長
                'sub_chapters': []
            }
            
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
                    
                    # 整理影片連結
                    video_links = {}
                    for file_info in video_data.get('files', []):
                        rendition = file_info.get('rendition')
                        link = file_info.get('link')
                        if rendition and link:
                            video_links[rendition] = link
                    
                    # 整理字幕連結
                    subtitle_links = {}
                    for subtitle in video_data.get('texttracks', []):
                        if subtitle.get('type') == 'subtitles':
                            lang = subtitle.get('language', 'unknown')
                            link = subtitle.get('link')
                            if link:
                                subtitle_links[lang] = link
                    
                    # 建立子章節資料
                    sub_chapter = {
                        'title': part_name,
                        'duration': part.get('duration', 0),  # 添加部分時長
                        'video_links': video_links,
                        'subtitle_links': subtitle_links
                    }
                    
                    # 添加課程材料
                    materials = part.get('materials', [])
                    if materials:
                        sub_chapter['materials'] = [
                            {
                                'name': material.get('name'),
                                'url': material.get('file_url')
                            }
                            for material in materials
                        ]
                    
                    chapter_data['sub_chapters'].append(sub_chapter)
                    
                except Exception as e:
                    logger.error(f"獲取影片 {part_name} 資源資訊時出錯: {str(e)}")
                    chapter_data['sub_chapters'].append({
                        'title': part_name,
                        'error': str(e)
                    })
            
            enriched_data['chapters'].append(chapter_data)
        
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
        structure_text = CourseParser.format_course_structure(data)
        structure_path = output_dir / "course_structure.txt"
        
        with open(structure_path, 'w', encoding='utf-8') as f:
            f.write(structure_text)
        
        logger.info(f"課程結構已保存到: {structure_path}")
    
    def _get_course_name(self, data: Dict) -> str:
        """從數據中獲取課程名稱"""
        # 直接從新的數據結構中獲取課程名稱
        course_name = data.get('course_name', '')
        if course_name:
            return course_name
            
        # 如果找不到，嘗試從舊的數據結構中獲取（向後兼容）
        if 'course_info' in data:
            course_info = data['course_info']
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
        
        course_name = course_data.get('course_name', 'unknown_course')
        chapters = course_data.get('chapters', [])
        
        logger.info(f"開始下載課程: {course_name}")
        course_dir = self._prepare_course_directory()
        
        for chapter_idx, chapter in enumerate(chapters, 1):
            self._process_chapter(chapter, chapter_idx, course_dir)
        
        logger.info(f"課程 {course_name} 下載完成")
    
    def _process_chapter(self, chapter: Dict, chapter_idx: int, course_dir: Path):
        """處理單個章節的下載"""
        chapter_title = chapter.get('chapter_title', f"Chapter_{chapter_idx}")
        chapter_dir = self._create_chapter_directory(course_dir, chapter_idx, chapter_title)
        
        logger.info(f"處理章節 {chapter_idx}: {chapter_title}")
        
        for part_idx, part in enumerate(chapter.get('sub_chapters', []), 1):
            self._process_sub_chapter(part, part_idx, chapter_dir)
    
    def _process_sub_chapter(self, part: Dict, part_idx: int, chapter_dir: Path):
        """處理子章節的下載"""
        part_title = part.get('title', f"Part_{part_idx}")
        
        if 'error' in part:
            logger.error(f"    跳過影片 {part_title}: {part['error']}")
            return
        
        # 下載影片
        video_links = part.get('video_links', {})
        if video_links:
            video_url = self._get_video_url(video_links)
            if video_url:
                self._download_video(video_url, part_idx, part_title, chapter_dir)
        
        # 下載字幕
        subtitle_links = part.get('subtitle_links', {})
        if subtitle_links:
            self._download_subtitles(subtitle_links, part_idx, part_title, chapter_dir)
        
        # 下載課程材料
        materials = part.get('materials', [])
        if materials:
            self._download_materials(materials, part_idx, part_title, chapter_dir)
    
    def _get_video_url(self, video_links: Dict) -> Optional[str]:
        """獲取最適合的影片URL"""
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
    
    def _download_video(self, video_url: str, part_idx: int, part_title: str, chapter_dir: Path):
        """下載影片"""
        video_filename = f"{part_idx:02d}_{FileUtils.sanitize_filename(part_title)}.mp4"
        video_path = chapter_dir / video_filename
        
        if video_path.exists():
            logger.info(f"    影片已存在: {video_filename}")
            return
        
        logger.info(f"    下載影片: {video_filename}")
        self._download_file(video_url, video_path)
    
    def _download_subtitles(self, subtitle_links: Dict, part_idx: int, part_title: str, chapter_dir: Path):
        """下載字幕"""
        for lang, subtitle_url in subtitle_links.items():
            subtitle_filename = f"{part_idx:02d}_{FileUtils.sanitize_filename(part_title)}_{lang}.vtt"
            subtitle_path = chapter_dir / subtitle_filename
            
            if not subtitle_path.exists():
                logger.info(f"    下載字幕: {subtitle_filename}")
                self._download_file(subtitle_url, subtitle_path)
    
    def _download_materials(self, materials: List[Dict], part_idx: int, part_title: str, chapter_dir: Path):
        """下載課程材料"""
        materials_dir = chapter_dir / "materials"
        materials_dir.mkdir(exist_ok=True, parents=True)
        
        for material in materials:
            material_name = material.get('name', 'unknown')
            material_url = material.get('url')
            if not material_url:
                continue
            
            # 從URL中提取文件擴展名
            ext = material_url.split('.')[-1] if '.' in material_url else ''
            material_filename = f"{part_idx:02d}_{FileUtils.sanitize_filename(part_title)}_{FileUtils.sanitize_filename(material_name)}.{ext}"
            material_path = materials_dir / material_filename
            
            if not material_path.exists():
                logger.info(f"    下載課程材料: {material_filename}")
                self._download_file(material_url, material_path)
    
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
    
    def _create_chapter_directory(self, course_dir: Path, chapter_idx: int, chapter_title: str) -> Path:
        """創建章節目錄"""
        chapter_dir = course_dir / f"{chapter_idx:02d}_{FileUtils.sanitize_filename(chapter_title)}"
        chapter_dir.mkdir(exist_ok=True, parents=True)
        return chapter_dir

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
        course_name = course_data.get('course_name', '未知課程')
        chapters = course_data.get('chapters', [])
        
        # 顯示基本資訊
        logger.info("\n=== 課程資訊 ===")
        logger.info(f"課程名稱: {course_name}")
        logger.info(f"章節數量: {len(chapters)}")
        
        # 計算總影片數
        total_videos = sum(len(chapter.get('sub_chapters', [])) for chapter in chapters)
        logger.info(f"影片總數: {total_videos}")
        
        # 計算成功和失敗的資源數
        success_count = 0
        failed_count = 0
        for chapter in chapters:
            for sub_chapter in chapter.get('sub_chapters', []):
                if 'error' in sub_chapter:
                    failed_count += 1
                else:
                    success_count += 1
        
        if success_count + failed_count > 0:
            logger.info("\n=== 影片資源資訊 ===")
            logger.info(f"總資源數: {success_count + failed_count}")
            logger.info(f"成功獲取: {success_count}")
            logger.info(f"失敗數量: {failed_count}")
        
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