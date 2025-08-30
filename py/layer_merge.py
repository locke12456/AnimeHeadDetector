import argparse
import os
import json
import sys
from PIL import Image
from typing import Dict, List, Set, Optional

class ImageProcessor:
    def __init__(self, input_dir: str, layers: List[str], output_dir: str, verbose: bool = False):
        self.input_dir = input_dir
        self.layers = layers
        self.output_dir = output_dir
        self.verbose = verbose
        self.folder_structure = self._analyze_folder_structure()
        
    def _analyze_folder_structure(self) -> Dict:
        """自動分析資料夾結構，識別 origin 和各種 layer 資料夾"""
        structure = {
            'origin_path': None,
            'layer_paths': {},
            'available_images': set()
        }
        
        if self.verbose:
            print(f"分析資料夾結構: {self.input_dir}")
        
        for item in os.listdir(self.input_dir):
            item_path = os.path.join(self.input_dir, item)
            if os.path.isdir(item_path):
                if item == 'origin':
                    structure['origin_path'] = item_path
                    # 取得所有原始圖片的基礎名稱
                    for img in os.listdir(item_path):
                        if img.endswith('.PNG'):
                            base_name = img.replace('.PNG', '')
                            structure['available_images'].add(base_name)
                elif item in self.layers:
                    structure['layer_paths'][item] = item_path
                    if self.verbose:
                        print(f"  找到圖層資料夾: {item}")
                        
        if self.verbose:
            print(f"  找到 {len(structure['available_images'])} 張原始圖片")
                    
        return structure
    
    def get_layer_image_mapping(self, layer_name: str) -> Dict:
        """取得該 layer 中所有可用的圖片映射"""
        layer_path = self.folder_structure['layer_paths'].get(layer_name)
        if not layer_path:
            return {}
            
        mapping = {}
        for file in os.listdir(layer_path):
            if file.endswith('.json'):
                config_path = os.path.join(layer_path, file)
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    base_name = config['base_filename']
                    mapping[base_name] = {
                        'config': config,
                        'config_path': config_path,
                        'layer_path': layer_path
                    }
                except Exception as e:
                    print(f"讀取配置檔案錯誤 {file}: {e}")
                    
        return mapping
    
    def process_all_layers(self) -> Dict[str, Set[str]]:
        """第一階段：處理所有指定的 layers 並儲存到各自資料夾"""
        print(f"處理圖層: {self.layers}")
        print(f"可用圖片: {len(self.folder_structure['available_images'])} 張")
        
        processed_layers = {}
        
        for layer in self.layers:
            print(f"\n--- 處理圖層: {layer} ---")
            layer_mapping = self.get_layer_image_mapping(layer)
            
            if not layer_mapping:
                print(f"圖層 '{layer}' 沒有找到圖片")
                processed_layers[layer] = set()
                continue
                
            # 顯示覆蓋情況
            available_for_layer = set(layer_mapping.keys())
            coverage = len(available_for_layer) / len(self.folder_structure['available_images']) * 100
            print(f"圖層 '{layer}' 覆蓋率: {len(available_for_layer)}/{len(self.folder_structure['available_images'])} 張圖片 ({coverage:.1f}%)")
            
            if self.verbose:
                print(f"包含 {layer} 的圖片: {sorted(available_for_layer)}")
            
            processed_images = self._process_layer(layer, layer_mapping)
            processed_layers[layer] = processed_images
            
        return processed_layers
    
    def _process_layer(self, layer_name: str, layer_mapping: Dict) -> Set[str]:
        """處理單一 layer"""
        output_layer_dir = os.path.join(self.output_dir, layer_name)
        os.makedirs(output_layer_dir, exist_ok=True)
        
        processed_images = set()
        
        for base_name, mapping_info in layer_mapping.items():
            config = mapping_info['config']
            layer_path = mapping_info['layer_path']
            
            # 檢查對應的 origin 圖片是否存在
            origin_image_path = os.path.join(
                self.folder_structure['origin_path'], 
                f"{base_name}.PNG"
            )
            
            if not os.path.exists(origin_image_path):
                print(f"  警告: 找不到原始圖片 {base_name}")
                continue
                
            if self.verbose:
                print(f"  處理 {base_name}")
                
            success = self._process_image_with_config(layer_path, config, output_layer_dir)
            if success:
                processed_images.add(base_name)
                
        print(f"圖層 {layer_name} 處理完成: {len(processed_images)} 張圖片")
        return processed_images
    
    def _process_image_with_config(self, layer_path: str, config: Dict, output_dir: str) -> bool:
        """根據 JSON 配置處理單一圖片"""
        try:
            # 取得檔案路徑
            image_file = f"{config['filename']}.png"
            mask_file = f"{config['mask_name']}.png"
            
            image_path = os.path.join(layer_path, image_file)
            mask_path = os.path.join(layer_path, mask_file)
            
            if not os.path.exists(image_path):
                print(f"    錯誤: 圖片檔案不存在: {image_file}")
                return False
                
            if not os.path.exists(mask_path):
                print(f"    錯誤: 遮罩檔案不存在: {mask_file}")
                return False
                
            # 處理圖片
            output_path = os.path.join(output_dir, f"{config['base_filename']}_processed.png")
            self._adjust_and_apply_mask(image_path, mask_path, config, output_path)
            
            if self.verbose:
                print(f"    已儲存: {output_path}")
            return True
            
        except Exception as e:
            print(f"    處理圖片時發生錯誤: {e}")
            return False
    
    def _adjust_and_apply_mask(self, image_path: str, mask_path: str, config: Dict, output_path: str):
        """調整圖片座標並應用 mask"""
        try:
            # 讀取修正後的圖片
            corrected_img = Image.open(image_path).convert("RGBA")
            
            # 讀取 mask
            mask = Image.open(mask_path).convert("L")
            mask_w, mask_h = mask.size
            
            # 建立與 mask 相同大小的透明底圖
            result_img = Image.new("RGBA", (mask_w, mask_h), (0, 0, 0, 0))
            
            # 取得座標資訊
            origin_rect = config['origin_rect']
            x, y = origin_rect['x1'], origin_rect['y1']
            w, h = origin_rect['width'], origin_rect['height']
            
            # 調整修正圖片大小以符合 origin_rect
            resized_img = corrected_img.resize((w, h), Image.Resampling.LANCZOS)
            
            # 貼到指定位置
            result_img.paste(resized_img, (x, y), resized_img)
            
            # 應用 mask
            result_img.putalpha(mask)
            
            # 儲存結果
            result_img.save(output_path)
            
        except Exception as e:
            print(f"調整圖片時發生錯誤: {e}")
            raise
    
    def merge_layers_for_all_images(self, processed_layers: Dict[str, Set[str]]):
        """第二階段：為每張圖片進行圖層合成"""
        print("\n=== 開始圖層合成 ===")
        
        # 建立合成輸出資料夾
        merged_output_dir = os.path.join(self.output_dir, 'merged')
        os.makedirs(merged_output_dir, exist_ok=True)
        
        total_images = len(self.folder_structure['available_images'])
        merged_count = 0
        skipped_count = 0
        
        for base_name in sorted(self.folder_structure['available_images']):
            result = self._merge_layers_for_image(base_name, processed_layers, merged_output_dir)
            if result:
                merged_count += 1
            else:
                skipped_count += 1
                
        print(f"\n圖層合成完成:")
        print(f"  成功合成: {merged_count} 張")
        print(f"  跳過: {skipped_count} 張")
        print(f"  總計: {total_images} 張")
    
    def _merge_layers_for_image(self, base_name: str, processed_layers: Dict[str, Set[str]], output_dir: str) -> bool:
        """為單張圖片進行圖層合成"""
        try:
            # 1. 載入 origin 圖片作為底圖
            origin_path = os.path.join(self.folder_structure['origin_path'], f"{base_name}.PNG")
            if not os.path.exists(origin_path):
                print(f"  跳過 {base_name}: 找不到原始圖片")
                return False
                
            base_image = Image.open(origin_path).convert("RGBA")
            base_w, base_h = base_image.size
            
            if self.verbose:
                print(f"  合成 {base_name} (尺寸: {base_w}x{base_h})")
            
            # 2. 依序疊加 layer0, layer1, layer2 (按 self.layers 順序)
            applied_layers = []
            
            for i, layer in enumerate(self.layers):
                # 檢查該圖片是否有這個圖層
                if base_name not in processed_layers.get(layer, set()):
                    if self.verbose:
                        print(f"    跳過 layer{i} ({layer}): 圖片沒有此圖層")
                    continue
                    
                # 載入處理過的圖層圖片
                layer_image_path = os.path.join(self.output_dir, layer, f"{base_name}_processed.png")
                
                if not os.path.exists(layer_image_path):
                    if self.verbose:
                        print(f"    跳過 layer{i} ({layer}): 找不到處理後的圖片")
                    continue
                    
                layer_image = Image.open(layer_image_path).convert("RGBA")
                
                # 調整圖層尺寸以匹配 origin
                if layer_image.size != (base_w, base_h):
                    layer_image = layer_image.resize((base_w, base_h), Image.Resampling.LANCZOS)
                
                # 合成到底圖上
                base_image = Image.alpha_composite(base_image, layer_image)
                applied_layers.append(f"layer{i}({layer})")
                
                if self.verbose:
                    print(f"    已套用 layer{i} ({layer})")
            
            # 3. 儲存最終合成結果
            if applied_layers:
                final_output = os.path.join(output_dir, f"{base_name}_merged.png")
                base_image.save(final_output)
                
                layers_info = ', '.join(applied_layers)
                print(f"  ✅ {base_name}: 套用圖層 [{layers_info}] → {base_name}_merged.png")
                return True
            else:
                print(f"  ⚠️ {base_name}: 沒有可用的圖層，跳過合成")
                return False
                
        except Exception as e:
            print(f"  ❌ {base_name}: 合成失敗 - {e}")
            return False

