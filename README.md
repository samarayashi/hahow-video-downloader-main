# hahow-video-downloader

一键下载好学校 hahow.in 课程视频

## 获取 authorization 配置

![](https://ptpimg.me/xwdh4r.png)


## Usage

- 修改 `config.yaml.sample` 为 `config.yaml`，然后将课程 URL 和上一步获取的到的 authorization 填写到配置文件中
- 运行`pip install -t requirements.txt`
- 运行`python main.py`


## sat_downloader
基於
https://github.com/techmovie/hahow-video-downloader
這個專案內容我再加上知識衛星（sat）的下載器sat_downloader.py
基本上是完全獨立的內容，只是我現在先放在同一個專案上管理
我把其需要的配置一起放在config.yaml中
應該可以在登入的狀態下從課程頁面中的network找到record_point 其中會帶有`authorization`的請求
而在進入課程頁面的`get`請求中
Request URL:
https://sat.cool/classroom/47
Request Method:
GET
應該就會找到帶有自己google登入狀態的cookies

## sat_downloader

基於 [techmovie/hahow-video-downloader](https://github.com/techmovie/hahow-video-downloader) 的專案內容，我新增了知識衛星（SAT）的下載器 `sat_downloader.py`。基本上，它是完全獨立的內容，只是目前先放在同一個專案中進行管理。

所有需要的配置都放在 `config.yaml` 文件中。要使用此下載器，可以在登入狀態下從課程頁面的 Network 中找到 `record_point`，其中會包含 `authorization` 的請求資訊。

另外，進入課程頁面的 `GET` 請求中，像是以下範例：
Request URL: https://sat.cool/classroom/47 Request Method: GET
可以找到帶有您 Google 登入狀態的 cookies。




