## atxserver2
移动设备管理平台

**Beta，尝鲜者可提前体验，虽然还有很多没开发的**

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
    - [x] 常用功能(打开网址, 电源)


## 部署
**Step 1**

先准备好一个rethinkdb服务器(推荐部署到Linux上) 具体方法查看[RethinkDB安装文档](https://rethinkdb.com/docs/install/)

**Step 2**

安装并启动Server，这里需要Python3.6以上版本

先将代码clone到本地，使用下面的方法安装依赖

```bash
pip3 install -r requirements.txt
```

最简单的启动方法 （默认连接的rethinkdb地址 `localhost:28015`)

```bash
# 启动方式，这也是最简单的启动方法
python3 main.py

# 指定认证方式
python3 main.py --auth simple # 默认是一个非常simple的认证，输入邮箱就可以
python3 main.py --auth openid # 网易内部使用
# 其他的认证方式还有待添加，非常欢迎PR

# 设置监听端口
python3 main.py --port 4000 # 默认监听的就是这个地址
```

通过环境变量的修改，可以更改RethinkDB的连接地址

```bash
# Linux环境
# the bellow is default value
export RDB_HOST=localhost
export RDB_PORT=28015
export RDB_USER=admin
export RDB_PASSWD=
export RDB_DBNAME=atxserver2

python3 main.py
```

启动之后，浏览器打开 <http://localhost:4000>，完成认证之后就可以顺利的看到设备列表页了。不过目前还是空的，什么都没有。

![image](https://user-images.githubusercontent.com/3281689/53810253-7eb35300-3f91-11e9-815c-7cafa892a645.png)

**Step 3: Android设备接入**

接下来，进行安卓设备接入。这时需要用到另外一个项目 [atxserver2-android-provider](https://github.com/openatx/atxserver2-android-provider)
这个项目运行需要Python3.6+和NodeJS

```bash
git clone https://github.com/openatx/atxserver2-android-provider
cd atxserver2-android-provider

# 安装Python依赖
pip3 install -r requirements.txt

# 安装NodeJS依赖()
npm install

# 运行，参数填写atxserver2的地址
python3 main.py --server http://localhost:4000
```

这个时候网页上应该就能看到连接上的设备了。不过先别急

现在有一点还没能自动完成，不过以后会写进程序里面，目前需要连接上手机之后，还需要执行下下面的命令

```bash
pip install uiautomator2
# 确保设备通过数据线连接到手机
adb devices # 检查设备是否在线
python -m uiautomator2 init # 安装atx-agent, minicap 等其他必要文件
```

到这一步，你可以进行远程真机的操作了。

![image](https://user-images.githubusercontent.com/3281689/53810343-ae625b00-3f91-11e9-8ce1-37a256f1e0aa.png)

**Step 3: iOS设备接入**

TODO

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
