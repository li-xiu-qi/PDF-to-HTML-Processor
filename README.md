# PDF-to-HTML-Processor
## 项目简介
PDF-to-HTML-Processor是一个处理pdf文件的项目，用于将PDF文件转换为HTML格式，并提取文本、图片、元数据等信息。它使用fitz和BeautifulSoup库来实现PDF的读取和HTML的生成。最终以生成器的方式输出一个个和langchain中Document类相同的对象。
## 功能特性
- 提取PDF中的文本、图片和元数据
- 将PDF转换为HTML格式
- 保存提取的图片到本地
- 支持嵌入标题到页面内容中
- 提取表格内容并保存为JSON格式
## 安装
1. 安装Python（建议使用Python 3.8及以上版本）
2. 安装依赖库：`pip install fitz beautifulsoup4 pandas`
## 使用方法
1. 创建PdfHtmlProcessor对象，传入PDF文件路径和其他可选参数
2. 调用process_pdf()方法，传入embed_titles参数（可选，默认为False）
3. 遍历返回的Document对象，获取页面内容、元数据和图片路径列表
## 示例
```python
from pdf_html_processor import PdfHtmlProcessor
pdf_path = "/path/to/your/pdf/file.pdf"
processor = PdfHtmlProcessor(pdf_path)
for doc in processor.process_pdf(embed_titles=True):
    print(doc.page_content)
    print(len(doc.page_content))
    print(doc.metadata)
```
## 注意事项
- 确保已安装所有依赖库
- 如果要保存提取的图片，请确保指定一个有效的图片存储目录
- 本项目仅支持提取PDF中的文本、图片和表格，不支持其他复杂元素（如注释、书签等）
## 联系方式
如果有任何问题或建议，请通过邮箱（xiaoke-work@qq.com）联系我。

