import argparse
import glob, os, sys
sys.path.insert(0, os.path.abspath("./py"))
from HeadDetector import HeadDetector

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('folder_name', nargs='?', default='.', help='Input folder containing PNG images')
    parser.add_argument('-f', '--folder_name', dest='folder_name_opt', help='Input folder (overrides positional)')
    parser.add_argument('-w', '--width', type=int, default=260, help='Width for cropping')
    parser.add_argument('-t', '--height', type=int, default=340, help='Height for cropping')
    
    parser.add_argument('-o', '--output', type=str, default='output', help='Output folder for cropped images')
    
    parser.add_argument('-i', '--info', action='store_true', help='Save rect info to JSON file')
    parser.add_argument('-m', '--mask', action='store_true', help='mask cropped images with blurred alpha')
    parser.add_argument('-b', '--blur_size', type=int, default=10, help='Blur size for alpha mask')
    
    parser.add_argument('--dry_run', action='store_true', help='Dry run, do not save cropped images')
    parser.add_argument('--force_rect_crop', action='store_true', help='Force rectangular crop')
    args = parser.parse_args()

    folder = args.folder_name_opt or args.folder_name
    width = args.width
    height = args.height
    dry_run = args.dry_run

    for img_path in glob.glob(os.path.join(folder, '*.png')):
        if dry_run:
            print(f"Would process: {img_path}")
        else:
            detector = HeadDetector(output=args.output, width=width, height=height)
            if args.force_rect_crop:
                detector.DetectAndForceRectCrop(img_path, args.width)
            else:
                mask_name = os.path.basename(img_path).replace('.png', '_mask.png')
                info_name = os.path.basename(img_path).replace('.png', '.json')
                if args.dry_run:
                    print(f"Processing: {img_path}")
                    print(f"Save mask to: {os.path.join(args.output, mask_name)}")  
                else:
                    
                    if args.mask:
                        bbox = detector.Detect(img_path)
                        masked, mask, info = detector.create_blurred_mask(img_path, bbox, args.blur_size)
                        
                        if mask is not None:
                            detector.Crop(img_path, info.origin_rect.to_tuple())
                            detector.save_image(mask, mask_name)
                            info.save_to_file(os.path.join(args.output, info_name))
                    else:
                        _, img, bbox =detector.DetectAndCrop(img_path)
            #DetectHead(img_path, output=args.output, width=width, height=height)