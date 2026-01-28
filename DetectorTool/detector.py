import argparse
import glob, os, sys


from .HeadDetector import HeadDetector
from .CensorDetector import CensorDetector

#..\..\python_embeded\python.exe .\py\detector.py --mode head -f "E:\code\dev\AI\productions\games\ero\piexl\Galahad\release\01" -o .\out2 --mask --blur_size 32  
#..\..\python_embeded\python.exe .\py\detector.py --mode censor -f "E:\code\dev\AI\productions\games\ero\piexl\Galahad\release\01" --filter penis -o .\out3 --mask --blur_size 32
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['head', 'censor'], required=True)
    parser.add_argument('-f', '--folder', default='.', help='Input folder containing PNG images')
    parser.add_argument('-o', '--output', type=str, default='output')
    parser.add_argument('--width', type=int, default=260)
    parser.add_argument('--height', type=int, default=340)
    parser.add_argument('--resize', action='store_true')
    parser.add_argument('--bg', type=str, default=None, help='Background image for cropping')
    parser.add_argument('--filter', type=str, help='Censor filter label')
    parser.add_argument('-d', '--dry_run', action='store_true')
    parser.add_argument('--force_rect_crop', action='store_true')
    parser.add_argument('-m', '--mask', action='store_true')
    parser.add_argument('-b', '--blur_size', type=int, default=10)
    parser.add_argument('--info', action='store_true')
    # [新增] --top_n 參數
    parser.add_argument('--top_n', type=int, default=3, help='Number of detections to process')
    args = parser.parse_args()

    folder = args.folder
    width = args.width
    height = args.height
    output = args.output

    if args.mode == 'head':
        detector = HeadDetector(output=output, width=width, height=height)
        for img_path in glob.glob(os.path.join(folder, '*.png')):
            img_path = img_path.replace("PNG", "png")
            mask_name = os.path.basename(img_path).replace('.png', '_mask.png')
            info_name = os.path.basename(img_path).replace('.png', '.json')
            if args.dry_run:
                print(f"Would process: {img_path}")
                print(f"Would save mask to: {os.path.join(output, mask_name)}")
            else:
                if args.force_rect_crop:
                    detector.DetectAndForceRectCrop(img_path, width, resize=args.resize, bg_path=args.bg)
                # [修改] mask 模式改用迴圈處理多個 bbox
                elif args.mask:
                    result = detector.detect(img_path)
                    bboxes = detector.get_top_rects(result, top_n=args.top_n if hasattr(args, 'top_n') else 3)
                    for idx, bbox in enumerate(bboxes, start=1):
                        masked, mask, info = detector.create_blurred_mask(img_path, bbox, args.blur_size, index=idx)
                        if mask is not None:
                            detector.Crop(img_path, info.origin_rect.to_tuple(), info.rect_filename)
                            detector.save_image(mask, info.mask_name)
                            if args.info:
                                info.save_to_file(os.path.join(output, f'{info.filename}.json'))
                else:
                    _, img, bbox = detector.DetectAndCrop(img_path)
    elif args.mode == 'censor':
        if not args.filter:
            print("Please specify --filter for censor mode.")
            sys.exit(1)
        detector = CensorDetector(output=output, width=width, height=height)
        for img_path in glob.glob(os.path.join(folder, '*.png')):
            img_path = img_path.replace("PNG", "png")
            mask_name = os.path.basename(img_path).replace('.png', f'_{args.filter}_mask.png')
            info_name = os.path.basename(img_path).replace('.png', f'_{args.filter}.json')
            if args.dry_run:
                print(f"Would process: {img_path}")
                print(f"Would save mask to: {os.path.join(output, mask_name)}")
            else:
                best = detector.detect(img_path)
                bbox = detector.get_best_rect(best, filter_label=args.filter)
                if bbox:
                    if args.force_rect_crop:
                        cropped, image = detector.force_rect_crop(img_path, best, width, height)
                        detector.save_image(cropped, image)
                    # [修改] mask 模式改用迴圈處理多個 bbox
                    elif args.mask:
                        bboxes = detector.get_top_rects(best, filter_label=args.filter, top_n=args.top_n if hasattr(args, 'top_n') else 3)
                        for idx, bbox in enumerate(bboxes, start=1):
                            masked, mask, info = detector.create_blurred_mask(img_path, bbox, args.blur_size, index=idx)
                            if mask is not None:
                                detector.Crop(img_path, info.origin_rect.to_tuple(), info.rect_filename)
                                detector.save_image(mask, info.mask_name)
                                if args.info:
                                    info.save_to_file(os.path.join(output, f'{info.filename}.json'))
                    else:
                        cropped, image, bbox = detector.crop(img_path, best)
                        detector.save_image(cropped, image)
                else:
                    print(f"No censor region found for filter '{args.filter}' in {img_path}")