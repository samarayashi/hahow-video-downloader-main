# hahow-video-downloader

keyword: Hahow 好學校影片下載, sat知識衛星影片下載

聲明：僅供練習使用，尊重智慧財產權，不做任何商業使用

基於 [techmovie/hahow-video-downloader](https://github.com/techmovie/hahow-video-downloader) 的專案內容，我新增了知識衛星（SAT）的下載器 `sat_downloader.py`。基本上，它是完全獨立的內容，只是目前先放在同一個專案中進行管理。

## 使用方法
- 修改 `config.yaml.sample` 為 `config.yaml`，依據其中內容做修改成自己上課url, authorization等配置yaml
- 執行`pip install -r requirements.txt`
- 執行`python main.py`

# Hahow downloader
## 得到 hahow authorization 配置的方法
![](https://ptpimg.me/xwdh4r.png)
如上截圖在hahow的上課頁面，找到me這隻請求，把相關內容填上yaml中hahow的配置上


# sat_downloader
## 配置sat(知識衛星的yaml)
1. 可以在登入狀態下從課程頁面的 Network 中找到 `record_point`，其中會包含 `authorization` 的請求資訊。![record_point](asset/doc_image/record_point.png)
2. 影片有通常有240p、360p、540p、720p、1080p畫質可以選擇
3. 實際上我是得到有課程資源json，再把課程json的內容自動化下載而已。（所以可以從配置的步驟中讓，動作只停留在得到資源json）




