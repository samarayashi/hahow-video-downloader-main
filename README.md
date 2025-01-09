# hahow-video-downloader

keyword: Hahow 好學校影片下載, sat知識衛星影片下載

基於 [techmovie/hahow-video-downloader](https://github.com/techmovie/hahow-video-downloader) 的專案內容，我新增了知識衛星（SAT）的下載器 `sat_downloader.py`。基本上，它是完全獨立的內容，只是目前先放在同一個專案中進行管理。

## Usage
- 修改 `config.yaml.sample` 为 `config.yaml`，依據其中內容做修改成自己上課url, authorization等配置yaml
- 运行`pip install -r requirements.txt`
- 运行`python main.py`

# Hahow downloader
## 得到 hahow authorization 配置的方法
![](https://ptpimg.me/xwdh4r.png)
如上截圖在hahow的上課頁面，找到me這隻請求，把相關內容填上yaml中hahow的配置上


# sat_downloader
## 配置sat(知識衛星的yaml)
所有需要的配置都放在 `config.yaml` 文件中。要使用此下載器，
1. 可以在登入狀態下從課程頁面的 Network 中找到 `record_point`，其中會包含 `authorization` 的請求資訊。
2. 另外，進入課程頁面的 `GET` 請求中，像是以下範例：
Request URL: https://sat.cool/classroom/47 Request Method: GET
可以找到帶有您 Google 登入狀態的 cookies。
3. 影片有通常有240p、360p、、540p、720p、1080p畫質可以選擇
4. 實際上我是得到有課程資源json，再把課程json的內容自動化下載而已。（所以可以從配置的步驟中讓，動作只停留在得到資源json）




