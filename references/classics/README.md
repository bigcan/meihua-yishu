原典 Classics

本目錄收錄六爻納甲體系的兩本核心原典，作為 najia-guide.md、liuyao-yongshen.md、case-studies-jinqian.md 的權威依據。
所有文本來自 ctext.org（公有領域、清代著作），格式為「原文 + 現代語譯 + 關鍵詞索引」。

現代橋樑書（《周易預測學》、《圖解易經》、傅佩榮《易經白話解》）：見 ../modern-references.md
（這些是仍有版權的現代教材，本工具僅註冊其概念框架與對應關係，不抄錄原文。）

收錄書目
書名|作者|年代|地位|本目錄狀態
增刪卜易|野鶴老人|清初（約 1690）|民間流傳最廣的六爻案例集|分卷收錄
卜筮正宗|王洪緒|清 1709|體系最嚴整的學院派標準|分章收錄

使用方式
1. 解卦時遇到疑難，從 classics-index.md 找對應原典章節
2. 原文段落保留古文，便於追溯
3. 每段附現代中文語譯，便於 LLM 與用戶理解
4. 關鍵詞索引（用神、世應、應期、旬空等）建立交叉引用

目錄結構
classics/
├── README.md（本文件）
├── zengshan-buyi/（增刪卜易）
│   ├── 00-preface.md（序）
│   ├── juan1-{section}.md（卷之一各章）
│   ├── juan2-{section}.md（卷之二各章）
│   ├── juan3-{section}.md（卷之三各章）
│   └── juan4-{section}.md（卷之四各章）
└── buzheng-zhengzong/（卜筮正宗）
    ├── 00-fanli.md（凡例）
    ├── 01-qimeng.md（啟蒙節要）
    ├── tables-{topic}.md（基礎表）
    ├── shi-ba-lun-{N}.md（十八論第 N 篇）
    └── case-studies-{N}.md（案例集）

優先收錄章節（v3.1 階段）
v3.1 首批收錄與 najia.py / liuyao-yongshen.md 直接對應的章節：
- 增刪卜易序 + 卷之一基礎章（八卦、卦象圖、六親、世應、用神、動變）
- 卜筮正宗凡例、啟蒙節要、用神分類定例第一、月破論第九、旬空論第十、反吟伏吟（十一、十二）、變出進退神論第十七

待補章節（v3.2+）
- 增刪卜易卷之二、卷之三、卷之四完整收錄
- 卜筮正宗其餘十八論章節、十八問答案例集、黃金策千金賦
- 完整案例集翻譯

下載指令參考
ctext.org 章節 URL 格式：https://ctext.org/wiki.pl?if=gb&chapter={ID}
完整 TOC 與 chapter ID 對照見 classics-toc.md
