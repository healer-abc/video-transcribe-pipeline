#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import tempfile
from datetime import datetime

# 输出目录（保持不变）
OUT_DIR = r"D:\Learning\VideoTranscripts"

# 长视频切片：默认每 10 分钟一段
SEGMENT_SECONDS = 600

# 文件名中禁止出现的字符（Windows / 跨平台）
ILLEGAL_CHARS = r'[\\/:*?"<>|\r\n\t]'


def is_url(x):
    return x.startswith(("http://", "https://", "www."))


def _resolve_ffmpeg():
    """定位 ffmpeg：优先 PATH，其次 imageio-ffmpeg 打包的二进制。"""
    import shutil
    exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if exe:
        return exe
    # 常见安装位置兜底
    for p in (
        r"D:\conda\Library\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ):
        if os.path.exists(p):
            return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return "ffmpeg"


def _resolve_ffprobe():
    """定位 ffprobe；找不到则由调用方用 ffmpeg 兜底解析时长。"""
    import shutil
    probe = shutil.which("ffprobe") or shutil.which("ffprobe.exe")
    if probe:
        return probe
    for p in (
        r"D:\conda\Library\bin\ffprobe.exe",
        r"C:\ffmpeg\bin\ffprobe.exe",
    ):
        if os.path.exists(p):
            return p
    return None


def _ffmpeg():
    """惰性解析 ffmpeg（兼容 PATH 在 import 后才补齐的情况）。"""
    return _resolve_ffmpeg()


def sanitize_filename(name):
    """清理文件名中的非法字符，返回安全的文件名（不含扩展名）。"""
    if not name:
        return ""
    name = re.sub(ILLEGAL_CHARS, "", name)
    name = name.strip().strip(".")      # 去掉首尾空白与点
    name = re.sub(r"\s+", " ", name)    # 连续空白合并为一个空格
    # Windows 保留文件名
    if name.upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        name = "_" + name
    return name[:120].strip(" .")       # 限制长度，避免路径过长


def base_name():
    """txt / md / srt 共用的时间戳基名（回退用）。"""
    return "transcript_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_base(title, when=None):
    """生成“视频标题_日期”基名；标题无效时回退到 transcript_时间。"""
    when = when or datetime.now()
    clean = sanitize_filename(title)
    if clean:
        return f"{clean}_{when.strftime('%Y%m%d')}"
    return base_name()


def fetch_title(url):
    """用 yt-dlp 获取视频标题；失败返回 None。"""
    print("🔎 获取视频标题中...")
    cmd = ["yt-dlp", "--no-playlist", "--print", "title", url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            title = (r.stdout or "").strip().splitlines()
            if title and title[0].strip():
                print(f"📺 标题：{title[0].strip()}")
                return title[0].strip()
        print("⚠️ 标题获取失败，回退到时间戳命名")
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ 标题获取异常：{e}")
    return None


def download_audio(url, tmp):
    """使用 yt-dlp 直接下载 bestaudio 原始音频（m4a），不再转 mp3。

    避免 -x / --audio-format mp3 触发的 ffmpeg 二次转换，
    从而绕开 B 站下载流程中的 503 不稳定问题。
    """
    print("⬇️ 下载音频中...")
    out = os.path.join(tmp, "audio.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f",
        "bestaudio",
        "--no-playlist",
        "-o",
        out,
        url,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-500:])

    # 返回实际下载到的音频文件（通常是 .m4a，也可能是 .webm/.opus 等）
    for f in sorted(os.listdir(tmp)):
        if os.path.splitext(f)[1].lower() in (
            ".m4a", ".mp3", ".webm", ".opus", ".aac", ".ogg", ".wav", ".flac",
        ):
            return os.path.join(tmp, f)
    raise RuntimeError("音频不存在")


def extract_audio(video, tmp):
    out = os.path.join(tmp, "audio.mp3")
    subprocess.run(
        [_ffmpeg(), "-i", video, "-vn", out, "-y"],
        capture_output=True
    )
    return out


def _audio_duration(audio):
    """读取音频总时长（秒）；失败返回 0.0。"""
    probe = _resolve_ffprobe()
    if probe:
        r = subprocess.run(
            [probe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio],
            capture_output=True, text=True,
        )
        try:
            return float((r.stdout or "").strip())
        except ValueError:
            return 0.0
    # 无 ffprobe：从 ffmpeg 的 stderr 里解析 Duration: 00:00:25.00
    r = subprocess.run([_ffmpeg(), "-i", audio], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr or "")
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return h * 3600 + mi * 60 + s
    return 0.0

def split_audio(audio, tmp, segment_seconds=SEGMENT_SECONDS):
    """用 ffmpeg 按固定时长切片，返回 [(路径, 偏移秒)] 列表。

    若音频短于一段，则直接返回原文件（偏移 0），不切片。
    """
    print(f"✂️ 检查音频长度（每 {segment_seconds // 60} 分钟一段）...")
    duration = _audio_duration(audio)

    if duration and duration <= segment_seconds:
        print("ℹ️ 音频较短，无需切片")
        return [(audio, 0.0)]

    if not duration:
        print("⚠️ 无法读取时长，跳过切片，按单文件处理")
        return [(audio, 0.0)]

    pattern = os.path.join(tmp, "segment_%03d.mp3")
    r = subprocess.run(
        [_ffmpeg(), "-i", audio, "-f", "segment",
         "-segment_time", str(segment_seconds),
         "-c", "copy", pattern, "-y"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        # 某些编码不支持 copy，回退到重编码
        r = subprocess.run(
            [_ffmpeg(), "-i", audio, "-f", "segment",
             "-segment_time", str(segment_seconds),
             "-c:a", "libmp3lame", "-q:a", "4", pattern, "-y"],
            capture_output=True, text=True,
        )
    if r.returncode != 0:
        raise RuntimeError("音频切片失败：" + r.stderr[-500:])

    parts = sorted(
        os.path.join(tmp, f) for f in os.listdir(tmp)
        if f.startswith("segment_") and f.endswith(".mp3")
    )
    if not parts:
        raise RuntimeError("切片后未找到音频片段")

    print(f"✂️ 已切成 {len(parts)} 段")
    return [(p, i * segment_seconds) for i, p in enumerate(parts)]


def get_api_key():
    """读取 GROQ_API_KEY：优先环境变量，其次 api-registry/.env。"""
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key.strip()
    for env_file in (
        os.path.expanduser("~/.shared-skills/api-registry/.env"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
    ):
        if os.path.exists(env_file):
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _client():
    from groq import Groq
    key = get_api_key()
    if not key:
        raise RuntimeError("缺少 GROQ_API_KEY（可在环境变量或 ~/.shared-skills/api-registry/.env 配置）")
    return Groq(api_key=key)


def _seg_field(seg, field, default=""):
    """兼容 dict / 对象两种返回结构。"""
    if isinstance(seg, dict):
        return seg.get(field, default)
    return getattr(seg, field, default)


def _to_segments(result):
    """把 Groq 返回结果归一化为 [{start, end, text}] 列表。"""
    raw = getattr(result, "segments", None)
    if not raw:
        return []
    out = []
    for seg in raw:
        text = (_seg_field(seg, "text") or "").strip()
        if not text:
            continue
        try:
            start = float(_seg_field(seg, "start", 0.0) or 0.0)
        except (TypeError, ValueError):
            start = 0.0
        try:
            end = float(_seg_field(seg, "end", start) or start)
        except (TypeError, ValueError):
            end = start
        out.append({"start": start, "end": end, "text": text})
    return out


def transcribe(audio, offset=0.0):
    """调用 Groq Whisper，返回 segments 列表，时间戳已加上 offset 偏移。"""
    client = _client()
    print("☁️ Groq Whisper 转录中...")
    with open(audio, "rb") as f:
        result = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3",
            language="zh",
            response_format="verbose_json",
        )

    segments = _to_segments(result)
    if segments:
        for s in segments:
            s["start"] += offset
            s["end"] += offset
        return segments

    # 回退：没有 segments 时，把整段文本当作一个 segment
    text = (getattr(result, "text", "") or "").strip()
    if text:
        return [{"start": offset, "end": offset, "text": text}]
    return []


def transcribe_all(audio, tmp):
    """长视频稳定处理：切片后逐段转录并合并，返回 segments 列表。"""
    parts = split_audio(audio, tmp)
    all_segments = []
    for i, (part, offset) in enumerate(parts, 1):
        print(f"▶️ 第 {i}/{len(parts)} 段转录中...")
        all_segments.extend(transcribe(part, offset=offset))
    return all_segments


def segments_to_text(segments):
    """中文分段：每个 segment 独立成段，段间空行分隔。"""
    paragraphs = [s["text"].strip() for s in segments if s["text"].strip()]
    return "\n\n".join(paragraphs)


def _fmt_ts(seconds, sep=","):
    """秒 -> SRR 时间戳 00:00:00,000"""
    if seconds < 0:
        seconds = 0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600 * 1000)
    m, ms = divmod(ms, 60 * 1000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def segments_to_srt(segments):
    """生成标准 SRT 字幕。"""
    lines = []
    for i, s in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(
            f"{_fmt_ts(s['start'])} --> {_fmt_ts(s['end'])}"
        )
        lines.append(s["text"].strip())
        lines.append("")
    return "\n".join(lines)


def write_txt(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_md(path, title, source, generated_at, text):
    md = (
        f"# {title}\n\n"
        f"来源：{source}\n\n"
        f"生成时间：{generated_at}\n\n"
        "---\n\n"
        "## 转录内容\n\n"
        f"{text}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)


def write_srt(path, segments):
    with open(path, "w", encoding="utf-8") as f:
        f.write(segments_to_srt(segments))


def main():
    parser = argparse.ArgumentParser(
        description="高质量字幕生成工具（Groq Whisper large-v3）"
    )
    parser.add_argument("--input", "-i", required=True, help="B站/视频 URL 或本地文件路径")
    parser.add_argument("--output", "-o", help="自定义输出基名（不含扩展名）")
    parser.add_argument(
        "--segment-seconds", type=int, default=SEGMENT_SECONDS,
        help=f"音频切片时长（秒），默认 {SEGMENT_SECONDS}",
    )
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    when = datetime.now()
    generated_at = when.strftime("%Y-%m-%d %H:%M:%S")

    # ① 标题：URL 用 yt-dlp 获取；本地文件用文件名
    title = None
    if is_url(args.input):
        title = fetch_title(args.input)
    else:
        local = os.path.splitext(os.path.basename(args.input))[0]
        title = sanitize_filename(local) or None

    # ② 输出基名：标题_日期，失败回退 transcript_时间
    if args.output:
        base = args.output
    else:
        base = os.path.join(OUT_DIR, safe_base(title, when))

    output_txt = base + ".txt"
    output_md = base + ".md"
    output_srt = base + ".srt"

    # ③ 音频获取 + 切片转录（保留 B站 URL / 本地视频两种输入）
    with tempfile.TemporaryDirectory() as tmp:
        if is_url(args.input):
            audio = download_audio(args.input, tmp)
        else:
            audio = extract_audio(args.input, tmp)

        segments = transcribe_all(audio, tmp)

        text = segments_to_text(segments)

        # ④ 落盘（在临时目录销毁前完成）
        write_txt(output_txt, text)
        write_md(output_md, title or os.path.basename(base), args.input,
                 generated_at, text)
        if segments:
            write_srt(output_srt, segments)

    print("✅ 完成")
    print(output_txt)
    print(output_md)
    if segments:
        print(output_srt)
    print(f"共 {len(segments)} 个字幕段")


if __name__ == "__main__":
    main()
