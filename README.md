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
目前采用tornado作为服务端，使用rethinkdb作为数据库

## Thanks
- [https://www.easyicon.net](https://www.easyicon.net/iconsearch/hub/)

## LICENSE
[MIT](LICENSE)
