# coding: utf-8
#

import os
import traceback
from concurrent.futures import ThreadPoolExecutor

import tornado.concurrent
from tornado import gen
from tornado.web import stream_request_body, StaticFileHandler

from ..utils import parse_apkfile
from .base import BaseRequestHandler
from .multipart_streamer import MultiPartStreamer


class UploadItemHandler(StaticFileHandler):
    async def get(self, path=None, include_body=True):
        filepath = os.path.join('uploads', path)
        if os.path.isfile(filepath):
            os.utime(filepath, None)  # update modtime
        return super().get(path, include_body)


@stream_request_body
class UploadListHandler(BaseRequestHandler):  # replace UploadListHandler
    async def prepare(self):
        await super().prepare()

        if self.request.method.lower() == "post":
            self.request.connection.set_max_body_size(8 << 30)  # 8G
        try:
            total = int(self.request.headers.get("Content-Length", "0"))
        except KeyError:
            total = 0
        self.ps = MultiPartStreamer(total)

    def data_received(self, chunk):
        self.ps.data_received(chunk)

    def get(self):
        self.render("upload.html")

    async def post(self):
        try:
            self.ps.data_complete()  # close the incoming stream.
            parts = self.ps.get_parts_by_name('file')
            if len(parts) == 0:
                self.write({
                    "success": False,
                    "description": "no form \"file\" providered",
                })
                return

            filepart = parts[0]
            filepart.f_out.seek(0)
            try:
                apk = parse_apkfile(filepart.f_out)
                pkg_name = apk.package_name
                main_activity = apk.main_activity
                version_code = apk.version_code
                version_name = apk.version_name
                icon_path = apk.icon_path
            except Exception as e:
                traceback.print_exc()
                self.write({
                    "success": False,
                    "description": str(e),
                })
                return

            target_dir = os.path.join('uploads', filepart.md5sum[:2],
                                      filepart.md5sum[2:])
            os.makedirs(target_dir, exist_ok=True)

            _, filext = os.path.splitext(filepart.get_filename())
            target_path = os.path.join(target_dir, pkg_name + filext)

            apk_url = self.request.protocol + '://' + self.request.host + "/" + target_path.replace(
                "\\", "/")
            icon_url = None
            if icon_path:
                apk.save_icon(os.path.join(target_dir, "icon.png"))
                icon_url = self.request.protocol + '://' + self.request.host + "/" + target_dir.replace(
                    "\\", "/") + "/icon.png"

            if not os.path.isfile(target_path):
                filepart.move(target_path)
            else:
                pass
            self.write({
                "success": True,
                "data": {
                    "url": apk_url,
                    "packageName": pkg_name,
                    "iconUrl": icon_url,
                    "iconPath": icon_path,
                    "md5sum": filepart.md5sum,
                    "mainActivity": main_activity,
                    "versionCode": version_code,
                    "versionName": version_name,
                }
            })
        except Exception as e:
            self.set_status(400)  # bad request
            self.write({"success": false, "description": str(e)})
        finally:
            self.ps.release_parts()
            self.finish()
