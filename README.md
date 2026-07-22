# 岁月留痕：家庭数字记忆档案项目

本项目面向社区长者与儿童家庭共创活动，目标不是把课堂做成复杂的软件培训，而是把真实口述记忆整理成可保存、可聆听、可扫码访问的家庭数字档案。

一句话概括：

> 第一堂课把故事采集完整，第二堂课把故事变成可听、可看、可扫码保存的家庭数字记忆档案。

## 当前建议路线

第一版建议采用轻量化静态网页方案：

```text
课堂采集素材
  -> 团队整理家庭数据
  -> Python 批量生成网页
  -> 为每个家庭生成固定二维码
  -> GitHub Pages 或其他静态网站托管上线
```

不建议第一轮直接做完整微信小程序。原因是首轮服务对象数量较少，主要由团队统一录入，暂时不需要居民账号、后台审核、数据库和复杂权限系统。

## 最终交付

每组家庭最终收到《家庭数字记忆档案包》：

1. 一张正式老物件故事卡；
2. 一个长期有效的二维码数字展签；
3. 一个可持续更新的家庭数字记忆页面；
4. 一段 30-60 秒声音明信片；
5. 一段可选 AI 记忆影像；
6. 一份可保存或转发的电子文件。

## 文件说明

更详细的通俗操作说明见：

- `OPERATION_GUIDE.md`：项目结构、二维码、现场增删改家庭素材流程

项目方案内容放在 `project-plan/`：

- `01-project-overview.md`：项目总方案与成果链
- `02-two-lesson-design.md`：两节课课堂设计
- `03-content-and-data-spec.md`：家庭档案内容字段与数据规范
- `04-implementation-roadmap.md`：技术实施路线与阶段计划
- `05-research-and-evaluation.md`：研究数据与评价方案
- `06-field-checklists.md`：现场执行清单、采集表和授权要点

网站构建文件包括：

- `data/families.json`：家庭档案数据
- `templates/`：首页、家庭页、打印故事卡模板
- `static/`：网页样式与基础交互
- `media/`：图片、音频、视频素材
- `build.py`：批量生成网页和二维码
- `docs/`：自动生成的网站文件

## 本地运行

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

生成网站：

```powershell
python build.py
```

本地预览：

```powershell
python preview.py
```

终端会显示两个地址：

```text
电脑打开：http://127.0.0.1:8000
手机扫码/访问：http://你的电脑局域网IP:8000
```

手机扫码前，请确认手机和电脑连接同一个 Wi-Fi。如果 Windows 防火墙弹窗，请允许 Python 访问专用网络。

如果手机仍然打不开，可以手动指定电脑 Wi-Fi 的 IPv4 地址：

```powershell
python preview.py --host-ip 192.168.1.23
```

浏览器打开：

```text
http://127.0.0.1:8000
```

注意：预览服务运行时，终端会一直停在那里，这是正常现象。不要关闭终端，也不要按 `Ctrl+C`；打开浏览器访问终端里显示的地址即可。需要结束预览时，再回到终端按 `Ctrl+C`。

等 GitHub Pages 地址确定后，重新设置 `BASE_URL` 构建即可生成正式二维码：

```powershell
$env:BASE_URL="https://你的用户名.github.io/suiyue-memory"
python build.py
```
