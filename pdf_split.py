import asyncio
from pprint import pprint

import fitz
import hashlib
import os
from base64 import b64decode
from datetime import datetime
from typing import Optional, Iterator

import fitz
from bs4 import BeautifulSoup
from bs4.element import Tag
from langchain_core.documents import Document


class PdfHtmlProcessor:
    """
    PDF HTML处理类，用于处理PDF文件，提取文本、图片、元数据等，并将其转换为HTML文档形式。

    参数:
    - pdf_path: PDF文件的路径。
    - add_metadata: 可选，要添加到PDF文件元数据中的额外元数据字典。
    - pdf_images_dir: 存储从PDF中提取的图片的目录路径，默认为"./pdf_images"。

    属性:
    - file_metadata: PDF文件的元数据。
    - text_titles: 存储PDF中不同级别的标题的列表。
    - accumulated_text: 存储当前页面累计的文本内容。
    - image_paths: 存储提取的图片文件路径的列表。
    - table_text_list: 存储表格文本内容的列表。
    - pdf_images_dir: 存储图片的目录路径。
    """

    def __init__(self, pdf_path: str, add_metadata: Optional[dict] = None, pdf_images_dir: str = "./pdf_images"):
        self.pdf_path = pdf_path
        self.add_metadata = add_metadata
        self.file_metadata = None
        self.text_titles = [None] * 6
        self.accumulated_text = ""
        self.image_paths = []
        self.table_text_list = []
        self.pdf_images_dir = pdf_images_dir

    def _check_and_decode_base64_image(self, img_tag: Tag) -> Optional[str]:
        """
        检查HTML中的图片标签是否为Base64编码的图片，并将其解码保存到本地，返回图片的文件路径。

        参数:
        - img_tag: BeautifulSoup对象中的图片标签。

        返回:
        - 图片文件的路径，如果图片不是Base64编码则返回None。
        """
        if not img_tag or not img_tag["src"].startswith("data:image/"):
            return None

        data_url = img_tag["src"]
        data_url_prefix = "data:image/"
        data_url_suffix = ";base64,"
        data_url_start = data_url.find(data_url_prefix)
        data_url_end = data_url.find(data_url_suffix, data_url_start)

        if data_url_start == -1 or data_url_end == -1:
            return None

        img_data = data_url[data_url_end + len(data_url_suffix):]

        image_data = b64decode(img_data)

        if not os.path.exists(self.pdf_images_dir):
            os.makedirs(self.pdf_images_dir)

        hash_name = hashlib.md5(image_data).hexdigest()
        file_extension = data_url[data_url_start + len(data_url_prefix):data_url_end].split("/")[-1]
        image_path = os.path.join(self.pdf_images_dir, f"{hash_name}.{file_extension}")

        with open(image_path, "wb") as img_file:
            img_file.write(image_data)

        return image_path

    @staticmethod
    def _convert_pdf_date(pdf_date_str: str) -> str:
        """
        将PDF日期字符串转换为标准的日期字符串格式。

        参数:
        - pdf_date_str: PDF元数据中的日期字符串。

        返回:
        - 转换后的日期字符串。
        """
        year = int(pdf_date_str[2:6])
        month = int(pdf_date_str[6:8])
        day = int(pdf_date_str[8:10])
        hour = int(pdf_date_str[10:12])
        minute = int(pdf_date_str[12:14])
        second = int(pdf_date_str[14:16])
        dt = datetime(year, month, day, hour, minute, second)
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    def process_pdf(self, embed_titles: bool = False, exact_images: bool = False) -> Iterator[Document]:
        """
        处理PDF文件，提取文本、图片、表格等信息，并以Document对象的形式返回处理结果。

        参数:
        - embed_titles: 是否将标题嵌入到页面内容中，默认为False。

        返回:
        - 一个迭代器，每次返回一个Document对象，包含页面内容、元数据（包括标题和图片路径列表）。
        """
        pdf = fitz.open(self.pdf_path)
        # 更新PDF的创建和修改日期为标准时间格式
        for key in ["creationDate", "modDate"]:
            if key in pdf.metadata:
                pdf.metadata[key] = self._convert_pdf_date(pdf.metadata[key])

        self.file_metadata = pdf.metadata

        for page in pdf:
            table_text = ""

            # 提取表格内容
            for table in page.find_tables():
                table_name = "_".join(filter(lambda x: x is not None and "Col" not in x, table.header.names))
                pan = table.to_pandas()
                json_text = pan.dropna(axis=1).to_json(force_ascii=False)

                table_text += f"{table_name}\n{json_text}\n"

            self.table_text_list.append(table_text)

            html_content = page.get_text("xhtml")
            soup = BeautifulSoup(html_content, "html.parser")
            div = soup.div
            children = div.children

            # 遍历页面元素，处理标题和段落
            for child in children:
                if child.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    level = int(child.name[-1])
                    self.text_titles[level - 1] = child.get_text()
                    self.text_titles[level:] = [None] * (6 - level)

                    if self.accumulated_text:
                        page_content = self.accumulated_text
                        if embed_titles:
                            page_content = "\n".join(self.text_titles[:level]) + "\n\n" + page_content

                        metadata = {
                            "titles": self.text_titles[:level],
                            "images": self.image_paths,
                        }
                        pdf_document = Document(page_content=page_content, metadata=metadata)
                        pdf_document.metadata.update({"table": self.table_text_list.copy()})
                        pdf_document.metadata.update(self.file_metadata)

                        yield pdf_document

                        self.accumulated_text = ""
                        self.image_paths = []
                        self.table_text_list.clear()

                elif child.name == "p":
                    if exact_images:

                        # 处理图片
                        image_path = self._check_and_decode_base64_image(child.find("img"))

                        if image_path:
                            self.image_paths.append(image_path)
                        else:
                            self.accumulated_text += child.get_text()
                    else:
                        self.accumulated_text += child.get_text()

        # 处理最后一个页面
        if self.accumulated_text:
            page_content = self.accumulated_text
            if embed_titles:
                page_content = "\n".join(filter(None, self.text_titles)) + "\n\n" + page_content

            metadata = {
                "titles": self.text_titles,
                "images": self.image_paths,
            }
            pdf_document = Document(page_content=page_content, metadata=metadata)
            pdf_document.metadata.update({"table": self.table_text_list})
            pdf_document.metadata.update(self.file_metadata)

            yield pdf_document

            self.accumulated_text = ""
            self.image_paths = []
            self.table_text_list.clear()


class PDFSplitAgent:
    def __init__(self, pdf_path: str, chunk_size: int = 960, chunk_overlap: int = 100):
        self.pdf_path = pdf_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def split_agent_pdf(self, embed_titles: bool = False) -> Iterator[Document]:
        pdf_obj = PdfHtmlProcessor(self.pdf_path)
        for document in pdf_obj.process_pdf(embed_titles=embed_titles):
            yield document


async def main():
    pdf_path = "test.pdf"
    pdf_split_agent = PDFSplitAgent(pdf_path)
    doc = pdf_split_agent.split_agent_pdf(embed_titles=True)
    async for doc in doc:
        print(doc.page_content)
        print(doc.metadata)
        print("=====================================")


if __name__ == '__main__':
    asyncio.run(main())
