# atxserver2 API文档
设备占用接口参考了openstf的[API](https://github.com/openstf/stf/blob/master/doc/API.md)

其中`$SERVER_URL`代表atxserver2的地址，如`http://localhost:4000`

所有的接口采用token认证，每个请求在 Header中增加 Authorization: Bearer xxxxx-token-xxxx

token可以在 `$SERVER_URL/user` 界面获取到

获取到token后，可以先做一个小的尝试。假设token被保存到了`$TOKEN`这个环境变量中

```
$ pip install httpie # 安装http命令行工具
$ http GET $SERVER_URL/api/v1/user Authorization:"Bearer $TOKEN"
{
    "username": "fa",
    ....
}
```

如果Token填写错误，服务器响应`403 Forbidden`

>下面的一些操作也都是用`httpie`这个小工具做的演示，使用方法见[httpie cheetsheet](https://devhints.io/httpie)


### 获取用户信息

**GET** /api/v1/user

```bash
$ http GET $SERVER_URL/api/v1/user
{
    "email": "fa@example.com",
    "username": "fa",
    "token": "xxxxx.....xxxxx",
    "createdAt": "2019-03-06T12:38:02.338000",
    ...
}
```

### 获取设备列表

**GET** /api/v1/devices

```bash
$ HTTP GET $SERVER_URL/api/v1/devices

{
    "success": true,
    "devices": [{
        "platform": "android",
        "present": true,
        "using": true,
        "codling": false,
        "userId": "fa@example.com",
        "properties": {
            "brand": "SMARTISAN",
            "version": "7.1.1"
        },
        ....
    }],
    "count": 4,
}
```

几个比较重要的字段说明

- `platform`目前有两个值`android`和`apple`
- `present`代表设备是否在线
- `colding`代表设备是否正在清理或者自检中, 此时是不能占用设备的
- `using`代表设备是否有人正在使用
- `userId`代表使用者的ID，这里的ID其实就是Email
- `properties`代表设备的一些状态信息，基本都是静态信息

### 占用设备

**POST** /api/v1/user/devices

```bash
$ http POST $SERVER_URL/api/v1/user/devices <<< '{"udid": "xx...xxxx"}'

{
    "success": true,
    "description": "Device successfully added"
}
```

### 释放设备

**DELETE** /api/v1/user/devices/${UDID}

```bash
$ http DELETE $SERVER_URL/api/v1/user/devices/xxx...xxx

{
    "success": true,
    "description": "Device successfully released"
}
```

### APK上传与解析(TODO)

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