#!/usr/bin/env python3
"""
影片處理工具 - Python 版本
功能包含：轉換 GIF、抽取畫面、格式轉換、媒體資訊掃描等
"""

import os
import sys
import glob
import argparse
import subprocess
import shutil
from pathlib import Path
import csv
import io

class VideoProcessor:
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self._check_dependencies()
    
    def _check_dependencies(self):
        """檢查必要工具是否安裝"""
        for tool in ['ffmpeg', 'ffprobe']:
            if not shutil.which(tool):
                print(f"❌ {tool} not found")
                sys.exit(1)
    
    def _run_command(self, cmd, cwd=None, capture_output=False):
        """執行命令的通用函數"""
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd, 
                capture_output=capture_output, 
                text=True,
                check=False
            )
            return result
        except subprocess.SubprocessError as e:
            print(f"❌ 執行命令失敗: {' '.join(cmd)}")
            print(f"錯誤: {e}")
            return None

    def convert_to_gif(self, input_file, fps=15, frames=None):
        """單一影片轉 GIF（使用 palette 避免色彩偏差）"""
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"❌ 找不到檔案：{input_file}")
            return False
        
        name = input_path.stem
        palette = f"{name}_palette.png"
        output = f"{name}.gif"
        
        print(f"🎞 轉換 {input_file} ➜ {output} (fps={fps})")
        
        # 生成調色盤
        palette_cmd = [
            'ffmpeg', '-y', '-i', str(input_path),
            '-vf', f'fps={fps},palettegen', palette
        ]
        
        result = self._run_command(palette_cmd, cwd=input_path.parent)
        if result and result.returncode != 0:
            print(f"❌ 調色盤生成失敗")
            return False
        
        # 生成 GIF
        gif_cmd = [
            'ffmpeg', '-y', '-i', str(input_path), '-i', palette,
            '-filter_complex', f'fps={fps}[x];[x][1:v]paletteuse'
        ]
        
        if frames:
            gif_cmd.extend(['-frames:v', str(frames)])
        
        gif_cmd.append(output)
        
        result = self._run_command(gif_cmd, cwd=input_path.parent)
        if result and result.returncode == 0:
            print(f"✅ GIF 輸出完成：{output}")
            # 清理調色盤檔案
            palette_path = input_path.parent / palette
            if palette_path.exists():
                palette_path.unlink()
            return True
        else:
            print(f"❌ GIF 轉換失敗")
            return False

    def batch_convert_gif(self, fps=15, directory="."):
        """批次轉換資料夾內的 .mp4 為 GIF"""
        mp4_files = list(Path(directory).glob("*.mp4"))
        
        if not mp4_files:
            print(f"在 {directory} 中沒有找到 .mp4 檔案")
            return
        
        print(f"找到 {len(mp4_files)} 個影片檔案")
        
        for file in mp4_files:
            self.convert_to_gif(str(file), fps)

    def extract_frames(self, input_file, fps=1, format_type="jpg"):
        """抽出影片畫面（JPG 或 PNG）"""
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"❌ 找不到檔案：{input_file}")
            return False, None
        
        base = input_path.stem
        outdir = input_path.parent / f"{base}_frames"
        
        outdir.mkdir(exist_ok=True)
        
        cmd = [
            'ffmpeg', '-y', '-i', str(input_path),
            '-qscale:v', '2', '-r', str(fps),
            str(outdir / f"frame_%04d.{format_type}")
        ]
        
        result = self._run_command(cmd)
        if result and result.returncode == 0:
            print(f"✅ 圖片已儲存到：{outdir}")
            return True, outdir
        else:
            print(f"❌ 畫面抽取失敗")
            return False, None

    def extract_jpg(self, input_file, fps=1):
        """抽出 JPG 畫面"""
        return self.extract_frames(input_file, fps, "jpg")

    def extract_png(self, input_file, fps=1):
        """抽出 PNG 畫面"""
        return self.extract_frames(input_file, fps, "png")

    def png2jpg(self, folder):
        """PNG ➜ JPG 批次轉換"""
        folder_path = Path(folder)
        if not folder_path.exists():
            print(f"❌ 資料夾不存在：{folder}")
            return
        
        png_files = list(folder_path.glob("*.png"))
        
        if not png_files:
            print(f"在 {folder} 中沒有找到 PNG 檔案")
            return
        
        print(f"找到 {len(png_files)} 個 PNG 檔案")
        
        for img in png_files:
            out = img.with_suffix('.jpg')
            cmd = ['ffmpeg', '-y', '-i', str(img), '-qscale:v', '2', str(out)]
            
            result = self._run_command(cmd)
            if result and result.returncode == 0:
                print(f"🖼 {img.name} ➜ {out.name}")
            else:
                print(f"❌ 轉換失敗：{img.name}")

    def batch_rename(self, file_format, new_name, start_num=1):
        """批次重新命名檔案"""
        pattern = f"*.{file_format}"
        files = sorted(glob.glob(pattern))
        
        if not files:
            print(f"沒有找到 {pattern} 檔案")
            return
        
        print(f"找到 {len(files)} 個 {file_format} 檔案")
        
        for i, file_path in enumerate(files):
            old_path = Path(file_path)
            new_filename = f"{new_name}_{start_num + i:02d}.{file_format}"
            new_path = old_path.parent / new_filename
            
            try:
                old_path.rename(new_path)
                print(f"📝 {old_path.name} ➜ {new_filename}")
            except OSError as e:
                print(f"❌ 重新命名失敗 {old_path.name}: {e}")

    def probe_info(self, directory, recursive=False, output_csv=None):
        """使用 ffprobe 擷取影片資訊"""
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"❌ 資料夾不存在：{directory}")
            return
        
        # CSV 標頭
        fieldnames = [
            'filename', 'filepath', 'codec_name', 'profile', 'codec_type', 
            'codec_tag_string', 'width', 'height', 'pix_fmt', 
            'avg_frame_rate', 'duration'
        ]
        
        # 準備輸出
        rows = []
        
        # 決定掃描方式
        if recursive:
            files = dir_path.rglob("*")
            print(f"📊 遞迴掃描 {directory} 中的媒體檔案...")
        else:
            files = dir_path.iterdir()
            print(f"📊 掃描 {directory} 中的媒體檔案...")
        
        # 掃描檔案
        processed_count = 0
        for file_path in files:
            if not file_path.is_file():
                continue
            
            # 使用 ffprobe 取得資訊
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'default=nokey=1:noprint_wrappers=1',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name,profile,codec_type,codec_tag_string,width,height,pix_fmt,avg_frame_rate',
                '-show_entries', 'format=duration',
                str(file_path)
            ]
            
            result = self._run_command(cmd, capture_output=True)
            if result and result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                
                # 確保有足夠的資料行
                while len(lines) < 9:
                    lines.append('')
                
                # 計算相對路徑（如果是遞迴模式）
                if recursive:
                    try:
                        rel_path = file_path.relative_to(dir_path)
                    except ValueError:
                        rel_path = file_path
                else:
                    rel_path = file_path.name
                
                # 準備資料行
                row_data = {
                    'filename': file_path.name,
                    'filepath': str(rel_path),
                    'codec_name': lines[0] if len(lines) > 0 else '',
                    'profile': lines[1] if len(lines) > 1 else '',
                    'codec_type': lines[2] if len(lines) > 2 else '',
                    'codec_tag_string': lines[3] if len(lines) > 3 else '',
                    'width': lines[4] if len(lines) > 4 else '',
                    'height': lines[5] if len(lines) > 5 else '',
                    'pix_fmt': lines[6] if len(lines) > 6 else '',
                    'avg_frame_rate': lines[7] if len(lines) > 7 else '',
                    'duration': lines[8] if len(lines) > 8 else ''
                }
                
                rows.append(row_data)
                processed_count += 1
        
        if not rows:
            print("沒有找到可處理的媒體檔案")
            return
        
        print(f"✅ 處理了 {processed_count} 個媒體檔案")
        
        # 輸出結果
        if output_csv:
            # 輸出到 CSV 檔案
            csv_path = Path(output_csv)
            try:
                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                print(f"✅ CSV 檔案已儲存到：{csv_path}")
            except Exception as e:
                print(f"❌ 無法寫入 CSV 檔案：{e}")
        else:
            # 輸出到終端機
            print(','.join(f'"{field}"' for field in fieldnames))
            for row in rows:
                row_values = [row.get(field, '') for field in fieldnames]
                print(','.join(f'"{value}"' for value in row_values))

