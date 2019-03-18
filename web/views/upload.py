# coding: utf-8
#

import os
import traceback
from concurrent.futures import ThreadPoolExecutor

import tornado.concurrent
from tornado import gen
from tornado.web import stream_request_body, StaticFileHandler

from ..utils import parse_apkfile
from .base import AuthRequestHandler
from .multipart_streamer import MultiPartStreamer


class UploadItemHandler(StaticFileHandler):
    async def get(self, path, include_body=True):
        filepath = self.get_absolute_path(self.root, path)
        if os.path.isfile(filepath):
            os.utime(filepath, None)  # update modtime
        await super().get(path, include_body)


@stream_request_body
class UploadListHandler(AuthRequestHandler):  # replace UploadListHandler
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

    def parse_filepart(self, filepart) -> dict:
        _, ext = os.path.splitext(filepart.get_filename())
        if ext == ".apk":
            apk = parse_apkfile(filepart.f_out)
            # icon_url = None
            # if icon_path:
            #     apk.save_icon(os.path.join(target_dir, "icon.png"))
            #     icon_url = self.request.protocol + '://' + self.request.host + "/" + target_dir.replace(
            #         "\\", "/") + "/icon.png"
            return {
                "packageName": apk.package_name,
                "mainActivity": apk.main_activity,
                "versionCode": apk.version_code,
                "versionName": apk.version_name,
                "iconPath": apk.icon_path,
            }
        return {}

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

            # parse apk or ipa
            fileinfo = self.parse_filepart(filepart)

            # save file
            target_dir = os.path.join('uploads', filepart.md5sum[:2],
                                      filepart.md5sum[2:])
            os.makedirs(target_dir, exist_ok=True)
            _, ext = os.path.splitext(filepart.get_filename())
            target_path = os.path.join(target_dir, "file" + ext)
            if not os.path.isfile(target_path):
                filepart.move(target_path)

            # gen file info
            url = ''.join([
                self.request.protocol, '://', self.request.host, "/",
                target_path.replace("\\", "/")
            ])
            data = dict(url=url, md5sum=filepart.md5sum)
            data.update(fileinfo)
            self.write({
                "success": True,
                "data": data,
            })
        except Exception as e:
            traceback.print_exc()
            # self.set_status(400)  # bad request
            self.write({"success": False, "description": str(e)})
        finally:
            self.ps.release_parts()
