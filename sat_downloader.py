import requests
from requests.utils import cookiejar_from_dict
from bs4 import BeautifulSoup
import json
import os
import urllib.request
import yaml

# 從 YAML 文件載入配置
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# 是某抓取課程json
fetch_course_content_json = config['fetch_course_content_json']

# 是否直接從這次提取的json文件中下載
download_from_fetch_dict = config['download_from_fetch_dict']

# 是否從已存在的json文件中下載
download_from_existed_json = config['download_from_existed_json']
existed_json_name = config['existed_json_name']

# 下載影片的品質
desired_quality = config['desired_quality']
# 下載路徑
download_path = config['base_path']

# 提取課程信息
COURSE_NUM = config['course']['course_num']
COURSE_URL = 'https://sat.cool/classroom/{}'.format(COURSE_NUM)
CONTENT_BASE_URL = 'https://api.sat.cool/api/v2/classroom/{}/vimeo'.format(COURSE_NUM)

# 提取 Bearer token
auth_token = config['auth']['token']


def parse_cookies_string_to_dict(raw_cookie_string):
    """將 raw cookie string 轉換為字典格式"""
    cookies_dict = {}
    for cookie in raw_cookie_string.split(';'):
        key, value = cookie.strip().split('=', 1)
        cookies_dict[key] = value
    return cookies_dict

def get_course_html(course_url, cookies_dict):


    # 定義請求頭
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7,ja;q=0.6,lg;q=0.5',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Referer': 'https://www.google.com/',
        'Sec-Ch-Ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }
    
    # 創建會話
    session = requests.Session()
    session.cookies = cookiejar_from_dict(cookies_dict)

    # 發送 GET 請求
    response = session.get(course_url, headers=headers)
            
    return response.text

def extract_chapter_content(html_content):
    # 解析 HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # 提取課程名稱
    course_name_tag = soup.select_one('.classroom-top-wrap a')
    course_name = course_name_tag.get_text(strip=True) if course_name_tag else '未知課程名稱'

    # 提取章節信息
    chapters = []
    tablist = soup.select_one('div[role="tablist"]')

    if (tablist):
        for chapter in tablist.select('.el-collapse-item'):
            chapter_title_tag = chapter.select_one('.classroom-chapter-list__collapse-title')
            chapter_title = chapter_title_tag.get_text(strip=True) if chapter_title_tag else '未知章節標題'
            
            sub_chapters = []
            for sub_chapter in chapter.select('[data-chapter-part]'):
                sub_chapter_title_tag = sub_chapter.select_one('.classroom-chapter-list__title')
                sub_chapter_title = sub_chapter_title_tag.get_text(strip=True) if sub_chapter_title_tag else '未知子章節標題'
                sub_chapter_id = sub_chapter.get('data-chapter-part', '未知ID')
                
                sub_chapters.append({
                    'title': sub_chapter_title,
                    'id': sub_chapter_id
                })
            
            chapters.append({
                'chapter_title': chapter_title,
                'sub_chapters': sub_chapters
            })

    # 構建最終的課程信息字典
    course_info = {
        'course_name': course_name,
        'chapters': chapters
    }
    return course_info

