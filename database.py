import sqlite3
import threading
from contextlib import contextmanager
from config import DATABASE_PATH, SIMILARITY_THRESHOLD

class QuestionDatabase:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器，实现连接复用"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path)
            # 启用WAL模式提高并发性能
            self._local.connection.execute('PRAGMA journal_mode=WAL')
            # 优化SQLite性能设置
            self._local.connection.execute('PRAGMA synchronous=NORMAL')
            self._local.connection.execute('PRAGMA cache_size=10000')
            self._local.connection.execute('PRAGMA temp_store=memory')
        
        try:
            yield self._local.connection
        except Exception:
            # 发生异常时回滚事务
            self._local.connection.rollback()
            raise
    
    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建题目表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                answer TEXT NOT NULL,
                type TEXT NOT NULL,
                keywords TEXT
            )
            ''')
            
            # 创建索引
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content ON questions(content)
            ''')
            
            conn.commit()
    
    def add_question(self, content, answer, type, keywords=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO questions (content, answer, type, keywords)
            VALUES (?, ?, ?, ?)
            ''', (content, answer, type, keywords))
            
            conn.commit()
    
    def extract_features(self, clean_text):
        """提取文本的多维度特征（分词、字符集、2-gram）以增强中文模糊匹配"""
        chars = set(clean_text.replace(' ', ''))
        tokens = set(clean_text.split())
        compact = clean_text.replace(' ', '')
        # 提取二元字符组 (2-gram)，解决中文没有空格导致分词交集为空的问题
        if len(compact) >= 2:
            for i in range(len(compact) - 1):
                tokens.add(compact[i:i+2])
        return chars, tokens

    def find_answer(self, question_text):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 先尝试精确匹配
            cursor.execute('''
            SELECT answer FROM questions
            WHERE content = ?
            ''', (question_text,))
            
            result = cursor.fetchone()
            
            if result:
                return result[0]
            
            # 预处理查询文本
            cleaned_query = self.clean_text(question_text)
            if not cleaned_query:
                return None
                
            query_chars, query_tokens = self.extract_features(cleaned_query)
            
            # 如果没有精确匹配，使用优化的模糊匹配
            cursor.execute('''
            SELECT answer, content FROM questions
            ''')
            
            best_match = None
            highest_similarity = 0
            min_threshold = SIMILARITY_THRESHOLD  # 使用配置的相似度阈值
            
            # 批量处理，减少函数调用开销
            for answer, content in cursor.fetchall():
                cleaned_content = self.clean_text(content)
                if not cleaned_content:
                    continue
                
                # 检查包含关系（如题干子串包含），给予很高的基础匹配度
                if len(cleaned_query) >= 4 and len(cleaned_content) >= 4:
                    if cleaned_query in cleaned_content or cleaned_content in cleaned_query:
                        match_ratio = min(len(cleaned_query), len(cleaned_content)) / max(len(cleaned_query), len(cleaned_content))
                        similarity = max(0.8, 0.7 + match_ratio * 0.3)
                        if similarity > highest_similarity:
                            highest_similarity = similarity
                            best_match = answer
                            if similarity > 0.9:
                                break
                        continue

                content_chars, content_tokens = self.extract_features(cleaned_content)
                
                # 快速预筛选：检查二元组或字符集合是否有交集
                char_inter = query_chars.intersection(content_chars)
                if not char_inter:
                    continue
                
                # 字符重合过低直接跳过（低于较短文本字符数的 30%）
                min_len = min(len(query_chars), len(content_chars))
                if min_len > 0 and (len(char_inter) / min_len) < 0.3:
                    continue
                
                similarity = self.calculate_similarity_fast(
                    cleaned_query, cleaned_content,
                    query_tokens, content_tokens,
                    query_chars, content_chars
                )
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = answer
                    
                    # 如果相似度很高，提前返回
                    if similarity > 0.9:
                        break
            
            # 只要找到相似度大于最低阈值的答案就返回
            if highest_similarity > min_threshold:
                return best_match
            
            return None
    
    def clean_text(self, text):
        """改进的文本清理方法，提高匹配准确性"""
        import re
        if not text:
            return ""
        
        # 移除题号、分数等格式（如 "1.(25分)" 或 "1. （25分）" 或 "一、"）
        text = re.sub(r'^\s*[\d一二三四五六七八九十]+[\.、\s]*\(\s*\d+\s*分\s*\)\s*', '', text)
        text = re.sub(r'^\s*[\d一二三四五六七八九十]+[\.、\s]+', '', text)
        
        # 统一标点符号：将中文标点替换为英文标点
        text = text.replace('，', ',')
        text = text.replace('。', '.')
        text = text.replace('；', ';')
        text = text.replace('：', ':')
        text = text.replace('？', '?')
        text = text.replace('！', '!')
        text = text.replace('《', '')
        text = text.replace('》', '')
        text = text.replace('「', '')
        text = text.replace('」', '')
        text = text.replace('（', '(')
        text = text.replace('）', ')')
        
        # 移除所有标点符号和特殊字符，替换为空格以避免词汇粘连
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
        
        # 统一处理空格：多个空格合并为一个，去除首尾空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text.lower()
    
    def calculate_similarity_fast(self, clean_text1, clean_text2, tokens1, tokens2, chars1=None, chars2=None):
        """优化的快速相似度计算，结合 N-Gram 与字符集合"""
        # 子串直接包含
        if clean_text1 in clean_text2 or clean_text2 in clean_text1:
            ratio = min(len(clean_text1), len(clean_text2)) / max(len(clean_text1), len(clean_text2))
            return 0.75 + ratio * 0.25
        
        # 词汇与 2-gram 的 Jaccard 相似度
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
        
        token_intersection = tokens1.intersection(tokens2)
        token_union = tokens1.union(tokens2)
        token_jaccard = len(token_intersection) / len(token_union) if token_union else 0
        
        # 字符集合的匹配度
        if chars1 is None:
            chars1 = set(clean_text1.replace(' ', ''))
        if chars2 is None:
            chars2 = set(clean_text2.replace(' ', ''))
            
        char_intersection = chars1.intersection(chars2)
        char_union = chars1.union(chars2)
        char_similarity = len(char_intersection) / len(char_union) if char_union else 0
        
        # 综合相似度：2-gram权重 0.65，单字权重 0.35
        return (token_jaccard * 0.65 + char_similarity * 0.35)
    
    def calculate_similarity(self, text1, text2):
        """保持向后兼容的相似度计算方法"""
        clean_text1 = self.clean_text(text1)
        clean_text2 = self.clean_text(text2)
        words1 = set(clean_text1.split())
        words2 = set(clean_text2.split())
        return self.calculate_similarity_fast(clean_text1, clean_text2, words1, words2)
    
    def question_exists(self, content):
        """检查题目是否已存在"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT COUNT(*) FROM questions WHERE content = ?
            ''', (content,))
            
            result = cursor.fetchone()
            return result[0] > 0 if result else False
    
    def get_all_questions(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, content, answer, type, keywords FROM questions
            ''')
            
            return cursor.fetchall()
    
    def delete_question(self, question_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            DELETE FROM questions WHERE id = ?
            ''', (question_id,))
            
            conn.commit()
        
    def update_question(self, question_id, answer, type, keywords=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if keywords is not None:
                cursor.execute('''
                UPDATE questions SET answer = ?, type = ?, keywords = ? WHERE id = ?
                ''', (answer, type, keywords, question_id))
            else:
                cursor.execute('''
                UPDATE questions SET answer = ?, type = ? WHERE id = ?
                ''', (answer, type, question_id))
            
            conn.commit()
    
    def close(self):
        """关闭数据库连接"""
        self.close_connection()
    
    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        try:
            self.close_connection()
        except:
            pass