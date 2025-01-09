# hahow-video-downloader

基於 [techmovie/hahow-video-downloader](https://github.com/techmovie/hahow-video-downloader) 的專案內容，我新增了知識衛星（SAT）的下載器 `sat_downloader.py`。基本上，它是完全獨立的內容，只是目前先放在同一個專案中進行管理。

## 获取 authorization 配置

![](https://ptpimg.me/xwdh4r.png)


## Usage

- 修改 `config.yaml.sample` 为 `config.yaml`，然后将课程 URL 和上一步获取的到的 authorization 填写到配置文件中
- 运行`pip install -r requirements.txt`
- 运行`python main.py`


## sat_downloader

所有需要的配置都放在 `config.yaml` 文件中。要使用此下載器，可以在登入狀態下從課程頁面的 Network 中找到 `record_point`，其中會包含 `authorization` 的請求資訊。

另外，進入課程頁面的 `GET` 請求中，像是以下範例：
Request URL: https://sat.cool/classroom/47 Request Method: GET
可以找到帶有您 Google 登入狀態的 cookies。




