## atxserver2
移动设备管理平台

**仍在开发中,暂时还不能用**

![img](static/favicon-dark.png)

## 环境依赖
- Python3.6+
- [RethinkDB](https://rethinkdb.com/)


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

## Thanks
- [https://www.easyicon.net](https://www.easyicon.net/iconsearch/hub/)
- <https://github.com/mikusjelly/apkutils>
- <https://github.com/gtsystem/python-remotezip>


## LICENSE
[MIT](LICENSE)
