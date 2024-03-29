import asyncio

import cv2
from winsdk.windows.graphics.imaging import (BitmapAlphaMode,
                                             BitmapPixelFormat, SoftwareBitmap)
from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.security.cryptography import CryptographicBuffer


class Ocr:
    @staticmethod
    def ibuffer(bytes):
        """create WinRT IBuffer instance from a bytes-like object"""
        return CryptographicBuffer.create_from_byte_array(bytes)

    @staticmethod
    def convert_to_buffer(img):
        """create WinRT IBuffer from numpy image"""
        H, W, *_ = img.shape

        if len(img.shape) == 2:
            FORMAT = BitmapPixelFormat.GRAY8
            ALPHA = BitmapAlphaMode.IGNORE
        else:
            FORMAT = BitmapPixelFormat.BGRA8
            ALPHA = BitmapAlphaMode.STRAIGHT

            if img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

        bytes = img.tobytes()

        buffer = Ocr.ibuffer(bytes)
        return SoftwareBitmap.create_copy_from_buffer(buffer, FORMAT, W, H, ALPHA)

    @staticmethod
    async def ensure_coroutine(awaitable):
        return await awaitable

    @staticmethod
    def blocking_wait(awaitable):
        return asyncio.run(Ocr.ensure_coroutine(awaitable))

    @staticmethod
    def ocr(img):
        languages_with_ocr = list(OcrEngine.available_recognizer_languages)
        languages_with_ocr.sort(key=lambda e: "en-" in e.language_tag, reverse=True)
        
        assert len(languages_with_ocr), "No language supports OCR"

        ocr_engine = OcrEngine.try_create_from_language(languages_with_ocr[0])

        buffer = Ocr.convert_to_buffer(img)

        res = Ocr.blocking_wait(ocr_engine.recognize_async(buffer))
        # print(res.text)
        return res.text
