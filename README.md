## atxserver2
移动设备管理平台

**仍在开发中,暂时还不能用**

![img](static/favicon-dark.png)

## 环境依赖
- Python3.6+
- [RethinkDB](https://rethinkdb.com/)

## Features
- [x] 设备远程控制

    - [x] 右键屏幕等价于点击HOME键
    - [x] 屏幕到后台自动断开WebSocket连接

- [x] APK上传和解析

## 部署
```bash
pip install -r requirements.txt
```

最简单的启动方法 （默认连接的rethinkdb地址 `localhost:28015`)

```bash
python3 main.py
```

使用OpenID作为认证方式(目前好像就网易在用，其他人可以忽略)

```
python3 main.py --auth openid
```

更改默认RethinkDB地址(Linux环境下)

```bash
# the bellow is default value
export RDB_HOST=localhost
export RDB_PORT=28015
export RDB_USER=admin
export RDB_PASSWD=
export RDB_DBNAME=atxserver2

python3 main.py
```

## Developers
目前采用tornado+rethinkdb

目录结构参考了django, 代码绝大多数都用到的`async`的功能

```
|-- static  静态目录
|-- templates 前端界面
|-- web  网页代码
      |-- urls.py 路由整合文件
      |-- settings.py 配置文件
      |-- database.py 数据库操作相关
      |-- utils.py 常用配置
      |-- views 每个界面的逻辑
        |-- slave.py 与atxslave通信用
        |-- device.py 设备相关路由
        |-- base.py 基于RequestHandler的基类
```

设备占用接口参考[openstf API](https://github.com/openstf/stf/blob/master/doc/API.md)

## 接口

占用设备

**POST** 
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

## Thanks
- [https://www.easyicon.net](https://www.easyicon.net/iconsearch/hub/)
- <https://github.com/mikusjelly/apkutils>
- <https://github.com/gtsystem/python-remotezip>


## LICENSE
[MIT](LICENSE)
