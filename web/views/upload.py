# coding: utf-8
#

import os
import traceback
from concurrent.futures import ThreadPoolExecutor

import tornado.concurrent
from tornado import gen
from tornado.web import stream_request_body, RequestHandler

from ..utils import parse_apkfile
from .base import BaseRequestHandler
from .multipart_streamer import MultiPartStreamer


class UploadListHandler(BaseRequestHandler):
    _thread_pool = ThreadPoolExecutor(max_workers=4)

    @tornado.concurrent.run_on_executor(executor='_thread_pool')
    def upload_image(self, binary_data):
        # return fpclient.upload_image_binary(binary_data)
        pass

    def get(self):
        self.render("upload.html")

    @gen.coroutine
    def post(self):
        # Only tornado 5.x.x support await
        # But tornado 5.x.x not support rethinkdb
        finfo = self.request.files["file"][0]
        url = yield self.upload_image(finfo['body'])
        self.write(url)


class UploadItemHandler(RequestHandler):
    async def get(self, path=None, include_body=True):
        filepath = os.path.join('uploads', path)
        if os.path.isfile(filepath):
            os.utime(filepath, None)  # update modtime
        return super(UploadItemHandler, self).get(path, include_body)



@stream_request_body
class UploadHandler(BaseRequestHandler): # replace UploadListHandler
    CORS_ORIGIN = '*'
    CORS_METHODS = 'GET,POST,OPTIONS'
    CORS_CREDENTIALS = True
    CORS_HEADERS = "x-requested-with"

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def options(self):
        # no body
        self.set_status(204)
        self.finish()

    def prepare(self):
        if self.request.method.lower() == "post":
            self.request.connection.set_max_body_size(4 << 30)  # 4G
        try:
            total = int(self.request.headers.get("Content-Length", "0"))
        except KeyError:
            total = 0
        self.ps = MultiPartStreamer(total)

    def data_received(self, chunk):
        self.ps.data_received(chunk)

    def post(self):
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
            except Exception as e:
                traceback.print_exc()
                self.write({
                    "success": False,
                    "description": str(e),
                })
                return

            target_dir = os.path.join(
                'uploads', filepart.md5sum[:2], filepart.md5sum[2:])
            if not os.path.isdir(target_dir):
                os.makedirs(target_dir)
            target_path = os.path.join(target_dir, pkg_name + '.apk')
            if not os.path.isfile(target_path):
                filepart.move(target_path)
            else:
                pass

            self.write({
                "success": True,
                "value": {
                    "url": self.request.protocol + '://' + self.request.host + "/" + target_path.replace("\\", "/"),
                    "packageName": pkg_name,
                    # "appName": app_name,
                    # "appIcon": app_icon,
                    "mainActivity": main_activity,
                    "versionCode": version_code,
                    "versionName": version_name,
                }
            })
        finally:
            self.ps.release_parts()
            self.finish()
