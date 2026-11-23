#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== stage 1: render game frames ==="
if [ "${SKIP_RENDER:-0}" != "1" ]; then
  python3 game.py
  echo "=== stage 2: synthesize beat ==="
  python3 beat.py
else
  echo "SKIP_RENDER=1: reusing existing game.mp4 and beat.wav"
fi

echo "=== stage 3: write referral code subtitles ==="
cat > code.ass <<'ASS'
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Code,JetBrains Mono,66,&H00191419,&H00191419,&H00191419,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:14.75,0:00:14.85,Code,,0,0,0,,{\an7\pos(228,1232)}n
Dialogue: 0,0:00:14.85,0:00:14.95,Code,,0,0,0,,{\an7\pos(228,1232)}n0
Dialogue: 0,0:00:14.95,0:00:15.05,Code,,0,0,0,,{\an7\pos(228,1232)}n0y
Dialogue: 0,0:00:15.05,0:00:15.15,Code,,0,0,0,,{\an7\pos(228,1232)}n0yk
Dialogue: 0,0:00:15.15,0:00:15.25,Code,,0,0,0,,{\an7\pos(228,1232)}n0yk8
Dialogue: 0,0:00:15.25,0:00:15.35,Code,,0,0,0,,{\an7\pos(228,1232)}n0yk8x
Dialogue: 0,0:00:15.35,0:00:15.45,Code,,0,0,0,,{\an7\pos(228,1232)}n0yk8xz
Dialogue: 0,0:00:15.45,0:00:16.50,Code,,0,0,0,,{\an7\pos(228,1232)}n0yk8xz9
ASS

echo "=== stage 4: composite video, card, code and audio ==="
ffmpeg -y -hide_banner -loglevel warning \
  -i game.mp4 \
  -i card.webm \
  -i beat.wav \
  -filter_complex "[0:v]subtitles=overlays.ass:fontsdir=fonts[v0];[1:v]setpts=PTS+14/TB[card];[v0][card]overlay=0:0:enable='between(t,14,16.5)':format=auto[v1];[v1]subtitles=code.ass:fontsdir=fonts[vout]" \
  -map "[vout]" -map 2:a \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 192k -ar 48000 \
  -t 16.5 -movflags +faststart frog-run.mp4

echo "=== stage 5: verify ==="
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,sample_rate,channels -of default=nw=1 frog-run.mp4
sha256sum frog-run.mp4
