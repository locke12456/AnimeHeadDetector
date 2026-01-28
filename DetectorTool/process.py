import os
import glob
import argparse
from pathlib import Path
from .video_processor import VideoProcessor  # 導入您轉換好的 VideoProcessor

def process_video_files(folder_path, fps="16", keep_frames=5, output_dir=None, dry_run=False):
    """
    處理指定資料夾中的所有 .mp4 檔案
    """
    processor = VideoProcessor()
    
    if not os.path.exists(folder_path):
        print(f"錯誤：資料夾 '{folder_path}' 不存在")
        return
    
    # 設定輸出目錄
    if output_dir:
        output_base = Path(output_dir)
        output_base.mkdir(parents=True, exist_ok=True)
        print(f"輸出資料夾：{output_base}")
    
    video_files = glob.glob(os.path.join(folder_path, "*.mp4"))
    
    if not video_files:
        print(f"在 '{folder_path}' 中沒有找到 .mp4 檔案")
        return
    
    print(f"找到 {len(video_files)} 個影片檔案")
    print(f"使用 VideoProcessor.extract_png()")
    print(f"幀率參數：{fps}")
    print(f"保留最後 {keep_frames} 張畫面")
    
    if dry_run:
        print("*** DRY RUN 模式 - 不會執行實際操作 ***")
    
    for video_file in video_files:
        process_single_video(video_file, processor, fps, keep_frames, output_dir, dry_run)

def process_single_video(video_file_path, processor, fps, keep_frames, output_dir=None, dry_run=False):
    """
    處理單個影片檔案
    """
    video_path = Path(video_file_path)
    video_name = video_path.stem
    
    print(f"\n處理影片：{video_name}.mp4")
    
    # 決定輸出資料夾位置
    if output_dir:
        # 使用指定的輸出資料夾
        final_output_folder = Path(output_dir)
    else:
        # 使用影片旁邊的預設資料夾
        final_output_folder = video_path.parent
    
    # 步驟 1: 使用 VideoProcessor.extract_png()
    if not dry_run:
        try:
            result = processor.extract_png(video_file_path, int(fps))
            
            # 處理不同的回傳格式
            if isinstance(result, tuple):
                success, temp_output_folder = result
            else:
                success = result
                temp_output_folder = video_path.parent / f"{video_name}_frames"
            
            if not success:
                print(f"錯誤：提取畫面失敗")
                return
                
        except Exception as e:
            print(f"錯誤：無法執行畫面提取 - {e}")
            return
    else:
        print(f"[DRY RUN] processor.extract_png('{video_file_path}', {fps})")
        temp_output_folder = video_path.parent / f"{video_name}_frames"
    
    # 步驟 2: 處理畫面檔案
    if not dry_run:
        if not temp_output_folder.exists():
            print(f"錯誤：輸出資料夾 '{temp_output_folder}' 不存在")
            return
        
        frame_files = sorted(glob.glob(str(temp_output_folder / "frame_*.png")))
    else:
        frame_files = [str(temp_output_folder / f"frame_{i:04d}.png") for i in range(1, 82)]
    
    if not frame_files:
        print(f"在 '{temp_output_folder}' 中沒有找到畫面檔案")
        return
    
    total_frames = len(frame_files)
    print(f"找到 {total_frames} 個畫面檔案")
    
    if total_frames <= keep_frames:
        print(f"畫面數量不超過 {keep_frames} 張，跳過處理")
        return
    
    # 步驟 3: 處理最後 N 張畫面
    last_frames = frame_files[-keep_frames:]
    
    if output_dir:
        # 如果指定了輸出資料夾，將檔案移動到那裡
        print(f"移動最後 {keep_frames} 張畫面到 {final_output_folder}...")
        
        for i, frame_file in enumerate(last_frames, 1):
            old_path = Path(frame_file)
            new_name = f"{video_name}[{i}].png"
            new_path = final_output_folder / new_name
            
            if not dry_run:
                try:
                    # 使用 shutil.move 而不是 rename，因為可能跨目錄
                    import shutil
                    shutil.move(str(old_path), str(new_path))
                    print(f"  {old_path.name} → {new_path}")
                except OSError as e:
                    print(f"錯誤：無法移動 {old_path.name} - {e}")
            else:
                print(f"  [DRY RUN] {old_path.name} → {new_path}")
    else:
        # 原地重新命名
        print(f"重新命名最後 {keep_frames} 張畫面...")
        
        for i, frame_file in enumerate(last_frames, 1):
            old_path = Path(frame_file)
            new_name = f"{video_name}[{i}].png"
            new_path = old_path.parent / new_name
            
            if not dry_run:
                try:
                    old_path.rename(new_path)
                    print(f"  {old_path.name} → {new_name}")
                except OSError as e:
                    print(f"錯誤：無法重新命名 {old_path.name} - {e}")
            else:
                print(f"  [DRY RUN] {old_path.name} → {new_name}")
    
    # 步驟 4: 刪除不需要的畫面檔案
    if output_dir:
        # 如果使用指定輸出資料夾，刪除所有原始畫面檔案
        frames_to_delete = frame_files  # 刪除所有原始檔案
        print(f"刪除所有 {len(frames_to_delete)} 張原始畫面檔案...")
    else:
        # 原地處理，只刪除前面的檔案
        frames_to_delete = frame_files[:-keep_frames]
        print(f"刪除前 {len(frames_to_delete)} 張畫面...")
    
    if not dry_run:
        deleted_count = 0
        for frame_file in frames_to_delete:
            try:
                os.remove(frame_file)
                deleted_count += 1
            except OSError as e:
                print(f"錯誤：無法刪除 {frame_file} - {e}")
        print(f"✅ 已刪除 {deleted_count} 張畫面")
        
        # 如果使用輸出資料夾且原始frames資料夾為空，刪除它
        if output_dir and temp_output_folder.exists():
            try:
                remaining_files = list(temp_output_folder.glob("*"))
                if not remaining_files:
                    temp_output_folder.rmdir()
                    print(f"✅ 已刪除空的資料夾：{temp_output_folder}")
            except OSError:
                pass  # 忽略刪除資料夾的錯誤
    else:
        print(f"[DRY RUN] 將刪除 {len(frames_to_delete)} 張畫面")
    
    print(f"✅ 處理完成：{video_name}.mp4")

