# Anime Head Detector

This project provides a simple command-line tool to batch detect heads in all PNG images within a folder and crop them to a specified output folder.

## Requirements

- Python 3.x
- Please refer to the imports in `HeadDetector.py` for additional dependencies

## Usage

1. Place the PNG images you want to process in the same folder.
2. Run the following command:

```bash
python py/test_HeadDetector.py [folder_path] -o [output_folder] -w [width] -t [height]
```

### Arguments

- `folder_path`: The folder containing images to process. Defaults to the current directory.
- `-o, --output`: Output folder for cropped images. Defaults to `output`.
- `-w, --width`: Width of the cropped images. Defaults to 260.
- `-t, --height`: Height of the cropped images. Defaults to 340.
- `--dry_run`: Only display the files that would be processed, without actually cropping.

### Examples

```bash
python py/test_HeadDetector.py ./images -o ./cropped -w 256 -t 320
```

Or to only display the files that would be processed:

```bash
python py/test_HeadDetector.py ./images --dry_run
```
### Example Input and Output

Suppose you have an input image `input/1.png`. After running the tool, the cropped result will be saved as `output/1.png`.

**Input:**  
`input/1.png`  
![https://github.com/locke12456/AnimeHeadDetector/blob/main/input/1.png?raw=true](https://github.com/locke12456/AnimeHeadDetector/blob/main/input/1.png?raw=true)

**Output:**  
`output/1.png`  
![https://github.com/locke12456/AnimeHeadDetector/blob/main/output/1.png?raw=true](https://github.com/locke12456/AnimeHeadDetector/blob/main/output/1.png?raw=true)
## Notes

- Make sure `HeadDetector.py` is correctly placed in the `py` folder.
- The output folder will be created automatically if it does not exist.
