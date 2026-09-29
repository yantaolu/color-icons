# color-icons

整理用于 Stash 的 Qure Color 与 Mini Color 图标集，并提供可重复运行的生成脚本。

## 图标集

| 图标集 | 文件 | 收录范围 |
| --- | --- | --- |
| Qure Color | [QureColor.json](QureColor.json) | 来源页面中的全部 Qure Color 清单，包含 Archived |
| Mini Color | [MiniColor.json](MiniColor.json) | mini+、mini icons、mini Color |

JSON 使用 Stash 图标集格式，包含 `name`、`description` 和 `icons`。每个图标保留原始名称与在线图片地址。

## 使用

在 Stash 的图标集导入功能中使用下列地址：

- Qure Color：`https://raw.githubusercontent.com/yantaolu/color-icons/master/QureColor.json`
- Mini Color：`https://raw.githubusercontent.com/yantaolu/color-icons/master/MiniColor.json`

图片仍从上游项目加载，本仓库不托管图片文件。

## 重新生成

需要 Python 3.9 或更新版本、curl，以及可访问来源站点和 GitHub 图片地址的网络。无需安装第三方 Python 包。

在仓库根目录运行：

```bash
python3 scripts/build_icon_sets.py
```

默认更新仓库根目录的两份 JSON。也可以指定输出目录和并发数：

```bash
python3 scripts/build_icon_sets.py --output-dir ./output --workers 8
```

通过 `--page-url` 可指定其他采用同样 Stash 安装链接结构的来源页面。

## 生成规则

1. 获取 [Stash 图标集页面](https://clashios.app/blog/icon-set)，按页面顺序解析图标集链接。
2. 下载清单，分别选取 Qure Color 与指定的三个 Mini 图标集。
3. 保持各清单内部顺序，以图标 URL 在每组内去重；首次出现的记录保留，后续清单仅向数组末尾追加新 URL，不按名称排序。同名但不同 URL 的图标保留。
4. 下载并检查全部图标链接是否返回 PNG；并发下载不改变输出顺序。
5. 所有下载和验证通过后，生成两份 JSON。下载失败、清单异常或图片验证失败时退出报错，不覆盖已有输出。

每次运行都以当前来源页面和清单重新生成，数量会随上游变化。脚本不会自动提交或推送文件。

## 来源与致谢

- 图标集索引：[clashios.app/blog/icon-set](https://clashios.app/blog/icon-set)
- Qure Color：[Koolson/Qure](https://github.com/Koolson/Qure)
- Mini Color：[Orz-3/mini](https://github.com/Orz-3/mini)

图标及相关权利归原作者所有，使用时请遵守各上游项目的许可和使用说明。
