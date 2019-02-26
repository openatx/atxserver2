# atxserver2 API文档
设备占用接口参考了openstf的[API](https://github.com/openstf/stf/blob/master/doc/API.md)

### 占用设备

**POST** /api/v1/devices


### APK上传与解析

**POST** /uploads

```bash
$ http POST $SERVER_URL/uploads file@wakey.appso.apk
HTTP/1.1 200 OK
Content-Length: 411
Content-Type: application/json; charset=UTF-8
Date: Wed, 23 Jan 2019 06:28:54 GMT
Server: TornadoServer/4.5.3

{
    "data": {
        "url": "http://localhost:4000/uploads/13/f46364434b526b77620ebf9bcf7322/com.doublep.wakey.apk",
        "md5sum": "13f46364434b526b77620ebf9bcf7322",
        "iconPath": "res/drawable-xxhdpi/ic_launcher.png",
        "iconUrl": "http://localhost:4000/uploads/13/f46364434b526b77620ebf9bcf7322/icon.png",
        "packageName": "com.doublep.wakey",
        "mainActivity": ".Bulb",
        "versionCode": "18",
        "versionName": "2.3"
    },
    "success": true
}
```