<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/record-index/main/docs/assets/logo-wide.png" alt="record-index — query the record instead of reading it" width="820">
</p>

# 记录索引

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/record-index/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

这是一个基于 SQLite+FTS5 的受控映射，用于处理 Markdown 格式的决策记录，因此会话可以**查询**该记录，而不是读取它——然后读取查询指向的那四十行，而不是原本需要浏览的六百行。

**[登录页面和手册 →](https://mcp-tool-shop-org.github.io/record-index/)**

The markdown stays canonical. The index is derived, regenerated on every fold, gated by a
four-leg `verify`, and **wrong by definition the day it is hand-edited**.

## 状态——已提取、已测试，尚未发布到 PyPI

*(本节内容在 2026-08-11 之前显示为“仅用于构建原型——该仓库中目前没有工具代码”，但提取过程证明了这一点。已进行更正。) *

**提取已完成。** 该软件包位于 `main`，并且在发布时受到字节身份验证的限制，与 facet 仓库中的构建版本（19/19）一致，并且在相同的语料库中**没有行级别的差异**。有两个消费者正在使用它：[facet](https://github.com/mcp-tool-shop-org/facet)，其大约 2462 行代码变成了一个声明和一个适配器，其中约有 140 个测试通过该适配器来测试该软件包；以及 [armature](https://github.com/mcp-tool-shop-org/armature)，其自身的索引包含 15/15 条规则，并基于 47 条判决。

**该软件包包含自己的测试套件：共 455 个检查项**，涵盖所有十个模块，在 CI 中运行于 Python 3.11 和 3.13 上，构建于两个不同的记录仓库之上，这两个仓库在每个可声明的轴上都存在差异——标记、语料库根目录、弧线规则、判决词汇表、标题格式——因此，错误的实现可以在某个地方被发现。**依赖项：无。** 仅使用标准库 (`sqlite3` + `re` + `json`)，并且这是一个声明的属性，而不是偶然的结果。

**已知有四个缺陷，已复现并作为 `xfail(strict=True)` 测试固定在仓库中**，而不是隐藏起来：`verify()` 将其诊断计数加倍（限制条件不受影响）；声明弧线模式假定 `E` 编号的弧线；子规则定位器不是从声明的标题格式派生的；并且四个声明字段不能被诚实地声明为空。这些缺陷都不会影响当前的两个消费者；所有这四个缺陷都已排队，将在下一个版本中解决。

**尚未发布到 PyPI。** `release.yml` 通过 OIDC 可信发布在创建 GitHub 发布时进行发布；不会在推送时进行发布。

## 这从何而来

这是对记录索引的提取，该索引是在 [`mcp-tool-shop-org/facet`](https://github.com/mcp-tool-shop-org/facet) 中构建和完善的，所有下面的约定都是在这里确定的。它进行提取而不是分叉，因为 facet 自身的规则手册中包含五个手动复制的函数，这些函数在四个不同的名称下存在，并且在基于名称的 grep 搜索中不可见；将数千行代码分叉到第二个仓库中，就是这个错误，而且还多了三个零。

提取条件已提前声明并受到测量的限制：*当第二个仓库采用这些约定时，索引将被提取。*
[`mcp-tool-shop-org/armature`](https://github.com/mcp-tool-shop-org/armature) 就是那个仓库。

## 设计（一段话）

一个记录仓库声明**其文档的含义**——哪些文件包含规则，哪个标题格式打开它，它的判决词汇表是什么，它有哪些语料库。该工具提供**搜索的工作方式**——解析、排序、确定性、验证步骤——以及用于调整的参数，这些参数携带了语料库和校准日期。约定是**完整的声明**（一个仓库声明自己的含义；它绝不会通过省略来继承另一个仓库的历史记录）。机制是**默认值加上覆盖**。

每个词汇表都会报告它**没有识别的内容**。一个空表格和一个默默丢弃了六个工件的表格在调用站点是无法区分的，而且只有一个是正确的。

## 曾经在这里存在的停止点以及它的结局

*(直到 2026-08-11，本节都会在检测到测量冲突时停止构建。停止点确实存在，判决已做出，并且构建继续进行——此处保留作为记录，而不是删除。) *

分类步骤已经测量出，从文档的开头 `E\d\d` 前缀派生弧线会**与 facet 的七个主键发生冲突**（`E10-ruling.md` 和 `E10-offsurface-ruling.md` 都变成弧线 `E10`）。执行器通过一个测试捕获了它，该测试的名称记录了相同的失败，联合判决被撤回并重新推导，并且提取过程通过其所有关卡。证据、推翻的答案以及取代它们的判决都包含在 `armature/docs/dispatches/` 中（S02 弧线）。

## 许可证

MIT——请参阅 [LICENSE](LICENSE)。
