import json
import logging

import cv2
import requests

import utils
from config import ConfigManager
from constants import NAME
from data import Data
from roblox import RobloxTypes


class Webhook:
    def send(self, roblox_type: RobloxTypes, data: Data, webhook_images: dict) -> requests.Response | None:
        url = ConfigManager().get(["webhook", "url"])
        if not url:
            return

        hasThumbnail = "thumbnail" in webhook_images
        hasImage = "image" in webhook_images

        thumbnail = webhook_images.get("thumbnail")
        image = webhook_images.get("image")

        server = ConfigManager().get(["roblox", roblox_type, "server"])

        share_link = ConfigManager().get(["webhook", "share link"])
        role_id = ConfigManager().get(["webhook", "role id"])
        user_id = ConfigManager().get(["webhook", "user id"])

        payload = {
            "username": NAME,
            "avatar_url": "",

            "content": (f"<@&{role_id}>" if role_id else "") + (f"<@{user_id}>" if user_id else ""),

            "embeds": [{
                "title": "Winds are picking up on speed :cloud_tornado:",
                "color": "333",

                "fields": [
                    {
                        "name": "Weather :cloud:",
                        "value": "```" + "\n".join([f"{key}: {item}" for key, item in data.items()]) + "```",
                        "inline": True
                    },
                    *([{
                        "name": "Server link :desktop:",
                        "value": f"[Link to server](https://www.roblox.com/games/6161235818/Twisted-BETA?privateServerLinkCode={server})",
                        "inline": True
                    }] if server and share_link else [])
                ],

                **({"thumbnail": {"url": "attachment://thumbnail.png"}} if hasThumbnail else {}),
                **({"image": {"url": "attachment://image.png"}} if hasImage else {}),
                "footer": {
                    "text": f"{NAME} • by Ad_amko",
                    "icon_url": "attachment://icon.png"
                }
            }]
        }

        files = {
            **({"_thumbnail.png": ("thumbnail.png", cv2.imencode(".png", thumbnail)[1].tostring())} if hasThumbnail else {}),
            **({"_image.png": ("image.png", cv2.imencode(".png", image)[1].tostring())} if hasImage else {}),
            "_icon.png": ("icon.png", open(utils.resource_path("assets/icon.png"), "rb").read()),
            'payload_json': (None, json.dumps(payload)),
        }

        try:
            return requests.post(url, files=files)
        except Exception as e:
            logging.error("Could not send message to Discord webhook.")
            logging.exception(e)
            return
