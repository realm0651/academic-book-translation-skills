本项目用于英文社会科学、历史学、政治学、哲学及相关学术著作的完整中文翻译，并生成最终Markdown、EPUB、PDF。项目有TRANSLATION_SKILL、EPUB_SKILL、PDF_SKILL三套SOP；处理时优先读取当前阶段对应SKILL.md并复用已有脚本/模板，除非我明确要求，不另造流程、不无必要改Skill。

# 一、总体工作流
原始PDF→判断PDF类型→TRANSLATION_SKILL→全书结构/Notes判断→book_plan.md→glossary.md→按book_plan逐Part翻译→滚动更新glossary和book_plan→全部Part/附录/Notes完成→最终Markdown整合→EPUB_SKILL→PDF_SKILL→EPUB+PDF→zlibrary_metadata.md。Translation Skill生成的最终master.md是EPUB/PDF唯一正文母稿，不维护两套正文。
`book_plan.md`是唯一workflow state，记录BOOK_STEM、PDF/Notes类型、全书结构、各Part物理页码范围、输出文件、状态、Next action、最新版glossary、book-specific decisions/profile、少量pending issues；`glossary.md`是唯一terminology state；原始PDF是原文权威来源；聊天历史仅辅助。文件命名以原始PDF去掉`.pdf`后的`<BOOK_STEM>`为前缀，仅做最小字符清理并保持不变；例如`<BOOK_STEM>_part1_中译.md`、`<BOOK_STEM>_master.md`；`book_plan.md`、`glossary.md`、`zlibrary_metadata.md`、`assets/`固定名。默认不为流程管理物理拆分Part PDF；逻辑Part和精确物理页码写入book_plan，翻译时直接从完整PDF读取。旧项目已有Part PDF可继续用。

# 二、新书初始化
我上传完整PDF并说“开始”“开始处理这本书”等时，读取TRANSLATION_SKILL/SKILL.md并初始化；若已有与本书对应、可用的book_plan.md，则不重复初始化，进入Resume Existing Book。
先判断PDF：
PDF-T：原生文字版，文字层可靠，走标准流程。
PDF-O：图片/扫描页+可用OCR层；只要正文覆盖、阅读顺序基本可靠、主要错误可借上下文/页面图像局部恢复，就可翻译，并在结构分析、glossary、逐Part翻译、QA全过程执行“文字提取+语义/OCR校正”；页面图像/可辨印刷原文优先于错误OCR。
PDF-I：只有图片、无可用文字层，或文字层严重缺失/乱码/错序，无法可靠恢复正文；停止并说明，不自行整本OCR。
初始化至少完成：判断PDF类型并抽查文字层；浏览全书；定位目录、序言/前言、Introduction、正文、附录、Notes、References、Bibliography、Index等；判断Notes类型；规划逻辑Parts并在book_plan记录每Part精确物理PDF页码、内容、输出文件、脚注前缀和状态；记录BOOK_STEM、PDF/Notes类型、翻译范围、profile/本书特殊决策、Current state、Next action；记录集中Notes/附录页码及后续阶段；建立初始glossary.md；检查文件与状态一致性。初始化后无需我重述下一步，回复简要记录“当前状态：初始化完成；已完成：全书结构分析/book_plan.md/glossary v1.0；下一步：翻译Part 1”，然后等“继续”。

# 三、“继续”的固定含义
无论同一对话还是新session，我只说“继续”，都表示按当前book_plan执行下一个未完成阶段。不要要求我重述Part、页码、文件名、脚注格式、glossary规则、profile或输出格式。执行前按顺序读取：当前Skill→book_plan.md→最新版glossary.md→book_plan记录的profile（如有）→原始PDF。book_plan是workflow权威，glossary是术语权威；聊天状态与文件冲突时优先当前文件，除非我明确纠正。没有book_plan才初始化；已有book_plan就Resume Existing Book，不因换session重新分析全书。若前一session已完成Part1–9，book_plan显示Next action=Part10，则新session一句“继续”直接做Part10。若Next action陈旧但状态表能唯一判断下一步，应自行修正；只有真实矛盾且无法判断时才询问具体矛盾。

# 四、文件连续使用与跨session恢复
当前环境能访问既有文件就继续用，不因换轮次/session要求重传。逐Part翻译的最小恢复集合原则上是：原始PDF+最新版book_plan.md+最新版glossary.md+适用profile（如有）+当前Skill。已完成Part Markdown和旧assets不是继续下一Part的常规前置条件。旧Part PDF不存在但原始PDF在时，直接按book_plan页码读取；不要为继续Part10要求上传Part1–9或其assets。只有当前正文明确回指前文且glossary/book_plan不足时，才按需读取相关已完成Part，不常规加载全部历史译文。
每完成一个Part，Part Markdown+更新后的book_plan.md+最新版glossary.md（如内容有变化）构成checkpoint。是否完成以book_plan中status=done为准，不能仅凭文件存在。恢复已有项目时应核对原始PDF与book_plan记录的Source PDF、总页数及可获得的版次/ISBN；若明显版本不一致，指出具体冲突，不默默沿用旧页码。必要文件确实不可读时，只说明缺哪个、为何需要、应从Library/本地附加哪个，不笼统要求“重新上传所有文件”。最终Markdown整合例外：必须一次性获得所有最终Part MD、附录/Notes MD和全部需要的assets。

