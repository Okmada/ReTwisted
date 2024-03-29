import json
import os
import sys

import cv2
import requests


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class Webhook:
    def __init__(self, config):
        self.config = config

    def send(self, data, data_image, code_image):
        url = self.config.get(["config", "webhook", "url"])
        if not url:
            return
        
        role_id = self.config.get(["config", "webhook", "role id"])
        user_id = self.config.get(["config", "webhook", "user id"])

        payload = {
            "username": "Re:Twisted",
            "avatar_url": "",

            "content": (f"<@&{role_id}>" if role_id else "") + (f"<@{user_id}>" if user_id else ""),

            "embeds": [{
                "title": "Winds are picking up on speed :cloud_tornado:",
                "color": "333",

                "fields": [
                    {
                        "name": "Weather :cloud:",
                        "value": f"```{'\n'.join([f'{key}: {item}' for key, item in data.items()])}```",
                        "inline": True
                    },
                ],

                "image": {"url": "attachment://data.png"},
                "thumbnail": {"url": "attachment://code.png"},
                "footer": {
                    "text": "Re:Twisted • by Ad_amko",
                    "icon_url": "attachment://icon.png"
                }
            }]
        }

        files = {
            "_code.png": ("code.png", cv2.imencode(".png", code_image)[1].tostring()),
            "_data.png": ("data.png", cv2.imencode(".png", data_image)[1].tostring()),
            "_icon.png": ("icon.png", open(resource_path("icon.png"), "rb").read()),
            'payload_json': (None, json.dumps(payload)),
        }

        return requests.post(url, files=files)
