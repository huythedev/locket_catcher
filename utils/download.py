import requests
import io
from PIL import Image
import logging

def download_video_file_sync(url, save_path):
    """Download a video file from the given URL and save it to the specified path."""
    try:
        response = requests.get(url, stream=True, timeout=(10, 20))
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Successfully downloaded video to {save_path}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download video from {url}: {e}")
        raise
    except IOError as e:
        logging.error(f"Failed to save video to {save_path}: {e}")
        raise

def download_and_convert_image_to_png_sync(url, save_path):
    """Download an image from the given URL, convert it to PNG, and save it."""
    try:
        response = requests.get(url, stream=True, timeout=(10, 20))
        response.raise_for_status()
        img_bytes = io.BytesIO(response.content)
        img = Image.open(img_bytes)
        img.convert("RGB").save(save_path, "PNG")
        logging.info(f"Successfully downloaded and converted image to PNG: {save_path}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download image from {url}: {e}")
        raise
    except IOError as e:
        logging.error(f"Failed to save image to {save_path}: {e}")
        raise
    except Exception as e:
        logging.error(f"Failed to process image from {url} for saving to {save_path}: {e}")
        raise