# 五、逐Part翻译
每次进入Part：1.读取book_plan、最新版glossary、适用profile；2.按book_plan从完整PDF读取当前Part精确物理页码，旧Part PDF可靠时也可用；3.PDF-O把提取文字视为待校正转录，对人名、术语、引文、数字、脚注标记、标题、断词、乱码、可疑字符必要时回看页面图像；4.按Translation Skill完整翻译，不总结、不删减、不扩写；5.按Skill处理标题、脚注、表格、图片，必要图片存入assets/；6.出现新的重要术语、人名、机构、理论概念等时更新glossary，PDF-O词条基于校正后的原文；7.完成Part QA，PDF-O额外检查OCR错读造成的专名、数字、引文、脚注、断词误译；8.生成`<BOOK_STEM>_partN_中译.md`；9.QA成功后才把该Part标记done，并更新输出文件、glossary版本、必要的book-specific decisions/pending issues、Current state、Next action；10.保存最新版book_plan和glossary。
PDF-O只允许校正识别错误，如断词/合词、字符混淆、乱码、明显错认的专名/术语、版面造成的错序；不得借语义校正修改作者事实判断、论证、措辞、拼写习惯或数据。无法可靠恢复的文字不得猜测，标记待核对。默认不整本重做OCR，只有局部在文字层和页面图像均不足时才把局部OCR作为最后手段。
每轮原则上完成一个Part。完成后聊天只需简要说明：Part N已完成；输出；Glossary版本变化或未更新；Book plan已更新；下一步。不要粘贴整篇译文。

# 六、状态与Glossary
整本翻译持续维护同一个book_plan.md，不创建book_plan_v2.md、translation_state.md等第二状态源。至少维护各Part/附录/Notes的pending/in progress/done/blocked、实际输出文件、glossary版本、Next action、必要profile/特殊决策、少量待核对问题。聊天状态只需简洁，如“✓初始化 ✓Part1 ✓Part2 →Part3”，不要冗长阶段报告、Git模拟日志。
后续始终只使用最新版glossary.md；某Part无新增固定译名时不为版本号强行更新；更新后下一Part直接用最新版，不要求人工合并旧版。即使仅发生首次出现状态变化（如Status 0→1）而版本号不升级，也要保存同一个更新后的glossary.md，避免跨session重复英文括注。

# 七、全部Part完成与整合
全部正文Part、附录和需翻译Notes完成后，更新book_plan为Translation stage: complete、Next action: whole-book Markdown assembly。不要假定能可靠读取所有历史MD；告诉我下一阶段是全书Markdown整合，并一次性要求：所有最终Part MD、附录MD、Notes MD（如适用）、assets或assets ZIP（如有）。除非必须回查原文，不要求原始PDF。
整合时读取TRANSLATION_SKILL/SKILL.md，按最小变换原则：不重新翻译、不润色、不改正文内容、不重编号正确脚注、不改数字/表格/注释正文/稳定译名；按原书顺序合并Part，移动各Part Notes，最终生成`# 注释`并按`## 前言/第一章/.../附录`等分组，输出`<BOOK_STEM>_master.md`。整合前后检查脚注和结构；发现真实错误要指出，不凭猜测自动修复。完成后记录“Markdown整合完成；输出master.md；下一步：生成EPUB和PDF”。

# 八、EPUB/PDF与Z-Library
master完成后我再说“继续”，依次读取EPUB_SKILL/SKILL.md和PDF_SKILL/SKILL.md，用同一个master；只修改构建脚本顶部必要书籍参数，优先复用现有CSS/Lua/TeX模板，不无意义重写；实际生成EPUB、PDF并QA；模板能工作时不要改正文MD迁就排版。最终交付master、EPUB、PDF、必要glossary/assets。生成`zlibrary_metadata.md`后再创建`<BOOK_STEM>_final.zip`，包含master、EPUB、PDF、glossary、zlibrary_metadata.md、assets（如有），不放构建临时文件、Part工作文件或book_plan，除非我另有要求。
`zlibrary_metadata.md`格式仅含：中文书名、English Title、作者、ISBN、出版年份、简介。中文书名用最终完整书名；英文保留完整title/subtitle；作者优先原文姓名，有稳定中译可并列；ISBN优先当前PDF版本ISBN-13，无法确认则“待核对”；年份取当前PDF对应版本；简介简短客观，概括主题、核心问题、分析路径，不宣传、不虚构；优先依据扉页/版权页，缺失或冲突且可联网时用可靠书目源核对；不额外生成标签/分类/出版社/语言；此步骤不修改master、EPUB、PDF、glossary、assets。

# 九、交互目标与备份
目标是尽量减少人工操作：我用“开始”初始化，用“继续”执行下一阶段，跨session也相同。比如18个Part，Session A完成到Part9后，只要最新版book_plan、glossary以及原始PDF/profile可访问，Session B一句“继续”就从Part10开始，不要求重述规则或上传Part1–9。普通约10 Part著作仍以约15轮内完成为目标，但不得牺牲完整性或强塞过大Part。
我可随时下载最新版book_plan、glossary、已完成Part、阶段ZIP备份；下载行为不改变当前状态。准备换session时，book_plan和glossary是最重要checkpoint；无需为继续下一Part重新附加全部历史Part/assets，最终整合时再一次性提供最终MD/assets。

# 十、PDF类型规则边界与优先级
PDF-T/PDF-O/PDF-I只改变“如何可靠读取原文”，不改变Notes/脚注规则、逻辑Part划分与book_plan页码定位、标题/表格/图片/Markdown规则、glossary滚动更新、最终整合、EPUB/PDF、Z-Library metadata等既有规则。
冲突优先级：1.我当前消息的明确要求；2.项目自定义指令；3.当前Skill的SKILL.md；4.Skill脚本/模板；5.一般学术翻译出版惯例。Skill已明确的问题不要重复问；能依据现有PDF、book_plan、glossary、文件结构和Skill判断就直接执行。核心目标：减少重复操作，同时保持长篇学术翻译的完整性、术语一致性、脚注可靠性和出版结构稳定性。