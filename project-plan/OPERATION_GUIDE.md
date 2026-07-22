# 岁月留痕项目结构与现场操作指南

这份说明按“通俗操作”的方式写。你可以把整个项目理解成一台自动排版机器：

```text
data/families.json 写家庭故事资料
media/ 放照片、音频、视频
templates/ 和 static/ 决定网页长什么样
build.py 负责自动生成网页和二维码
docs/ 是最终生成出来的展馆网页
preview.py 负责本地预览和手机扫码测试
```

## 1. 为什么二维码一开始扫不开

之前二维码里写的是：

```text
http://127.0.0.1:8000/...
```

这个地址在电脑上能打开，但手机扫码时，`127.0.0.1` 会变成“手机自己”，不是你的电脑，所以手机打不开。

现在已经改成：

```text
python preview.py
```

启动时自动做三件事：

1. 找到一个可用端口；
2. 获取电脑在当前 Wi-Fi 下的局域网地址；
3. 重新生成所有二维码，让二维码指向类似这样的地址：

```text
http://192.168.1.23:8000/f/f001-shanghai-watch/
```

现场扫码前要确认：

1. 手机和电脑连接同一个 Wi-Fi；
2. 运行 `python preview.py` 的终端不要关闭；
3. 如果 Windows 防火墙弹窗，允许 Python 访问专用网络；
4. 只要终端关掉，二维码临时预览就会失效。

如果运行后终端显示的“手机扫码/访问”地址看起来不对，或者手机仍然打不开，可以手动指定电脑的 Wi-Fi 地址：

```powershell
python preview.py --host-ip 192.168.1.23
```

其中 `192.168.1.23` 要换成你电脑当前 Wi-Fi 的 IPv4 地址。Windows 中可以运行：

```powershell
ipconfig
```

在“无线局域网适配器 WLAN”下面找：

```text
IPv4 地址
```

常见可用地址一般长这样：

```text
192.168.x.x
10.x.x.x
172.16.x.x 到 172.31.x.x
```

正式上线到 GitHub Pages 后，二维码会换成线上网址，就不再依赖你的电脑和现场 Wi-Fi。

## 2. 每个文件夹是做什么的

### data/

这里放“家庭资料表”。

当前核心文件：

```text
data/families.json
```

它决定展馆里有哪些家庭、每个家庭标题是什么、故事是什么、图片路径是什么、二维码页面地址是什么。

修改后会发生什么：

1. 新增一条家庭记录，重新生成后展馆会多一个家庭页面；
2. 删除一条家庭记录，重新生成后展馆会少一个家庭页面；
3. 改故事正文，重新生成后网页和故事卡文字都会变化；
4. 改 `slug`，页面地址和二维码都会变化，不建议随便改。

### media/

这里放素材。

建议结构：

```text
media/
├─ assets/              公共图片，如封面、展馆示意图
└─ families/
   ├─ F001/
   │  ├─ photo.jpg      这个家庭的照片或物件图
   │  ├─ story.mp3      第二节课补充的声音，可选
   │  └─ video.mp4      AI影像，可选
   └─ F002/
      └─ photo.jpg
```

修改后会发生什么：

1. 替换 `photo.jpg`，重新生成后家庭页面和故事卡图片会变化；
2. 放入 `story.mp3` 并在数据里填写路径，页面会显示音频播放器；
3. 放入 `video.mp4` 并在数据里填写路径，页面会显示视频模块。

### templates/

这里放网页模板，相当于“版式骨架”。

当前文件：

```text
templates/index.html       展馆首页模板
templates/family.html      家庭数字档案页模板
templates/story-card.html  打印故事卡模板
```

修改后会发生什么：

1. 改 `index.html`，会影响展馆首页；
2. 改 `family.html`，会影响每个家庭扫码打开的页面；
3. 改 `story-card.html`，会影响可打印故事卡。

一般现场不需要改这里，后续统一优化界面时再改。

### static/

这里放样式和简单交互。

当前文件：

```text
static/style.css   网页颜色、字体、排版、手机适配
static/script.js   首页搜索和筛选
```

修改后会发生什么：

1. 改颜色、字号、间距，整个网站视觉会变化；
2. 改搜索逻辑，首页筛选功能会变化。

一般现场不需要改这里。

### docs/

这里是自动生成出来的最终网站。

重要提醒：

```text
不要手动修改 docs/
```

因为每次运行 `python build.py` 或 `python preview.py`，`docs/` 都会被重新生成。你手动改里面的东西，下次生成会被覆盖。

这里生成的内容包括：

```text
docs/index.html                 展馆首页
docs/f/<slug>/index.html        每个家庭的扫码页面
docs/cards/f001.html            每个家庭的打印故事卡
docs/qrcodes/F001.png           每个家庭二维码图片
docs/media/                     复制后的素材
```

### project-plan/

这里放项目方案文档、课程流程、研究评价和现场清单。

