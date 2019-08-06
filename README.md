## atxserver2
移动设备管理平台(支持Android和iOS), 欢迎加入QQ群交流

![image-20190619180012756](docs/qq.png)

![img](static/favicon-dark.png)

## 部署方案1 （docker-compose方式）
代码Clone到本地

接下来切换到代码目录，只需要再执行一条命令即可。

```bash
docker-compose up
```

## 部署方案2 （手动部署）
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

# 默认支持运行在Nginx下，支持 X-Real-Ip/X-Forwarded-For
# 如果不需要可以通过 --no-xheaders 关闭该功能
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

![image](https://user-images.githubusercontent.com/3281689/54806497-1a90ce80-4cb5-11e9-84c5-bbb4f427cbd5.png)

**Step 3: Android设备接入**

接下来，进行安卓设备接入。这时需要用到另外一个项目 [atxserver2-android-provider](https://github.com/openatx/atxserver2-android-provider)
这个项目运行需要Python3.6+和NodeJS

如果你用的是Linux系统，推荐使用Docker部署，其他平台需要用源码部署，具体请参考文档 [atxserver2-android-provider](https://github.com/openatx/atxserver2-android-provider)

```bash
SERVER_URL="http://10.0.0.1:4000" # 这个修改成自己的atxserver2地址
IMAGE="codeskyblue/atxserver2-android-provider"
docker pull $IMAGE
docker run --rm --privileged -v /dev/bus/usb:/dev/bus/usb --net host \
    ${IMAGE} python main.py --server ${SERVER_URL}
```

该镜像会把所有必要的资源 （atx-uiautomator.apk, minicap, minitouch, atx-agent) 全部推送到手机上。
一切就绪后，你可以进行远程真机的操作了。

![atxserver2-remotecontrol](https://user-images.githubusercontent.com/3281689/54807405-187c3f00-4cb8-11e9-8a8e-8092c5472dc1.gif)

**Step 3: iOS设备接入**

参考项目介绍 [atxserver2-ios-provider](https://github.com/openatx/atxserver2-ios-provider)

### 私有设备接入（Beta）
目前只实现了Android

`atxserver2-android-provider`启动的时候可以通过传递参数 `--owner=xingxing` 声明该provider所有连接的设备属于`xingxing`这个组所有，或者`--owner=panpan@gmail.com` 声明为panpan个人所有

通过点击导航栏的下拉菜单，点击`用户信息`,在这个标签页下可以获取个人的token，也可以进行组的管理。（目前还没有组成员管理的功能）

## 管理员功能
默认第一个登录的用户会成为管理员

管理员有哪些特权呢？

1. 可以释放他人正在使用的设备。（按住ALT，然后双击`正在使用`按钮）
2. 使用他人的身份占用设备（参考API文档）
3. 获取设备的source信息（参考API文档）
4. 将他人设置为管理员，导航栏可以看到`后台管理`链接
5. 有权修改`资产编号`字段

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

Examples:

- [Install app and run uiautomator2 test](examples/android_test.py)

## Thanks
- <https://github.com/openstf>
- <https://github.com/Genymobile/scrcpy>
- [https://www.easyicon.net](https://www.easyicon.net/iconsearch/hub/)
- <https://github.com/mikusjelly/apkutils>
- <https://github.com/gtsystem/python-remotezip>
- <https://github.com/willerce/WhatsInput>

## 微信打赏
以前我一直对打赏这种行为不屑一顾，但真正的收到社区成员千翻百计找到我的打赏码打赏的时候还是很开心，感觉工作得到的人认可，很开心。我也有时候会打赏别人，让激动的心情有了发泄的出口。
请不要打赏太多，知道了你们的心意就好了。我将会用收到的money通通拿来去楼下咖啡店买咖啡，买饮料。^_^

![wechat](docs/wechat_qrcode.jpg)

## LICENSE
[MIT](LICENSE)
