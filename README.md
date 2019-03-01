## atxserver2
移动设备管理平台

**开发中,即将能开始用了**

![img](static/favicon-dark.png)

## 环境依赖
- Python3.6+
- [RethinkDB](https://rethinkdb.com/)

## Features
- [x] APK上传和解析
- [x] 设备远程控制

    - [x] 鼠标右键点击BACK，中间点击HOME
    - [x] 屏幕到后台自动断开WebSocket连接
    - [x] 鼠标滚轮翻屏
    - [ ] 上传安装应用
    - [ ] 常用功能(打开网址, 电源)


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

## 操作指南
鼠标操作

- Right-Click: BACK
- Middle-Click: HOME

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

## 接口
详情点击 接口[REST API](API.md)


## Thanks
- <https://github.com/openstf>
- <https://github.com/Genymobile/scrcpy>
- [https://www.easyicon.net](https://www.easyicon.net/iconsearch/hub/)
- <https://github.com/mikusjelly/apkutils>
- <https://github.com/gtsystem/python-remotezip>
- <https://github.com/willerce/WhatsInput>

## LICENSE
[MIT](LICENSE)
