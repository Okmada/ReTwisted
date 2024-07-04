import re
from typing import List, Tuple

import cv2
import numpy as np

import ocr


def find_contours(image: np.ndarray) -> List[Tuple[Tuple[int, int]]]:
    return list(cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0])

def get_contour_center(contour: np.ndarray) -> Tuple[int, int]:
    M = cv2.moments(contour)
    center_X = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
    center_Y = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0
    return (center_X, center_Y)

def extract_contour(image: np.ndarray, contour: np.ndarray) -> np.ndarray:
    X, Y, W, H = cv2.boundingRect(contour)

    mask = np.zeros([H, W], np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, -1, offset=(-X, -Y))
    points = np.where(mask)

    cutout = np.zeros([H, W] + list(image.shape[2:]), np.uint8)
    cutout[points] = image[tuple(np.dstack((np.dstack(points) + [Y, X])[0])[0])]

    return cutout

def crop_image(image: np.ndarray, top=True, bottom=True, left=True, right=True) -> np.ndarray:
    H, W, *_ = image.shape

    non_empty_columns = np.where(image.max(axis=0) > 0)[0]
    non_empty_rows = np.where(image.max(axis=1) > 0)[0]

    crop_box = (min(non_empty_rows) if top else 0,
                max(non_empty_rows)+1 if bottom else H,
                min(non_empty_columns) if left else 0,
                max(non_empty_columns)+1 if right else W)
    return image[crop_box[0]:crop_box[1], crop_box[2]:crop_box[3]]

def mask_transparent(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    assert mask.shape[:2] == image.shape[:2], "missmatched mask shape"

    transparent_image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    transparent_image[mask == 0] = [0]*4

    return transparent_image

def read_text(image: np.ndarray) -> str:
    scale = 325 / image.shape[0]

    image = cv2.copyMakeBorder(image, *[int(image.shape[0] * 0.35)] * 4, cv2.BORDER_CONSTANT)
    new_dims = [round(dim * scale) for dim in image.shape[:2]][::-1]
    image = cv2.resize(image, new_dims, interpolation=cv2.INTER_LINEAR)

    return ocr.ocr(image)

def read_number(image: np.ndarray) -> str:
    text = read_text(image)

    text = text.replace("Ø", "0")
    text = text.replace("ø", "0")
    text = text.replace("l", "1")

    nums = re.findall("([0-9]+[.]{1}[0-9]+|[0-9]+)", text)

    return nums[-1] if nums else "0"