def fetch_vimeo_data(base_url, course_chapter_part_id, auth_token):
    """
    發送帶有 Authorization 的 GET 請求，並返回響應數據。

    :param base_url: str, API 端點的基礎 URL
    :param course_chapter_part_id: str or int, 課程章節部分的 ID
    :param auth_token: str, Authorization 所需的 Bearer token
    :return: dict, 返回的 JSON 數據，若請求失敗則返回空字典
    """
    url = f"{base_url}?course_chapter_part_id={course_chapter_part_id}"
    headers = {
        'Authorization': f'Bearer {auth_token}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 如果請求失敗，拋出異常
        return response.json()  # 返回 JSON 數據
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return {}

def organize_course_data2json(chapter_content, export_json=True):
    """
    整理課程數據為指定的 JSON 結構。

    :param course_data: dict, 課程數據
    :return: dict, 整理後的 JSON 結構
    """
    course_name = chapter_content['course_name']
    chapters = chapter_content['chapters']

    organized_data = {
        "course_name": course_name,
        "chapters": []
    }
    
    embed_links_data = {
        "course_name": course_name,
        "chapters": []
    }
    
    for chapter in chapters:
        chapter_title = chapter['chapter_title']
        sub_chapters = chapter['sub_chapters']

        chapter_data = {
            "chapter_title": chapter_title,
            "sub_chapters": []
        }
        
        embed_links_chapter_data = {
            "chapter_title": chapter_title,
            "sub_chapters": []
        }

        for sub_chapter in sub_chapters:
            sub_chapter_title = sub_chapter['title']
            sub_chapter_id = sub_chapter['id']
            video_links = {}
            subtitle_links = {}
            embed_link = None

            vimeo_data = fetch_vimeo_data(CONTENT_BASE_URL, sub_chapter_id, auth_token)
            if vimeo_data.get('success'):
                print(f'sub_chapter{sub_chapter} success')
                files = vimeo_data['data'].get('files', [])
                texttracks = vimeo_data['data'].get('texttracks', [])
                embed_link = vimeo_data['data'].get('player_embed_url')


                for file in files:
                    rendition = file['rendition']
                    link = file['link']
                    video_links[rendition] = link

                for texttrack in texttracks:
                    if texttrack['type'] == 'subtitles':
                        language = texttrack['language']
                        link = texttrack['link']
                        subtitle_links[language] = link

            sub_chapter_data = {
                "title": sub_chapter_title,
                "video_links": video_links,
                "subtitle_links": subtitle_links
            }
            
            embed_links_sub_chapter_data = {
                "title": sub_chapter_title,
                "player_embed_url": embed_link
            }


            chapter_data['sub_chapters'].append(sub_chapter_data)
            embed_links_chapter_data['sub_chapters'].append(embed_links_sub_chapter_data)


        organized_data['chapters'].append(chapter_data)
        embed_links_data['chapters'].append(embed_links_chapter_data)


        
    if export_json:
        output_filename = f"{organized_data['course_name']}_video_resources.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(organized_data, f, indent=4, ensure_ascii=False)
        
        embed_links_output_filename = f"{embed_links_data['course_name']}_embed_links.json"
        with open(embed_links_output_filename, 'w', encoding='utf-8') as f:
                json.dump(embed_links_data, f, indent=4, ensure_ascii=False)


    print(f"Organized data saved to {output_filename}")
    print(f"Embed links data saved to {embed_links_output_filename}")

    return organized_data

def download_videos_and_subtitles(data, quality='360p', base_path='./'):
    course_name = data['course_name']
    chapters = data['chapters']
    
    course_path = os.path.join(base_path, course_name)
    os.makedirs(course_path, exist_ok=True)
    
    for chapter in chapters:
        chapter_title = chapter['chapter_title']
        chapter_path = os.path.join(course_path, chapter_title)
        os.makedirs(chapter_path, exist_ok=True)
        
        sub_chapters = chapter['sub_chapters']
        for sub_chapter in sub_chapters:
            title = sub_chapter['title']
            video_links = sub_chapter['video_links']
            subtitle_links = sub_chapter['subtitle_links']
            
            sub_chapter_path = os.path.join(chapter_path, title)
            os.makedirs(sub_chapter_path, exist_ok=True)
            
            # 下載影片
            for quality_key, video_link in video_links.items():
                if quality_key == quality:
                    video_filename = os.path.join(sub_chapter_path, f'{title}_{quality}.mp4')
                    urllib.request.urlretrieve(video_link, video_filename)
                    
            # 下載字幕
            for lang, subtitle_link in subtitle_links.items():
                subtitle_filename = os.path.join(sub_chapter_path, f'{title}_{lang}.vtt')
                urllib.request.urlretrieve(subtitle_link, subtitle_filename)

def downloader():
    
    # 提取 cookies_string
    cookies_string = config['cookies_string']
    cookies_dict = parse_cookies_string_to_dict(cookies_string)
    
    if fetch_course_content_json:
        # 獲取html
        html_content = get_course_html(COURSE_URL, cookies_dict)
        # 拿到各章節名稱與id
        chapter_content = extract_chapter_content(html_content)
        # 將影片資源連結彙整成dict/json
        video_resource_dict = organize_course_data2json(chapter_content, export_json=True)
        if download_from_fetch_dict:
            download_videos_and_subtitles(video_resource_dict, desired_quality, download_path)


    if download_from_existed_json:
        with open(existed_json_name, 'r', encoding='utf-8') as f:
            video_resource_dict = json.load(f)
            download_videos_and_subtitles(video_resource_dict, desired_quality, download_path)
