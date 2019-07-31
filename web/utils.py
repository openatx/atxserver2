# coding: utf-8
#

import json
import os
import time
import shutil
from xml.dom import minidom

from apkutils2 import APK, apkfile


class Manifest(object):
    def __init__(self, apk: APK):
        content = apk.get_org_manifest()
        self._dom = minidom.parseString(content)
        self._permissions = None
        self._apk = apk

    @property
    def icon_path(self):
        return self._apk.get_app_icon()

    def save_icon(self, icon_path: str):
        """
        Args:
            icon_path (str): should endwith .png
        """
        zip_icon_path = self._apk.get_app_icon()
        with apkfile.ZipFile(self._apk.apk_path) as z:
            with z.open(zip_icon_path) as f:
                with open(icon_path, 'wb') as w:
                    shutil.copyfileobj(f, w)

    @property
    def package_name(self):
        return self._dom.documentElement.getAttribute('package')

    @property
    def version_code(self):
        return self._dom.documentElement.getAttribute("android:versionCode")

    @property
    def version_name(self):
        return self._dom.documentElement.getAttribute("android:versionName")

    @property
    def permissions(self):
        if self._permissions is not None:
            return self._permissions

        self._permissions = []
        for item in self._dom.getElementsByTagName("uses-permission"):
            self._permissions.append(str(item.getAttribute("android:name")))
        return self._permissions

    @property
    def main_activity(self):
        """
        Returns:
            the name of the main activity
        """
        x = set()
        y = set()

        for item in self._dom.getElementsByTagName("activity"):
            for sitem in item.getElementsByTagName("action"):
                val = sitem.getAttribute("android:name")
                if val == "android.intent.action.MAIN":
                    x.add(item.getAttribute("android:name"))

            for sitem in item.getElementsByTagName("category"):
                val = sitem.getAttribute("android:name")
                if val == "android.intent.category.LAUNCHER":
                    y.add(item.getAttribute("android:name"))

        z = x.intersection(y)
        if len(z) > 0:
            return z.pop()
        return None


def parse_apkfile(file: str) -> Manifest:
    '''
    Args:
        - file: filename

    Returns:
        Manifest(Class)
    '''
    return Manifest(APK(file))


def remove_useless_apk():
    """
    remove old files to free disk space
    
    tornado.ioloop.PeriodicCallback(remove_useless_apk, 60 * 1000).start() # milliseconds, equals to 10 minutes
    """
    abandon_timeline = time.time() - 60 * 60 * 24 * 10  # 10 days
    for root, dirs, files in os.walk("uploads"):
        for file in files:
            if not file.endswith('.apk'):
                continue
            path = os.path.join(root, file)
            if os.stat(path).st_mtime > abandon_timeline:
                continue
            # force remove file
            try:
                os.unlink(path)
                print("remove", path)
            except PermissionError as e:
                print("remove err", path, str(e))

        # finally cleanup
        if not os.listdir(root):
            print("remove empty dir", root)
            os.rmdir(root)


if __name__ == '__main__':
    # test
    m = parse_apkfile("your-apk.apk")
    print(m.version_code)
