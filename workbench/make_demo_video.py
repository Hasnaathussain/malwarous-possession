"""Render permitted synthetic positions to an optional MP4 using local ffmpeg.

No input media, network requests, model, or external Python packages are used.
"""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess

from .demo import make_demo


def render_frame(sample, width=840, height=544):
    """RGB pitch frame corresponding exactly to one synthetic tracking sample."""
    image = bytearray(bytes((229, 238, 225)) * width * height)
    pad = 24
    pw, ph = width - 2 * pad, height - 2 * pad
    def rect(x, y, w, h, color):
        left, right = max(0, int(x)), min(width, int(x + w))
        if right <= left:
            return
        row = bytes(color) * (right - left)
        for yy in range(max(0, int(y)), min(height, int(y + h))):
            start = (yy * width + left) * 3
            image[start:start + len(row)] = row
    def outline(x, y, w, h, color, thickness=2):
        rect(x,y,w,thickness,color); rect(x,y+h-thickness,w,thickness,color)
        rect(x,y,thickness,h,color); rect(x+w-thickness,y,thickness,h,color)
    def circle(x, y, radius, color):
        for yy in range(-radius, radius + 1):
            half = int(math.sqrt(max(0, radius * radius - yy * yy)))
            rect(int(x) - half, int(y) + yy, half * 2 + 1, 1, color)
    for stripe in range(10):
        rect(pad + pw * stripe / 10, pad, pw / 10 + 1, ph,
             (220,234,215) if stripe % 2 else (231,240,227))
    line = (143,169,145)
    outline(pad,pad,pw,ph,line); rect(width/2,pad,2,ph,line)
    for degree in range(360):
        angle = math.radians(degree)
        circle(width/2 + math.cos(angle)*9.15/105*pw,
               height/2 + math.sin(angle)*9.15/68*ph, 1, line)
    for side in (0, 1):
        box_width = 16.5/105*pw
        outline(pad if side == 0 else width-pad-box_width, pad+(68/2-20.16)/68*ph,
                box_width,40.32/68*ph,line)
    for player in sample["players"]:
        x, y = pad + player["x"]/105*pw, pad + (1-player["y"]/68)*ph
        circle(x,y,8,(255,255,255))
        circle(x,y,6,(18,110,101) if player["team"] == "H" else (178,95,48))
    if sample["ball"]:
        x, y = sample["ball"][:2]
        circle(pad+x/105*pw,pad+(1-y/68)*ph,6,(35,57,40))
        circle(pad+x/105*pw,pad+(1-y/68)*ph,4,(255,255,255))
    return bytes(image)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
        default=Path(__file__).resolve().parents[1] / "artifacts_private" / "v2" / "demo")
    args = parser.parse_args(argv)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        parser.exit(2, "Local ffmpeg executable is required for optional demo video generation.\n")
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    video_path = out / "synthetic-demo.mp4"
    if video_path.exists():
        parser.exit(2, "Demo video already exists. Choose a new output directory to avoid overwriting it.\n")
    bundle = make_demo()
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
        "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", "840x544",
        "-framerate", "10", "-i", "pipe:0", "-an", "-c:v", "libx264",
        "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-metadata", "title=Synthetic software demonstration; not accuracy evidence", str(video_path)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        # Exactly 720 frames / 10 Hz = 72 seconds (final endpoint sample is not another frame).
        for sample in bundle["matches"][0]["samples"][:-1]:
            process.stdin.write(render_frame(sample))
        process.stdin.close()
        result = process.wait()
    except BaseException:
        process.kill(); process.wait()
        raise
    if result:
        parser.exit(2, f"ffmpeg failed with exit status {result}.\n")
    bundle["matches"][0]["media"] = dict(id="synthetic-demo", offset_s=0, fps=10)
    (out / "demo.json").write_text(json.dumps(bundle, allow_nan=False), encoding="utf-8")
    (out / "media-map.json").write_text(json.dumps({"synthetic-demo":video_path.name}), encoding="utf-8")
    print("Generated synthetic-only media and bundle in " + str(out))
    print('python -m workbench.server --data "' + str(out / "demo.json") + '" --media-map "' + str(out / "media-map.json") + '"')


if __name__ == "__main__":
    main()
