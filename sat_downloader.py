import requests
from requests.utils import cookiejar_from_dict
from bs4 import BeautifulSoup
import json
import os
import urllib.request
import yaml

# 定義程式行為
fetch_course_content_from_web = True
download_videos = False
download_from_fetch_dict = False
download_from_existed_resource_json = 'test.json'

# 从 YAML 文件加载配置
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

# 提取 user_cookies
user_cookies = config['user_cookies']

# 提取課程信息
COURSE_NUM = config['course']['course_num']
course_url = config['course']['course_url'].format(COURSE_NUM)
content_base_url = config['course']['content_base_url'].format(COURSE_NUM)

# 提取 Bearer token
auth_token = config['auth']['token']

# 下載參數
# Specify the desired video quality
desired_quality = '360p'
# Define the base path where the course folders will be created
base_path = './'


def get_course_html(course_url, user_cookies):
    # 设置目标 URL
    course_url = 'https://sat.cool/classroom/47'

    # 定义请求头
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
    
    # 创建会话
    session = requests.Session()
    session.cookies = cookiejar_from_dict(user_cookies)

    # 发送 GET 请求
    response = session.get(course_url, headers=headers)
    
    # 如果需要将内容保存到文件
    # with open('classroom_page.html', 'w', encoding='utf-8') as file:
    #     file.write(response.text)
            
    return response.text

def extract_chapter_content(html_content):
    # 解析 HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # 提取课程名称
    course_name_tag = soup.select_one('.classroom-top-wrap a')
    course_name = course_name_tag.get_text(strip=True) if course_name_tag else '未知课程名称'

    # 提取章节信息
    chapters = []
    tablist = soup.select_one('div[role="tablist"]')

    if tablist:
        for chapter in tablist.select('.el-collapse-item'):
            chapter_title_tag = chapter.select_one('.classroom-chapter-list__collapse-title')
            chapter_title = chapter_title_tag.get_text(strip=True) if chapter_title_tag else '未知章节标题'
            
            sub_chapters = []
            for sub_chapter in chapter.select('[data-chapter-part]'):
                sub_chapter_title_tag = sub_chapter.select_one('.classroom-chapter-list__title')
                sub_chapter_title = sub_chapter_title_tag.get_text(strip=True) if sub_chapter_title_tag else '未知子章节标题'
                sub_chapter_id = sub_chapter.get('data-chapter-part', '未知ID')
                
                sub_chapters.append({
                    'title': sub_chapter_title,
                    'id': sub_chapter_id
                })
            
            chapters.append({
                'chapter_title': chapter_title,
                'sub_chapters': sub_chapters
            })

    # 构建最终的课程信息字典
    course_info = {
        'course_name': course_name,
        'chapters': chapters
    }
    return course_info
    # 输出结果
    # print(json.dumps(course_info, ensure_ascii=False, indent=2))
    
    # 如果需要将内容保存到文件
    # with open('content_id.txt', 'w', encoding='utf-8') as file:
    #     file.write(str(course_info))

def fetch_vimeo_data(base_url, course_chapter_part_id, auth_token):
    """
    发送带有 Authorization 的 GET 请求，并返回响应数据。

    :param base_url: str, API 端点的基础 URL
    :param course_chapter_part_id: str or int, 课程章节部分的 ID
    :param auth_token: str, Authorization 所需的 Bearer token
    :return: dict, 返回的 JSON 数据，若请求失败则返回空字典
    """
    url = f"{base_url}?course_chapter_part_id={course_chapter_part_id}"
    headers = {
        'Authorization': f'Bearer {auth_token}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 如果请求失败，抛出异常
        return response.json()  # 返回 JSON 数据
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return {}

def organize_course_data2json(chapter_content, export_json = True):
    """
    整理课程数据为指定的 JSON 结构。

    :param course_data: dict, 课程数据
    :return: dict, 整理后的 JSON 结构
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

            vimeo_data = fetch_vimeo_data(content_base_url, sub_chapter_id, auth_token)
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
            
            # Download videos
            for quality_key, video_link in video_links.items():
                if quality_key == quality:
                    video_filename = os.path.join(sub_chapter_path, f'{title}_{quality}.mp4')
                    urllib.request.urlretrieve(video_link, video_filename)
                    
            # Download subtitles
            for lang, subtitle_link in subtitle_links.items():
                subtitle_filename = os.path.join(sub_chapter_path, f'{title}_{lang}.vtt')
                urllib.request.urlretrieve(subtitle_link, subtitle_filename)


video_resource_dict = None
if fetch_course_content_from_web:
    # 獲取html
    html_content = get_course_html(course_url, user_cookies)
    # 拿到各章節名稱與id
    chapter_content = extract_chapter_content(html_content)
    # 將影片資源連結彙整成dict/json
    video_resource_dict = organize_course_data2json(chapter_content)


if download_videos:
    if  download_from_existed_resource_json:
        with open('test.json', 'r', encoding='utf-8') as f:
            video_resource_dict = json.load(f)
    elif download_from_fetch_dict:
        pass
    download_videos_and_subtitles(video_resource_dict, desired_quality, base_path)
      

