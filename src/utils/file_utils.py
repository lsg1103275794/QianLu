import os
import logging
from pathlib import Path
from typing import Tuple, Optional, Callable

def detect_file_type(filepath: Path) -> str:
    """
    自动检测文件类型，不仅依赖扩展名。
    返回文件类型: 'txt', 'pdf', 'md', 'docx', 'epub', 'unknown'
    """
    # 首先检查扩展名
    ext = filepath.suffix.lower()
    if ext in ['.txt', '.pdf', '.md', '.docx', '.epub']:
        # 进一步验证文件内容
        try:
            # 检查前几个字节来验证 PDF 文件
            if ext == '.pdf':
                with open(filepath, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        return 'pdf'
                    else:
                        return 'unknown'  # 非 PDF 格式
            
            # 检查 DOCX 文件 (ZIP 格式)
            elif ext == '.docx':
                import zipfile
                try:
                    with zipfile.ZipFile(filepath) as zip_ref:
                        if '[Content_Types].xml' in zip_ref.namelist():
                            return 'docx'
                        else:
                            return 'unknown'  # 非 DOCX 格式
                except zipfile.BadZipFile:
                    return 'unknown'  # 非 ZIP 格式
            
            # 检查 EPUB 文件 (也是 ZIP 格式)
            elif ext == '.epub':
                import zipfile
                try:
                    with zipfile.ZipFile(filepath) as zip_ref:
                        if 'META-INF/container.xml' in zip_ref.namelist():
                            return 'epub'
                        else:
                            return 'unknown'  # 非 EPUB 格式
                except zipfile.BadZipFile:
                    return 'unknown'  # 非 ZIP 格式
            
            # TXT 和 MD 文件，检查是否为文本文件
            elif ext in ['.txt', '.md']:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        f.read(64)  # 尝试读取前 64 字节
                    return ext[1:]  # 去掉前面的点
                except UnicodeDecodeError:
                    return 'unknown'  # 非文本文件
        
        except Exception as e:
            logging.warning(f"文件类型检测出错: {e}")
            return ext[1:]  # 出错时仍然返回基于扩展名的类型
        
    # 无法识别的扩展名，尝试检测内容
    try:
        # 尝试作为文本文件读取
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(1024)  # 读取前 1KB
                # 检查是否为 Markdown
                if content.startswith('# ') or '## ' in content or '```' in content:
                    return 'md'
                else:
                    return 'txt'  # 默认为纯文本
        except UnicodeDecodeError:
            pass  # 不是文本文件，继续检测
        
        # 检测 PDF
        with open(filepath, 'rb') as f:
            header = f.read(4)
            if header == b'%PDF':
                return 'pdf'
        
        # 检测 ZIP 格式 (可能是 DOCX 或 EPUB)
        import zipfile
        try:
            with zipfile.ZipFile(filepath) as zip_ref:
                if '[Content_Types].xml' in zip_ref.namelist():
                    return 'docx'
                elif 'META-INF/container.xml' in zip_ref.namelist():
                    return 'epub'
        except zipfile.BadZipFile:
            pass  # 不是 ZIP 文件
    
    except Exception as e:
        logging.warning(f"高级文件类型检测出错: {e}")
    
    return 'unknown'

def load_file_content(file_obj, app_logger: logging.Logger, progress_cb: Callable = None) -> str:
    """
    根据文件类型自动加载文件内容。
    
    参数:
        file_obj: Gradio 上传的文件路径
        app_logger: 日志记录器实例
        progress_cb: 进度回调函数，用于在UI更新进度
    
    返回:
        str: 文件内容文本
    """
    # 基本输入检查
    if not file_obj:
        app_logger.warning("未提供文件。")
        return ""
    
    try:
        filepath = Path(file_obj)
        if not filepath.exists():
            error_msg = f"文件不存在: {filepath}"
            app_logger.error(error_msg)
            return f"错误: {error_msg}"
        
        if filepath.is_dir():
            error_msg = f"提供的路径是目录，不是文件: {filepath}"
            app_logger.error(error_msg)
            return f"错误: {error_msg}"
        
        # 检查文件大小
        file_size = filepath.stat().st_size
        if file_size == 0:
            app_logger.warning(f"文件 {filepath.name} 大小为零。")
            return f"警告: 文件 {filepath.name} 为空文件。"
        
        # 检查文件大小限制（例如 PDF 太大可能会导致内存问题）
        max_size_mb = 50  # 50MB 限制
        if file_size > max_size_mb * 1024 * 1024:
            app_logger.warning(f"文件 {filepath.name} 超过 {max_size_mb}MB，处理可能很慢。")
            if progress_cb:
                progress_cb(0.1, f"文件较大 ({file_size/1024/1024:.1f}MB)，处理可能需要一些时间...")
        
        # 自动检测文件类型
        file_type = detect_file_type(filepath)
        app_logger.info(f"检测到文件类型: {file_type} (文件: {filepath.name})")
        
        # 根据文件类型调用相应的解析器
        content = ""
        error = None
        
        if progress_cb:
            progress_cb(0.2, f"开始解析 {file_type.upper()} 文件...")
        
        try:
            if file_type == 'txt':
                content, error = parse_txt_file(filepath, app_logger)
            elif file_type == 'pdf':
                content, error = parse_pdf_file(filepath, app_logger, progress_cb)
            elif file_type == 'md':
                content, error = parse_markdown_file(filepath, app_logger)
            elif file_type == 'docx':
                content, error = parse_docx_file(filepath, app_logger)
            elif file_type == 'epub':
                content, error = parse_epub_file(filepath, app_logger, progress_cb)
            else:
                error = f"不支持的文件类型: {file_type} (文件: {filepath.name})"
                # 尝试作为纯文本读取
                app_logger.warning(f"{error}。尝试作为纯文本读取。")
                try:
                    content, _ = parse_txt_file(filepath, app_logger)
                    if content:
                        error = f"警告: 文件 {filepath.name} 被作为纯文本处理，但实际格式可能不同。"
                    else:
                        error = f"错误: 无法读取文件 {filepath.name}，不支持的文件格式。"
                except Exception:
                    error = f"错误: 无法读取文件 {filepath.name}，不支持的文件格式。"
        except Exception as e:
            error_msg = f"解析文件时发生未预期的错误: {str(e)}"
            app_logger.error(error_msg, exc_info=True)
            error = error_msg
        
        if progress_cb:
            progress_cb(1.0, "文件解析完成")
        
        # 处理结果
        if error:
            if content:  # 有内容但有警告
                app_logger.warning(error)
                return f"{error}\n\n{content}"
            else:  # 没有内容，返回错误
                app_logger.error(error)
                return f"错误: {error}"
        
        if not content or not content.strip():
            app_logger.warning(f"从文件 {filepath.name} 中提取的内容为空。")
            return f"警告: 未能从文件 {filepath.name} 中提取到有效内容。"
        
        app_logger.info(f"成功从文件 {filepath.name} 中提取了 {len(content)} 字符。")
        return content
    
    except Exception as e:
        # 捕获任何未预期的异常
        error_msg = f"处理文件时出现意外错误: {str(e)}"
        app_logger.error(error_msg, exc_info=True)
        return f"错误: {error_msg}"

def parse_txt_file(filepath: Path, app_logger: logging.Logger) -> Tuple[str, Optional[str]]:
    """解析纯文本文件。返回 (content, error_message)"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        app_logger.info(f"从 TXT 文件 {filepath.name} 加载了 {len(content)} 字符。")
        return content, None
    except UnicodeDecodeError:
        # 尝试使用其他编码
        for encoding in ['gbk', 'latin1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                app_logger.info(f"从 TXT 文件 {filepath.name} 使用 {encoding} 编码加载了 {len(content)} 字符。")
                return content, None
            except UnicodeDecodeError:
                continue
        error_msg = f"无法读取文件 {filepath.name}：不支持的文本编码。"
        app_logger.error(error_msg)
        return "", error_msg
    except Exception as e:
        error_msg = f"读取文本文件 {filepath.name} 失败: {e}"
        app_logger.error(error_msg, exc_info=True)
        return "", error_msg

def parse_pdf_file(filepath: Path, app_logger: logging.Logger, progress_cb=None) -> Tuple[str, Optional[str]]:
    """解析 PDF 文件。返回 (content, error_message)"""
    try:
        # 导入 pypdf
        from pypdf import PdfReader
        
        reader = PdfReader(filepath)
        
        total_pages = len(reader.pages)
        text_parts = []
        
        for i, page in enumerate(reader.pages):
            # 更新进度
            if progress_cb and total_pages > 1:
                progress_cb((i+1)/total_pages, f"正在解析 PDF：第 {i+1}/{total_pages} 页...")
            
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        content = "\n".join(text_parts)
        if not content.strip():
            app_logger.warning(f"PDF 文件 {filepath.name} 没有提取到文本内容，可能是扫描件。")
            return "", f"警告：PDF 文件 {filepath.name} 没有提取到文本内容，可能是扫描件。"
        
        app_logger.info(f"从 PDF 文件 {filepath.name} ({total_pages} 页) 提取了 {len(content)} 字符。")
        return content, None
    except ImportError:
        return "", f"错误：缺少解析 PDF 所需的库 pypdf。请安装后再试。"
    except Exception as e:
        error_msg = f"解析 PDF 文件 {filepath.name} 失败: {e}"
        app_logger.error(error_msg, exc_info=True)
        return "", error_msg

def parse_markdown_file(filepath: Path, app_logger: logging.Logger) -> Tuple[str, Optional[str]]:
    """解析 Markdown 文件。返回 (content, error_message)"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            md_text = f.read()
        
        try:
            # 导入 markdown 和 BeautifulSoup
            import markdown
            from bs4 import BeautifulSoup
            
            html = markdown.markdown(md_text)
            soup = BeautifulSoup(html, 'html.parser')
            content = soup.get_text()
            app_logger.info(f"从 Markdown 文件 {filepath.name} 提取了 {len(content)} 字符。")
            return content, None
        except ImportError:
            # 检查哪些依赖库缺失
            missing_libs = []
            try:
                import markdown
            except ImportError:
                missing_libs.append("markdown")
                
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                missing_libs.append("beautifulsoup4")
            
            app_logger.warning(f"缺少 {', '.join(missing_libs)} 库，将直接使用原始 Markdown 文本。")
            return md_text, None
    except Exception as e:
        error_msg = f"解析 Markdown 文件 {filepath.name} 失败: {e}"
        app_logger.error(error_msg, exc_info=True)
        return "", error_msg

def parse_docx_file(filepath: Path, app_logger: logging.Logger) -> Tuple[str, Optional[str]]:
    """解析 Word 文档。返回 (content, error_message)"""
    try:
        # 导入 docx
        import docx
        
        doc = docx.Document(filepath)
        text_parts = [para.text for para in doc.paragraphs if para.text]
        content = "\n".join(text_parts)
        app_logger.info(f"从 Word 文件 {filepath.name} 提取了 {len(content)} 字符。")
        return content, None
    except ImportError:
        return "", f"错误：缺少解析 Word 文件所需的库 python-docx。请安装后再试。"
    except Exception as e:
        error_msg = f"解析 Word 文件 {filepath.name} 失败: {e}"
        app_logger.error(error_msg, exc_info=True)
        return "", error_msg

def parse_epub_file(filepath: Path, app_logger: logging.Logger, progress_cb=None) -> Tuple[str, Optional[str]]:
    """解析 EPUB 电子书。返回 (content, error_message)"""
    try:
        # 导入 ebooklib 和 BeautifulSoup
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
        
        book = epub.read_epub(filepath)
        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        total_items = len(items)
        text_parts = []
        
        for i, item in enumerate(items):
            # 更新进度
            if progress_cb and total_items > 1:
                progress_cb((i+1)/total_items, f"正在解析 EPUB：第 {i+1}/{total_items} 章节...")
            
            try:
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                text = soup.get_text(" ", strip=True)
                if text:
                    text_parts.append(text)
            except Exception as e:
                app_logger.warning(f"解析 EPUB 章节时出错: {e}")
        
        content = "\n\n".join(text_parts)
        app_logger.info(f"从 EPUB 文件 {filepath.name} ({total_items} 个章节) 提取了 {len(content)} 字符。")
        return content, None
    except ImportError:
        # 检查哪些依赖库缺失
        missing_libs = []
        try:
            import ebooklib
        except ImportError:
            missing_libs.append("ebooklib")
            
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            missing_libs.append("beautifulsoup4")
        
        return "", f"错误：缺少解析 EPUB 所需的库 {', '.join(missing_libs)}。请安装后再试。"
    except Exception as e:
        error_msg = f"解析 EPUB 文件 {filepath.name} 失败: {e}"
        app_logger.error(error_msg, exc_info=True)
        return "", error_msg 