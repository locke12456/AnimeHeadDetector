# Anime Head Detector

This project provides a simple command-line tool to batch detect heads in all PNG images within a folder and crop them to a specified output folder.  
**The cropping region's width and height can be customized using the `-w` and `-t` options. The cropping area will be adjusted according to the specified width, ensuring the output images have the desired dimensions.**

## Features

- Batch process all PNG images in a folder
- Detect and crop anime heads automatically
- Customizable crop width and height (cropping region will be set according to the specified width and height)
- Optional dry run mode to preview which files will be processed
- Option to force rectangular cropping
- Option to save blurred alpha mask and crop info as JSON

## Requirements

- Python 3.x
- Additional dependencies may be required; please refer to the imports in `HeadDetector.py`

## Usage

1. Place the PNG images you want to process in the same folder.
2. Run the following command:

```bash
python py/test_HeadDetector.py [folder_path] -o [output_folder] -w [width] -t [height] [--force_rect_crop] [--dry_run] [--mask] [--info] [--blur_size BLUR]
```

### Arguments

- `folder_path`: The folder containing images to process. Defaults to the current directory.
- `-o, --output`: Output folder for cropped images. Defaults to `output`.
- `-w, --width`: **Width of the cropped images. The cropping region will be adjusted to this width. Defaults to 260.**
- `-t, --height`: **Height of the cropped images. The cropping region will be adjusted to this height. Defaults to 340.**
- `--force_rect_crop`: Force rectangular crop instead of default cropping.
- `--dry_run`: Only display the files that would be processed, without actually cropping.
- `-m, --mask`: Save blurred alpha mask for each cropped image.
- `-i, --info`: Save crop rectangle info as a JSON file.
- `-b, --blur_size`: Blur size for alpha mask (default: 10).

### Examples

Process all images in `./images` and save cropped results to `./cropped` with custom size:

```bash
python py/test_HeadDetector.py ./images -o ./cropped -w 256 -t 320
```

Preview which files would be processed (no cropping will be performed):

```bash
python py/test_HeadDetector.py ./images --dry_run
```

Force rectangular crop:

```bash
python py/test_HeadDetector.py ./images --force_rect_crop
```

Save blurred alpha mask and crop info:

```bash
python py/test_HeadDetector.py ./images -m -i
```

### Example Input and Output

Suppose you have an input image `input/1.png`. After running the tool, the cropped result will be saved as `output/1.png`.

**Input:**  
`input/1.png`  
![input/1.png](https://github.com/locke12456/AnimeHeadDetector/blob/main/input/1.png?raw=true)

**Output:**  
`output/1.png`  
![output/1.png](https://github.com/locke12456/AnimeHeadDetector/blob/main/output/1.png?raw=true)

## Notes

- Make sure `HeadDetector.py` is correctly placed in the `py` folder.
- The output folder will be created automatically if it does not exist.
- Only PNG images (`*.png`) will be processed.
- **The cropping region will be set to the specified width and height, and will not exceed the image boundaries.**

## License

MIT License