def parse_arguments():
    """命令列參數解析 - Windows 修復版本"""
    
    def debug_args():
        print("=== 除錯: 原始命令列參數 ===")
        for i, arg in enumerate(sys.argv):
            print(f"argv[{i}]: '{arg}'")
        print()
    
    # 自動除錯模式
    if len(sys.argv) > 1 and any('debug' in arg.lower() for arg in sys.argv):
        debug_args()
    
    parser = argparse.ArgumentParser(
        prog='layer_merge.py',
        description='圖片圖層處理和合成工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用範例:
  python layer_merge.py -i "need fix" --layers pussy penis head -o output --dry-run
  python layer_merge.py --layers head pussy -i input_folder -o output_folder --verbose
  python layer_merge.py -i "path/to/images" --layers head -o output --debug
        '''
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        required=True,
        metavar='DIR',
        help='輸入資料夾路徑（包含 origin/, head/, pussy/, penis/ 子資料夾）'
    )
    
    parser.add_argument(
        '--layers',
        nargs='+',
        required=True,
        choices=['pussy', 'penis', 'head'],
        metavar='LAYER',
        help='要處理的圖層，按順序合成：pussy penis head'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        metavar='DIR',
        help='輸出資料夾路徑'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='預覽模式，分析但不實際處理圖片'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細輸出'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='除錯模式，顯示原始參數'
    )
    
    parser.add_argument(
        '--no-merge',
        action='store_true',
        help='僅處理圖層，不進行合成'
    )
    
    # Windows 路徑修復
    try:
        args = parser.parse_args()
        
        # 正規化路徑，解決 Windows 反斜線問題
        args.input = os.path.normpath(args.input.rstrip('\\\\').rstrip('/'))
        args.output = os.path.normpath(args.output.rstrip('\\\\').rstrip('/'))
        
        if args.debug:
            print("=== 除錯: 解析後的參數 ===")
            print(f"input: '{args.input}'")
            print(f"layers: {args.layers}")
            print(f"output: '{args.output}'")
            print(f"dry_run: {args.dry_run}")
            print(f"verbose: {args.verbose}")
            print()
        
        return args
        
    except SystemExit:
        print("\n=== 參數解析失敗 ===")
        debug_args()
        print("\n請嘗試以下格式：")
        print('python layer_merge.py -i "need fix" --layers head pussy penis -o output --dry-run')
        print("或者：")
        print('python layer_merge.py --layers head pussy penis -i "need fix" -o output --dry-run')
        raise

def validate_input_structure(input_dir: str, layers: List[str]) -> bool:
    """驗證輸入資料夾結構"""
    print(f"驗證輸入資料夾: {input_dir}")
    
    if not os.path.exists(input_dir):
        print(f"❌ 錯誤: 輸入資料夾不存在: {input_dir}")
        print(f"當前工作目錄: {os.getcwd()}")
        print("\n可用的資料夾:")
        try:
            for item in os.listdir('.'):
                if os.path.isdir(item):
                    print(f"  - {item}")
        except:
            pass
        return False
        
    # 檢查 origin 資料夾
    origin_path = os.path.join(input_dir, 'origin')
    if not os.path.exists(origin_path):
        print(f"❌ 錯誤: 找不到 origin 資料夾: {origin_path}")
        return False
        
    # 檢查圖片數量
    origin_images = [f for f in os.listdir(origin_path) if f.endswith('.PNG')]
    print(f"📁 origin 資料夾: {len(origin_images)} 張圖片")
    
    # 檢查指定的 layer 資料夾
    missing_layers = []
    available_layers = []
    
    for layer in layers:
        layer_path = os.path.join(input_dir, layer)
        if os.path.exists(layer_path):
            available_layers.append(layer)
            # 計算該 layer 的圖片數量
            layer_configs = [f for f in os.listdir(layer_path) if f.endswith('.json')]
            print(f"📁 {layer} 資料夾: {len(layer_configs)} 張圖片配置")
        else:
            missing_layers.append(layer)
            
    if missing_layers:
        print(f"⚠️ 警告: 缺少圖層資料夾: {missing_layers}")
        print(f"✅ 可用的圖層資料夾: {available_layers}")
        
        # 顯示實際存在的資料夾
        print(f"\n📂 {input_dir} 中的資料夾:")
        try:
            for item in os.listdir(input_dir):
                if os.path.isdir(os.path.join(input_dir, item)):
                    print(f"  - {item}")
        except Exception as e:
            print(f"無法讀取資料夾內容: {e}")
            
        if not available_layers:
            return False
    else:
        print(f"✅ 所有指定的圖層資料夾都存在: {available_layers}")
    
    return True

def main():
    """主程式"""
    try:
        args = parse_arguments()
        
        print(f"🎯 輸入資料夾: {args.input}")
        print(f"📤 輸出資料夾: {args.output}")
        print(f"🎨 處理圖層: {args.layers}")
        
        # 驗證輸入結構
        if not validate_input_structure(args.input, args.layers):
            print("\n❌ 驗證失敗，請檢查資料夾結構")
            sys.exit(1)
        
        print("\n✅ 資料夾結構驗證通過")
        
        if args.dry_run:
            print("\n=== 🔍 預覽模式 ===")
            processor = ImageProcessor(args.input, args.layers, args.output, args.verbose)
            
            # 分析會處理的內容
            print("\n分析處理內容:")
            for layer in args.layers:
                layer_mapping = processor.get_layer_image_mapping(layer)
                if layer_mapping:
                    coverage = len(layer_mapping) / len(processor.folder_structure['available_images']) * 100
                    print(f"  {layer}: {len(layer_mapping)} 張圖片 ({coverage:.1f}% 覆蓋率)")
                    if args.verbose:
                        print(f"    圖片: {sorted(layer_mapping.keys())}")
                else:
                    print(f"  {layer}: 沒有圖片")
            
            print("\n🚀 移除 --dry-run 參數來實際執行處理")
            return
        
        # 建立輸出目錄
        if not os.path.exists(args.output):
            os.makedirs(args.output)
            print(f"📁 建立輸出目錄: {args.output}")
        
        # 初始化處理器
        processor = ImageProcessor(args.input, args.layers, args.output, args.verbose)
        
        # 第一階段：處理各圖層
        print("\n=== 🎨 階段 1: 處理圖層 ===")
        processed_layers = processor.process_all_layers()
        
        if args.no_merge:
            print("\n⏹️ 僅處理圖層模式，跳過合成")
        else:
            # 第二階段：圖層合成
            print("\n=== 🔄 階段 2: 圖層合成 ===")
            processor.merge_layers_for_all_images(processed_layers)
        
        print(f"\n🎉 處理完成！結果儲存在: {args.output}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 使用者中斷執行")
        sys.exit(1)
    except SystemExit as e:
        if e.code != 0:
            print("\n=== 💡 疑難排解建議 ===")
            print("1. 檢查路徑中是否有特殊字元")
            print("2. 嘗試使用相對路徑而非絕對路徑")
            print("3. 確認資料夾確實存在")
            print("4. 使用 --debug 查看詳細參數解析")
        sys.exit(e.code)
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
        if args.verbose if 'args' in locals() else False:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()