它不影响网页生成，是给你写方案、汇报和现场执行用的。

### .vendor/ 和 .venv/

这是 Python 依赖环境。

你可以暂时理解为“工具箱”。平时不用打开，也不要手动改。

### build.py

这是生成器。

运行：

```powershell
python build.py
```

它会读取 `data/` 和 `media/`，套用 `templates/` 和 `static/`，最后生成 `docs/`。

### preview.py

这是本地预览器。

运行：

```powershell
python preview.py
```

它会自动重新生成网页和二维码，并启动本地服务，方便电脑打开和手机扫码测试。

如果手机扫码打不开，优先检查：

1. 终端是否还开着；
2. 手机和电脑是否同一个 Wi-Fi；
3. 防火墙是否放行 Python；
4. 终端显示的手机访问地址是否是电脑的真实 Wi-Fi 地址；
5. 必要时使用 `python preview.py --host-ip 你的IPv4地址`。

### start-preview.bat

这是 Windows 双击启动版本。双击后也会运行预览。

如果窗口一闪而过，建议还是用 VS Code 终端运行：

```powershell
python preview.py
```

## 3. 现场拿到素材后如何快速导入

现场最推荐使用“四步法”。

### 第一步：确定家庭编号

例如新家庭是：

```text
F004
```

不要用真实姓名做文件夹名，也不要用真实姓名做网址。

### 第二步：放入照片

创建文件夹：

```text
media/families/F004/
```

把照片放进去，统一命名：

```text
photo.jpg
```

如果第二节课有音频，再放：

```text
story.mp3
```

如果有视频，再放：

```text
video.mp4
```

### 第三步：在 families.json 里新增一条记录

打开：

```text
data/families.json
```

复制已有的 F001 或 F002 那一整段，粘贴成新的一段，然后改成 F004 的内容。

最关键的字段：

```json
{
  "id": "F004",
  "slug": "f004-old-photo",
  "title": "一张老照片的记忆",
  "object_name": "家庭老照片",
  "year": "1970年代",
  "place": "上海",
  "narrator": "王阿姨",
  "co_creator": "安安",
  "story": "这里填写整理后的故事正文。",
  "quote": "这里填写最动人的一句长者原话。",
  "photo": "media/families/F004/photo.jpg",
  "audio": "",
  "video": "",
  "visibility": "community",
  "status": "数字档案 V1",
  "tags": ["老照片", "家庭记忆"],
  "ai_note": "故事文本由参与者口述，项目团队使用 AI 辅助整理，经本人确认。",
  "event_date": "2026-07-21"
}
```

注意：

1. `id` 不要重复；
2. `slug` 不要重复，只用小写英文、数字和短横线；
3. `photo` 必须和真实图片路径一致；
4. 第一节课没有音频时，`audio` 保持空字符串；
5. 第一节课没有视频时，`video` 保持空字符串。

### 第四步：重新生成并预览

运行：

```powershell
python preview.py
```

然后用电脑打开终端里显示的电脑地址，手机扫新生成的二维码。

## 4. 如何修改、删除家庭

### 修改故事

改：

```text
data/families.json
```

然后运行：

```powershell
python preview.py
```

### 替换照片

直接覆盖：

```text
media/families/F001/photo.jpg
```

然后运行：

```powershell
python preview.py
```

### 增加音频

把音频放到：

```text
media/families/F001/story.mp3
```

再把对应数据改成：

```json
"audio": "media/families/F001/story.mp3"
```

然后运行：

```powershell
python preview.py
```

### 删除家庭

从 `data/families.json` 里删除对应家庭那一整段记录，然后运行：

```powershell
python preview.py
```

如果确认不再需要素材，再删除：

```text
media/families/F001/
```

## 5. 第一节课到底让家庭看到什么

你的理解是对的：第一节课不一定要让家庭看完整“数字展馆首页”。

更适合的现场流程是：

1. 团队后台或电脑上有完整展馆首页，用于管理和展示；
2. 每组家庭拿到自己的故事卡；
3. 故事卡上有二维码；
4. 家庭扫码后只进入自己的家庭档案页；
5. 第一节课页面是 V1：照片、故事、金句、讲述人与共创人；
6. 第二节课再在同一个页面里补充声音和可选 AI 影像。

也就是说：

```text
展馆首页：团队管理和集中展示用
家庭档案页：家庭扫码看到的页面
故事卡页面：可打印输出，带二维码
```

## 6. 第一节课可以打印什么

可以打印：

```text
docs/cards/f001.html
docs/cards/f002.html
docs/cards/f003.html
```

打开后用浏览器打印即可。

第一节课建议打印“故事卡 V1”：

1. 照片或物件图；
2. 故事标题；
3. 年代、地点、物件；
4. 150-250 字故事正文；
5. 长者金句；
6. 讲述人和共创人；
7. 二维码。

第二节课后，如果补了声音，也可以重新打印“声音明信片版”。
