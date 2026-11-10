#!/usr/bin/env bash
# Build demo/demo.mp4 from screenshots of the running UI.
# Captions are the narration in docs/demo_script.md, shortened to fit the frame.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHOTS="$ROOT/docs/screenshots"
OUT="$ROOT/demo/demo.mp4"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Crop the top of each tall screenshot so the choice cards stay readable.
crop() {
  local src="$1" dst="$2"
  ffmpeg -y -i "$src" -vf "scale=1280:-1,crop=1280:720:0:0" -frames:v 1 "$dst" >/dev/null 2>&1
}

crop "$SHOTS/ui_form.png" "$WORK/00.png"
crop "$SHOTS/P1.png" "$WORK/01.png"
crop "$SHOTS/P2.png" "$WORK/02.png"
crop "$SHOTS/P3.png" "$WORK/03.png"
crop "$SHOTS/P4.png" "$WORK/04.png"
crop "$SHOTS/P5.png" "$WORK/05.png"
crop "$SHOTS/P6.png" "$WORK/06.png"
crop "$SHOTS/edge_invalid.png" "$WORK/07.png"
crop "$SHOTS/edge_budget.png" "$WORK/08.png"

# Durations in seconds. Total about 150s.
cat > "$WORK/list.txt" << 'EOF'
file 00.png
duration 12
file 01.png
duration 18
file 02.png
duration 24
file 03.png
duration 18
file 04.png
duration 22
file 05.png
duration 18
file 06.png
duration 18
file 07.png
duration 12
file 08.png
duration 16
file 08.png
duration 0.1
EOF

cat > "$WORK/captions.srt" << 'EOF'
1
00:00:00,000 --> 00:00:12,000
StackSense picks a stack from the brief with rules and scores.
The LLM switch stays off. Same file in, same JSON out.

2
00:00:12,000 --> 00:00:30,000
Portfolio. One beginner, two weeks, zero dollars, pages must rank.
Astro, no server, no database, Cloudflare Pages. Cost band is zero.

3
00:00:30,000 --> 00:00:54,000
Home services in India. Data stays in Bangalore.
Next.js and Expo, one NestJS API. Razorpay takes payment.
The SMS warning is explicit. OTP can pass a 150 dollar cap.

4
00:00:54,000 --> 00:01:12,000
Whiteboard. 5000 people, 100 ms, GDPR.
Go on ECS in Frankfurt, React on the client, Yjs for the board.
Not Kubernetes.

5
00:01:12,000 --> 00:01:34,000
Lending. AWS only, Mumbai only. Postgres with a standby.
Cards stay at Razorpay. The model is SageMaker in the same region.
Backups have to stay in India too.

6
00:01:34,000 --> 00:01:52,000
HR tool. Reuse Entra ID and the existing SQL Server.
Razor Pages on Azure in Central India.
SQL Server 2019 is past mainstream support. The warning says so.

7
00:01:52,000 --> 00:02:10,000
Crop survey. Offline first. SQLite on the phone, FastAPI in Bangalore.
Shrink photos before a weak network. Do not start on Realm. It was shut down.

8
00:02:10,000 --> 00:02:22,000
Bad types and a priority of 9: invalid input, no stack. The process does not crash.

9
00:02:22,000 --> 00:02:38,000
A fintech with a zero dollar budget is infeasible.
The cheapest legal stack is still shown, and the dollar gap is printed.
EOF

ffmpeg -y -f concat -safe 0 -i "$WORK/list.txt" -i "$WORK/captions.srt" \
  -vf "subtitles=$WORK/captions.srt:force_style='FontName=DejaVu Sans,FontSize=16,PrimaryColour=&H00F3EFE6,OutlineColour=&H001C1915,BorderStyle=3,Outline=1,Shadow=0,MarginV=28'" \
  -c:v libx264 -pix_fmt yuv420p -r 30 -movflags +faststart \
  "$OUT"

ls -lh "$OUT"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
