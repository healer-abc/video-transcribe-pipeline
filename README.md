
# Video Transcribe Pipeline

> 将 Bilibili / YouTube 视频快速转换为可搜索的学习文本。

Video Transcribe Pipeline 是一个面向学习场景的视频转录工具。

它可以自动完成：

```
视频链接
    ↓
音频提取
    ↓
Whisper 语音识别
    ↓
TXT / Markdown / SRT 输出
    ↓
个人知识库
```

适用于：

- AI / 深度学习课程整理
- 技术分享视频转文字
- Bilibili / YouTube 学习资料整理
- Obsidian 知识库构建


## Features

### 🎬 视频处理

支持：

- Bilibili 视频
- YouTube 视频
- 本地视频文件

自动完成：

- 获取视频信息
- 下载音频
- 提取语音内容


### 🧠 高质量语音识别

使用：

- Groq API
- Whisper large-v3 模型

特点：

- 支持中文识别
- 识别速度快
- 保留原始内容


### 📄 多格式输出

生成：

```
TXT
 |
 ├── 原始转录文本
 |
Markdown
 |
 └── 适合 Obsidian 笔记管理

SRT
 |
 └── 带时间戳字幕文件
```


## Installation

### 1. Clone repository

```bash
git clone https://github.com/healer-abc/video-transcribe-pipeline.git

cd video-transcribe-pipeline
```


### 2. Install dependencies

```bash
pip install yt-dlp groq
```


### 3. Install ffmpeg

Windows:

```powershell
winget install Gyan.FFmpeg
```

检查：

```powershell
ffmpeg -version
yt-dlp --version
```


## Configure API Key

本项目使用 Groq API 调用 Whisper。

首先获取 API Key：

https://console.groq.com/


设置环境变量：

Windows PowerShell:

```powershell
setx GROQ_API_KEY "your_api_key"
```

重新打开终端。


检查：

```powershell
echo $env:GROQ_API_KEY
```


注意：

- 不要把 API Key 写入代码
- 不要上传 `.env` 文件


## Usage


### Bilibili 视频

```bash
python Tools/transcribe.py \
--input "https://www.bilibili.com/video/BVxxxx/"
```


### 本地视频

```bash
python Tools/transcribe.py \
--input "video.mp4"
```


## Output Example

默认输出：

```
D:\Learning\VideoTranscripts
```

生成：

```
视频标题.txt
视频标题.md
视频标题.srt
```


示例：

输入：

```
Bilibili AI课程视频
```

输出：

```
AI课程视频.md
AI课程视频.txt
AI课程视频.srt
```


## Project Structure

```
video-transcribe-pipeline

├── Tools
│   └── transcribe.py
│
├── README.md
└── .gitignore
```


## Design Idea

传统视频学习流程：

```
观看视频
 ↓
手动记录
 ↓
整理笔记
```

效率较低。


本项目尝试建立：

```
视频资源

 ↓

自动转录

 ↓

结构化文本

 ↓

个人知识库
```

减少重复整理工作。


## Future Improvements

计划：

- [ ] 自动章节划分
- [ ] 自动生成学习笔记
- [ ] 批量视频处理
- [ ] 接入本地 Whisper
- [ ] Obsidian 自动同步


## Credits

This project is based on:

https://github.com/Jane-xiaoer/claude-skill-video-transcribe


Major modifications:

- Replaced transcription backend with Groq Whisper
- Added Bilibili video processing
- Added TXT / Markdown / SRT export
- Improved personal learning workflow