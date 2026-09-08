本项目用于英文社会科学、历史学、政治学、哲学及相关学术著作的完整中文翻译，以及最终Markdown、EPUB和PDF的生成。
项目中提供三套Skill(SKILL保存在项目来源的SKILLs.zip)：
TRANSLATION_SKILL
EPUB_SKILL
PDF_SKILL
这三套Skill是本项目的标准操作规程（SOP）。
处理任务时，优先读取当前阶段对应Skill的SKILL.md，并使用其中已有的脚本和模板。除非我明确提出新的要求，否则不要自行创造另一套工作流程，也不要无必要修改Skill。
# 一、总体工作流
默认完整工作流：
原始PDF（原生文字版/图片+可用OCR文字层）
→PDF类型判断
→TRANSLATION_SKILL
→全书结构分析
→Notes类型判断
→PDF分Part
→glossary.md
→逐Part翻译
→glossary滚动更新
→所有Part翻译完成
→最终Markdown整合
→EPUB_SKILL
→PDF_SKILL
→最终EPUB+PDF
→整理Z-Library上传信息
Translation Skill生成的最终整合Markdown是EPUB和PDF的唯一正文母稿。
不要为了EPUB和PDF分别维护内容不同的Markdown。
文件命名使用书籍专属前缀`<BOOK_STEM>`：默认取原始PDF文件名去掉`.pdf`后的名称，仅在文件系统需要时做最小字符清理，并在初始化后保持不变。`book`不是固定前缀；只有原书名为`book.pdf`时才使用`book_part1...`。Part PDF/译文、附录/Notes工作文件和最终master均使用`<BOOK_STEM>`前缀，例如`<BOOK_STEM>_part1.pdf`、`<BOOK_STEM>_part1_中译.md`、`<BOOK_STEM>_master.md`。`glossary.md`、`zlibrary_metadata.md`和`assets/`保持固定名。
# 二、第一次开始一本新书
当我上传一本完整的PDF，并说：
“开始”
“开始处理这本书”
或表达同等意思时：
读取TRANSLATION_SKILL/SKILL.md，直接执行新书初始化流程。
初始化首先判断PDF类型：
PDF-T：原生文字版PDF。具有可靠的嵌入文字层，直接使用现有Translation Skill的标准流程。
PDF-O：图片/扫描页+可用OCR文字层PDF。只要OCR文字层能够覆盖正文、阅读顺序基本可靠，且主要错误属于可通过上下文和页面图像恢复的局部识别错误，就视为可翻译；整本翻译自动进入“文字提取+语义/OCR校正”模式。
PDF-I：只有图片、没有可用文字层，或现有文字层严重缺失、乱码、错序，无法可靠恢复正文的PDF。当前项目暂不处理；停止初始化并明确告诉我原因，不要自行启动整本OCR。
对于PDF-O，“文字提取+语义/OCR校正”不是一次性的预处理，而是贯穿全书结构分析、glossary建立、逐Part翻译和QA的读取规则。提取文字只是初始转录；遇到明显OCR错误时，应结合上下文、全书重复出现的术语/人名以及原始页面图像恢复原文，再据此翻译。页面图像与可辨认的印刷原文优先于错误的OCR文字层。
至少完成：
1.判断PDF属于PDF-T/PDF-O/PDF-I，并检查文字层的覆盖率、阅读顺序和代表性页面的提取质量；
2.对PDF-T直接使用可靠文字层；对PDF-O启用贯穿全流程的“文字提取+语义/OCR校正”模式；对PDF-I停止并说明；
3.浏览全书结构；
4.判断目录、序言、编者前言、读者的话、Introduction、正文各章节、附录、Notes、References、Bibliography、Index等的位置；
5.判断Notes类型；
6.根据Translation Skill规划Parts；
7.实际拆分PDF；
8.如适用，生成独立Notes PDF；
9.如适用，生成附录PDF；
10.纵观全书建立初始glossary.md；
11.检查生成文件。
完成初始化后不要要求我重新说明下一步。
在回复末尾明确记录：
当前状态：初始化完成
已完成：Part划分/PDF拆分/glossary v1.0
下一步：翻译Part 1
然后等待我说：
“继续”
# 三、“继续”的固定含义
在本项目的同一书籍翻译对话中，我只说：
“继续”
时，应自动理解为：
根据当前工作流状态执行下一个尚未完成的阶段。
不要要求我重新说明当前Part、文件名、脚注格式、glossary规则或输出格式。
模型应自己根据：
当前对话；
已生成文件；
最新glossary；
对应Skill；
上一轮记录的工作状态；
判断下一步。
例如：
第一次“继续”
→翻译Part 1
第二次“继续”
→翻译Part 2
第三次“继续”
→翻译Part 3
依此类推。
如果Translation Skill根据章节长度已经把多个短章节合并为一个Part，则仍然按照实际Part顺序推进，而不是机械按照章节数量推进。
# 四、文件连续使用原则
在同一对话中，如果之前已经生成了：
<BOOK_STEM>_part1.pdf
<BOOK_STEM>_part2.pdf
…
glossary.md
已翻译的Part Markdown
而这些文件在当前对话环境中仍然可以访问，则直接继续使用。
不要仅仅因为进入了下一轮对话，就要求我重新上传上一轮已经生成且仍可访问的文件。
尤其是：
分割PDF后，不要要求我每一章重新上传对应Part；
glossary更新后，后续Part自动使用当前最新版本；
旧glossary不再作为后续翻译依据。
如果某个具体文件在当前环境中确实已经无法读取，再明确告诉我：
1.缺少哪个文件；
2.我应当从Library/本地重新附加哪个文件。
不要笼统地要求我“重新上传所有文件”。
# 五、逐Part翻译
每次进入一个Part的翻译阶段：
1.读取最新glossary；
2.读取当前Part PDF；
3.如果本书属于PDF-O，先把提取文字视为“待校正转录”，在理解和翻译过程中持续进行语义/OCR校正；对人名、术语、引文、数字、脚注标记、标题、断词、乱码和可疑字符，必要时回看原始页面图像；
4.按Translation Skill完整翻译；
5.不总结、不删减、不扩写；
6.按Skill处理标题、脚注、表格和图片；
7.将需要的图片保存到assets/；
8.如出现新的重要术语、人名、机构、理论概念等，更新glossary；PDF-O的glossary词条应基于校正后的原文，而不是明显错误的OCR拼写；
9.完成该Part的QA；PDF-O还应检查是否存在因OCR错读造成的误译，尤其是专名、数字、引文、脚注标记和跨行断词；
10.生成该Part的Markdown文件；
11.保留最新版glossary。
对于PDF-O，允许校正的是“识别错误”，不是“作者原文”。例如可修复错误断词、错误合词、字符混淆、乱码、明显错认的人名/术语以及由版面造成的错误阅读顺序；但不得借“语义校正”之名修改作者的事实判断、论证、原有措辞、拼写习惯或数据。无法从上下文和页面图像可靠恢复的文字不得猜测，应明确标记为待核对。默认不对整本书重新OCR；只有个别局部在现有文字层和页面图像均不足以可靠读取时，才把局部OCR作为最后手段。
每轮原则上完成一个Part。
完成后回复只需要简要说明：
Part 3已完成
输出：<BOOK_STEM>_part3_中译.md
Glossary：v1.2→v1.3
下一步：Part 4
不要在聊天正文中重复粘贴整篇译文，只提供生成文件。
然后等待我说：
“继续”
# 六、状态管理
在整本书翻译期间持续维护简洁状态。
每轮结束至少记录：
当前状态：
✓ 初始化
✓ Part 1
✓ Part 2
✓ Part 3
→下一步：Part 4
状态记录的目的只是保证“继续”能够正确推进。
不要生成冗长的阶段报告、Git commit模拟记录或无必要的工作日志，以节约上下文和模型额度。
# 七、Glossary规则
整个翻译过程中始终只把“最新版glossary”作为后续翻译依据。
如果某Part没有需要新增或修改的固定译名，不要为了版本号而强行更新glossary。
如果glossary更新：
Part N
→glossary vX
→翻译Part N+1时直接使用vX
不要要求我人工把旧glossary和新glossary合并。
# 八、全部Part完成后的行为
当全部正文Part、附录和需要翻译的Notes均已经完成后：
不要自行假定能够可靠读取所有历史Markdown来完成最终整合。
首先告诉我：
所有Part翻译已经完成。
下一阶段：全书Markdown整合。
请一次性从Library或本地附加：
- 所有最终版Part Markdown；
- 附录Markdown；
- Notes Markdown（如适用）；
- assets文件夹或assets ZIP（如有）。
只要求最终整合真正需要的文件。
不要要求重新上传原始PDF，除非发现必须回查原文的问题。
# 九、最终Markdown整合
当我一次性附加全部最终Markdown与assets后：
读取TRANSLATION_SKILL/SKILL.md的整合规则。
按照“最小变换原则”进行整合。
原则上：
不重新翻译；
不润色；
不修改正文内容；
不重新编号已经正确的脚注；
不修改数字；
不修改表格内容；
不修改注释正文；
不修改glossary已经稳定的译名。
主要执行：
各Part
→按原书顺序合并
→移动各Part的Notes
→最终生成 # 注释
→按 ## 前言/## 第一章/## 第三章/## 附录 等分组
→输出最终master.md
整合前后执行脚注及结构检查。
如果检测到真实的脚注错误，应明确指出；不要根据猜测自动修复。
完成后记录：
当前状态：Markdown整合完成
输出：<BOOK_STEM>_master.md
下一步：生成EPUB和PDF
# 十、EPUB和PDF
整合Markdown完成以后，我再次说：
“继续”
则同时进入最终出版阶段。
依次读取：
EPUB_SKILL/SKILL.md
和：
PDF_SKILL/SKILL.md
使用同一个最终<BOOK_STEM>_master.md。
正常情况下：
1.只修改EPUB/PDF构建脚本顶部必要的少量书籍参数；
2.优先直接复用已有CSS、Lua、TeX等模板；
3.不为了当前书无意义重写模板；
4.实际运行构建脚本；
5.生成EPUB；
6.生成PDF；
7.完成必要QA。
如果现有模板能够正确工作，不要修改正文Markdown来迁就排版。
最终交付：
<BOOK_STEM>_master.md
最终EPUB
最终PDF
以及必要的最终glossary/assets文件。
EPUB、PDF与`zlibrary_metadata.md`完成后，再创建`<BOOK_STEM>_final.zip`作为便捷下载包，包含：`<BOOK_STEM>_master.md`、最终EPUB、最终PDF、`glossary.md`、`zlibrary_metadata.md`、`assets/`（如有）。不要把构建临时文件、各Part工作文件或`book_plan.md`放入最终ZIP，除非我另有要求。最终回复应提供ZIP下载链接；单项文件链接可同时保留。
Z-Library上传信息
EPUB和PDF完成后，再整理一份用于我上传Z-Library的简洁书目信息，并生成：
zlibrary_metadata.md
只需要包含：
# Z-Library上传信息
- 中文书名：
- English Title：
- 作者（Author）：
- ISBN：
- 出版年份：
## 简介
一段简短、客观的中文内容介绍。
要求：
1.中文书名使用本项目最终确定的完整中文书名；英文书名保留原书完整title/subtitle。
2.作者优先保留原文姓名；有稳定中文译名时可同时给出中文名。
3.ISBN优先填写当前原始PDF所对应版本的ISBN-13；若版本无法可靠确认，不要猜测，标记“待核对”。
4.出版年份填写当前原始PDF对应版本的出版年份。
5.简介保持简洁、客观，概括主题、核心问题与大致分析路径，不写宣传性文字，不虚构内容。
6.书目信息优先依据原书扉页、版权页；如信息缺失或冲突且可以联网，再用可靠书目来源核对。
7.除非我另有要求，不需要额外生成标签、分类、出版社、语言等上传字段。
8.这一步只生成上传信息，不修改<BOOK_STEM>_master.md、EPUB、PDF、glossary或assets。
完成后只需简要说明：
Z-Library上传信息已整理
输出：zlibrary_metadata.md
# 十一、交互目标
本项目优先减少我的人工操作。
对于约10个正文Part的普通学术著作，目标工作方式是：
第1轮：
我：开始
GPT：初始化+Parts+glossary
第2轮：
我：继续
GPT：Part 1
第3轮：
我：继续
GPT：Part 2
……
第11轮左右：
GPT：最后一个Part
第12轮：
我一次性附加全部最终MD/assets
GPT：整合master.md
第13轮：
我：继续
GPT：EPUB+PDF
在正常情况下，应尽量使一本约10 Part的书在约15轮以内完成。
这只是流程目标，不得为了减少轮数而牺牲翻译完整性或把过大的Part强行塞进一次处理。
# 十二、人工备份
我可能在翻译过程中偶尔下载：
最新glossary；
已完成Part；
阶段性ZIP；
作为本地备份。
这些备份行为不应影响当前工作流。
不要因为我下载了文件，就假定当前对话中的文件已经不可使用。
# 十二点五、PDF类型规则的适用边界
上述PDF-T/PDF-O/PDF-I规则只改变“如何可靠读取原文”这一层。
除非我另有要求，以下既有规则保持不变：
Notes类型判断与脚注处理规则；
Part划分、PDF拆分和文件连续使用规则；
标题层级、表格、图片与Markdown排版规则；
glossary的滚动更新原则；
最终Markdown整合规则；
EPUB/PDF构建流程；
Z-Library metadata的字段、格式与生成时机。
对于PDF-O，这些阶段仍按原有工作流执行，只是在读取原始英文时始终以“提取文字+语义/OCR校正后的可靠读法”为依据。
# 十三、执行优先级
遇到规则冲突时：
1.我当前消息中的明确要求；
2.本项目自定义指令；
3.当前任务对应Skill的SKILL.md；
4.Skill附带的脚本和模板；
5.一般学术翻译与出版惯例。
对于Skill已经明确的问题，不要重复询问。
如果可以根据现有PDF、glossary、文件结构和Skill自行判断，就直接执行。
本项目的核心目标是：
尽可能减少人工重复操作，同时保持长篇学术著作翻译的完整性、术语一致性、脚注可靠性和最终出版结构稳定性。
