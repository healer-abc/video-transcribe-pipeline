# Video Transcribe Pipeline

一个面向学习场景的视频转录工具。

本项目基于开源 VideoTranscribe 项目进行二次开发，针对个人技术学习场景进行了功能扩展：接入 Groq Whisper 语音识别服务，实现 Bilibili 等在线视频自动下载、语音转文字、多格式输出。

项目目标不是替代专业字幕工具，而是建立一个可控、可扩展的视频学习资料采集 pipeline，将课程视频、技术分享快速转换为可检索的文本资料。

---

## Features

### Video Processing

- 支持 Bilibili / YouTube 等 yt-dlp 支持的平台
- 支持本地视频和音频文件
- 自动获取视频标题
- 自动提取音频

### Speech Recognition

- 使用 Groq API 调用 Whisper large-v3 模型
- 支持中文语音识别
- 保留原始内容，不进行自动总结

### Multiple Output Formats

自动生成：

- `.txt`
  - 原始转录文本
  - 适合搜索和后续处理

- `.md`
  - Markdown 格式
  - 适合 Obsidian 等知识管理工具

- `.srt`
  - 标准字幕格式
  - 包含时间戳，可直接用于播放器加载字幕

---

## Pipeline

```
Video URL / Local File

        ↓

      yt-dlp

        ↓

   Audio Extraction

        ↓

 Groq Whisper large-v3

        ↓

 ┌───────────────┐
 │               │
TXT             SRT
 │
MD
```

---

## Project Structure

```
video-transcribe-pipeline/

├── Tools/
│   └── transcribe.py        # 主程序
│
├── README.md
├── .gitignore
└── SKILL.md
```

---

## Installation

### Requirements

- Python >= 3.10
- ffmpeg
- yt-dlp

### Install Python dependencies

```bash
pip install yt-dlp groq
```

### Install ffmpeg

Windows:

```powershell
winget install Gyan.FFmpeg
```

检查安装：

```powershell
ffmpeg -version
yt-dlp --version
```

---

## API Configuration

本项目使用 Groq API 调用 Whisper 模型。

设置环境变量：

Windows PowerShell:

```powershell
setx GROQ_API_KEY "your_api_key"
```

重新打开终端后检查：

```powershell
echo $env:GROQ_API_KEY
```

注意：

- 不要将 API Key 写入代码；
- 不要提交 `.env` 或包含密钥的文件。

---

## Usage

### Bilibili Video

```bash
python Tools/transcribe.py \
--input "https://www.bilibili.com/video/BVxxxx/"
```

### Local Video

```bash
python Tools/transcribe.py \
--input "video.mp4"
```

---

## Output Example

默认输出目录：

```
D:\Learning\VideoTranscripts
```

生成：

```
Video_Title.txt
Video_Title.md
Video_Title.srt
```

---

## Example

输入：

```
Bilibili AI Course Video
```

处理：

```
Video
 ↓
Audio Extraction
 ↓
Whisper Transcription
 ↓
Subtitle Generation
```

输出：

### TXT

```
Transformer是一种基于Attention机制的模型...
```

### Markdown

```markdown
# Video Title

## Transcript

Transformer是一种基于Attention机制的模型...
```

### SRT

```
1
00:00:00,000 --> 00:00:05,000
Transformer是一种基于Attention机制的模型。
```

---

## Development Background

在学习深度学习、机器人和具身智能相关课程时，大量技术视频需要反复查阅。

传统方式通常依赖网页字幕或在线工具，但存在：

- 数据流程不可控；
- 输出格式固定；
- 难以整合个人知识库。

因此，本项目构建了一个可扩展的视频转录 pipeline：

```
视频资源
    ↓
自动获取音频
    ↓
语音识别
    ↓
结构化保存
    ↓
个人知识库
```

---

## Future Improvements

可能的优化方向：

- [ ] 批量视频处理
- [ ] 自动章节划分
- [ ] 自动生成课程笔记
- [ ] 接入本地 Whisper 模型
- [ ] Obsidian 知识库自动同步

---

## Credits

This project is based on:

VideoTranscribe:
https://github.com/Jane-xiaoer/claude-skill-video-transcribe

Major modifications:

- Replaced original transcription backend with Groq Whisper
- Added Bilibili video processing workflow
- Added TXT / Markdown / SRT export
- Improved local learning workflow