def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="影片畫面提取和處理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例：
  python video_frame_processor.py /path/to/videos
  python video_frame_processor.py /path/to/videos --fps 8 --keep 10
  python video_frame_processor.py . --output ./processed_frames --keep 3
  python video_frame_processor.py . -o ~/Desktop/frames --fps 24 --dry-run
        """.strip()
    )
    
    parser.add_argument("folder", nargs="?", default=".", help="包含影片檔案的資料夾路徑（預設：當前目錄）")
    parser.add_argument("--fps", "-f", default="16", help="畫面提取的幀率參數（預設：16）")
    parser.add_argument("--keep", "-k", type=int, default=5, help="要保留的最後幾張畫面（預設：5）")
    parser.add_argument("--output", "-o", help="指定輸出資料夾，所有處理後的圖片都會放到這裡（預設：與影片相同位置）")
    parser.add_argument("--dry-run", "-n", action="store_true", help="試運行模式，只顯示將要執行的操作而不實際執行")
    parser.add_argument("--verbose", "-v", action="store_true", help="顯示詳細資訊")
    
    args = parser.parse_args()
    
    if args.verbose or args.dry_run:
        print("=== 影片畫面處理工具 ===")
        print(f"資料夾路徑：{args.folder}")
        print(f"幀率參數：{args.fps}")
        print(f"保留畫面：{args.keep}")
        print(f"輸出資料夾：{args.output or '與影片相同位置'}")
        if args.dry_run:
            print("模式：試運行（不執行實際操作）")
        print("=" * 30)
    
    process_video_files(args.folder, args.fps, args.keep, args.output, args.dry_run)
    
    if args.dry_run:
        print("\n*** DRY RUN 完成 - 沒有實際執行任何操作 ***")
    else:
        print("\n所有處理完成！")

if __name__ == "__main__":
    main()