from typing import List, Tuple

import cv2
import numpy as np


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

def split_characters(img: np.ndarray) -> None:
    cropped = crop_image(img)

    characters_contours = find_contours(cropped)

    for contour in characters_contours:
        hull = cv2.convexHull(contour, returnPoints=False)
        defects = cv2.convexityDefects(contour, hull)

        if defects is not None:
            short_lines_filter = filter(lambda e: np.linalg.norm(np.array(contour[e[0][0]][0]) - np.array(contour[e[0][1]][0])) > cropped.shape[0]//2, defects)
            vertical_lines_filter = filter(lambda e: abs(np.arctan2(*(np.array(contour[e[0][0]][0]) - np.array(contour[e[0][1]][0]))[::-1]) % np.pi - (np.pi / 2)) > np.pi / 4, short_lines_filter)
            sorted_defects = sorted(vertical_lines_filter, key=lambda e: np.array(contour[e[0][2]][0])[0])

            for i in range(0, 2 * (len(sorted_defects) // 2), 2):
                s1, e1, f1, d1 = sorted_defects[i][0]
                s2, e2, f2, d2 = sorted_defects[i + 1][0]

                far1 = tuple(contour[f1][0])
                far2 = tuple(contour[f2][0])

                cv2.line(cropped, far1, far2, 0, 10)
