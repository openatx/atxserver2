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
# 支持的过滤参数 ?platform=apple&usable=true

{
    "success": true,
    "devices": [{
        "platform": "android",
        "present": true,
        "using": true,
        "colding": false,
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

usable等价于`{present: true, using: false, colding: false}`

### 获取单个设备信息（不包含sources字段)

**GET** /api/v1/devices

```bash
$ HTTP GET $SERVER_URL/api/v1/devices/${udid}
{
    "success": true,
    "device": {
        "udid": "6EB0217704000486",
        "platform": "android",
        "present": true,
        "using": false,
        "colding": false,
        "userId": null,
        "properties": {
            "brand": "HONOR",
            "model": "DUK-AL20",
            "name": "华为 荣耀 V9",
            "serial": "6EB0217704000486",
            "version": "8.0.0"
        },
        "updatedAt": "2019-03-29T14:53:56.569000",
        "usingBeganAt": "2019-03-28T18:33:23.100000"
    }
}
```

If udid not found, status code = 400

### 占用设备

**POST** /api/v1/user/devices

```bash
$ http POST $SERVER_URL/api/v1/user/devices <<< '{"udid": "xx...xxxx"}'

{
    "success": true,
    "description": "Device successfully added"
}
```

通过payload传递数据，JSON格式

- udid是必须字段(Android设备的udid是设备的product，mac地址，serial组合生成的)
- idleTimeout: 设备最长空闲时间 seconds(可选), 当前时间 - 活动时间 > idleTimeout 自动释放设备

```json
{
    "udid": "xlj1311l2fkjkzdf",
    "idleTimeout": 600
}
```

如果你是管理员，你还可以传`email`将设备占用人指定为其他人。

```json
{
    "udid": "xlj1311l2fkjkzdf",
    "email": "hello@world.com"
}
```

**更新活动时间接口**

**GET** /api/v1/user/devices/{$UDID}/active

```bash
$ http GET /api/v1/user/devices/${UDID}/active
{
    "success": true,
    "description": "Device activated time updated"
}
```

### 获取用户设备信息(包含source字段)

**GET** /api/v1/user/devices/${UDID}

```bash
$ http GET $SERVER_URL/api/v1/user/devices/${UDID}

{
    "success": true,
    "device": {
        "platform": "android",
        "present": true,
        "using": true,
        "colding": false,
        "userId": "fa@example.com",
        "properties": {
            "brand": "SMARTISAN",
            "version": "7.1.1"
        },
        "source": {
            "atxAgentAddress": "10.0.0.1:20001",
            "remoteConnectAddress": "10.0.0.1:20002",
            "whatsInputAddress": "10.0.0.1:20003",
            "secret": "6NC5Tls1",
            "url": "http://10.0.1.1:3500",
        }
    }
}
```

比 `/api/v1/devices` 获取到的设备，多出一个source字段，下面详细说明下

Android和iOS source都包含的部分

- url: provider的URL，通过可以让设备cold和安装应用

Android的source独有内容

- atxAgentAddress: 主要用于[uiautomator2](https://github.com/openatx/uiautomator2)测试框架
- remoteConnectAddress: 用于`adb connect`连接使用
- whatsInputAddress: 这个可以不用关注，他主要提供远程真机的实时输入法

iOS的source独有内容

- wdaUrl: webdriveragent用到的http接口，eg `http://10.0.0.1:9300`

WebSocket访问`${wdaUrl}/screen`可以获取到当前的图片流

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

### 通过PROVIDER进行APK安装

这个要用到`PROVIDER_URL`对应设备信息接口返回值中的`source.url`字段,另外需要指定udid（因为provider可能连接了多个手机）

**POST** $PROVIDER_URL/app/install?udid=xxxx

```bash
$ http --form POST $PROVIDER_URL/app/install?udid=xxxx url==http://example.com/some.apk launch==true
# launch是可选参数，代表是否安装成功后启动应用
# 成功返回 200
{
    "success": true
    "return": 0,
    "output": "Success\r\n",
    "packageName": "io.appium.android.apis",
}
# 失败返回 400 or 500
{
    "description": "Failure reason",
    "success": false
}
```

### 通过PROVIDER进行IPA安装

这个要用到`PROVIDER_URL`对应设备信息接口返回值中的`source.url`字段,另外需要指定udid（因为provider可能连接了多个手机）

**POST** $PROVIDER_URL/app/install?udid=xxxx

```bash
$ http --form POST $PROVIDER_URL/app/install?udid=xxxx url==http://example.com/some.ipa
# 成功返回 200
{
    "success": true
    "return": 0,
    "output": "Success",
}
# 失败返回 400 or 500
{
    "description": "Failure reason",
    "success": false
}
```