def create_parser():
    """建立命令行參數解析器"""
    parser = argparse.ArgumentParser(
        description="影片處理工具 - Python 版本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  %(prog)s video.mp4                          # 轉 GIF，預設 fps=15
  %(prog)s video.mp4 --fps 10 --frames 100   # 自訂 fps 和畫面數
  %(prog)s batch-gif --fps 20                # 批次轉 GIF
  %(prog)s extract-jpg video.mp4 --fps 2     # 抽取 JPG 畫面
  %(prog)s extract-png video.mp4 --fps 1     # 抽取 PNG 畫面
  %(prog)s png2jpg ./frames                  # PNG 轉 JPG
  %(prog)s probe-info ./videos               # 掃描影片資訊
  %(prog)s probe-info ./videos -r --csv info.csv  # 遞迴掃描並輸出 CSV
  %(prog)s batch-rename png "新名稱" --start 1  # 批次重新命名
        """.strip()
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 轉 GIF (預設命令)
    gif_parser = subparsers.add_parser('gif', help='轉換影片為 GIF')
    gif_parser.add_argument('input', help='輸入影片檔案')
    gif_parser.add_argument('--fps', type=int, default=15, help='FPS (預設: 15)')
    gif_parser.add_argument('--frames', type=int, help='畫面數限制')
    
    # 批次轉 GIF
    batch_gif_parser = subparsers.add_parser('batch-gif', help='批次轉換 MP4 為 GIF')
    batch_gif_parser.add_argument('--fps', type=int, default=15, help='FPS (預設: 15)')
    batch_gif_parser.add_argument('--directory', default='.', help='目標資料夾 (預設: 當前目錄)')
    
    # 抽取 JPG
    jpg_parser = subparsers.add_parser('extract-jpg', help='抽取 JPG 畫面')
    jpg_parser.add_argument('input', help='輸入影片檔案')
    jpg_parser.add_argument('--fps', type=int, default=1, help='FPS (預設: 1)')
    
    # 抽取 PNG
    png_parser = subparsers.add_parser('extract-png', help='抽取 PNG 畫面')
    png_parser.add_argument('input', help='輸入影片檔案')
    png_parser.add_argument('--fps', type=int, default=1, help='FPS (預設: 1)')
    
    # PNG 轉 JPG
    convert_parser = subparsers.add_parser('png2jpg', help='PNG 轉 JPG')
    convert_parser.add_argument('folder', help='目標資料夾')
    
    # 掃描資訊
    probe_parser = subparsers.add_parser('probe-info', help='掃描影片資訊')
    probe_parser.add_argument('directory', help='目標資料夾')
    probe_parser.add_argument('--recursive', '-r', action='store_true', help='遞迴掃描子資料夾')
    probe_parser.add_argument('--csv', help='輸出 CSV 檔案路徑 (若未指定則輸出到終端機)')
    
    # 批次重新命名
    rename_parser = subparsers.add_parser('batch-rename', help='批次重新命名')
    rename_parser.add_argument('format', help='檔案格式 (例: png, mp4)')
    rename_parser.add_argument('new_name', help='新名稱前綴')
    rename_parser.add_argument('--start', type=int, default=1, help='起始數字 (預設: 1)')
    
    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    processor = VideoProcessor()
    
    # 處理沒有子命令的情況（直接轉 GIF）
    if not args.command and len(sys.argv) >= 2:
        # 假設第一個參數是影片檔案
        input_file = sys.argv[1]
        fps = int(sys.argv[2]) if len(sys.argv) > 2 else 15
        frames = int(sys.argv[3]) if len(sys.argv) > 3 else None
        processor.convert_to_gif(input_file, fps, frames)
        return
    
    if not args.command:
        parser.print_help()
        return
    
    # 執行對應命令
    if args.command == 'gif':
        processor.convert_to_gif(args.input, args.fps, args.frames)
    elif args.command == 'batch-gif':
        processor.batch_convert_gif(args.fps, args.directory)
    elif args.command == 'extract-jpg':
        processor.extract_jpg(args.input, args.fps)
    elif args.command == 'extract-png':
        processor.extract_png(args.input, args.fps)
    elif args.command == 'png2jpg':
        processor.png2jpg(args.folder)
    elif args.command == 'probe-info':
        processor.probe_info(args.directory, args.recursive, args.csv)
    elif args.command == 'batch-rename':
        processor.batch_rename(args.format, args.new_name, args.start)

if __name__ == "__main__":
    main()