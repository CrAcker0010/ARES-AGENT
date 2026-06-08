import sqlite3
import re
import math
import json
import os
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'else', 'to', 'of', 'in', 'on', 'at', 
    'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 
    'after', 'above', 'below', 'from', 'up', 'down', 'in', 'out', 'off', 'over', 'under', 
    'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 
    'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 
    'will', 'just', 'don', 'should', 'now', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 
    'ourselves', 'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 
    'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 
    'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 
    'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 
    'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'would', 'should', 'could', 
    'ought', 'i\'m', 'you\'re', 'he\'s', 'she\'s', 'it\'s', 'we\'re', 'they\'re', 'i\'ve', 
    'you\'ve', 'we\'ve', 'they\'ve', 'i\'d', 'you\'d', 'he\'d', 'she\'d', 'we\'d', 'they\'d', 
    'i\'ll', 'you\'ll', 'he\'ll', 'she\'ll', 'we\'ll', 'they\'ll', 'isn\'t', 'aren\'t', 
    'wasn\'t', 'weren\'t', 'hasn\'t', 'haven\'t', 'hadn\'t', 'doesn\'t', 'don\'t', 'didn\'t', 
    'won\'t', 'wouldn\'t', 'shan\'t', 'shouldn\'t', 'can\'t', 'cannot', 'couldn\'t', 'mustn\'t'
}

def tokenize(text):
    if not text:
        return []
    text = text.lower()
    words = re.findall(r'\b[a-z0-9_]{2,}\b', text)
    return [w for w in words if w not in STOP_WORDS]

class VectorGraphStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # facts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    timestamp REAL NOT NULL
                )
            """)
            # connections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connections (
                    source_id INTEGER,
                    target_id INTEGER,
                    type TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    description TEXT,
                    PRIMARY KEY (source_id, target_id, type),
                    FOREIGN KEY (source_id) REFERENCES facts(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_id) REFERENCES facts(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def add_fact(self, content: str, category: str = "general") -> int:
        content = content.strip()
        if not content:
            return -1
        # Basic category auto-detection if it's 'general'
        if category == "general":
            lower_content = content.lower()
            if any(k in lower_content for k in ["prefer", "like", "love", "hate", "style", "habit"]):
                category = "preference"
            elif any(k in lower_content for k in ["project", "repo", "task", "work", "todo", "build"]):
                category = "project_context"
            elif any(k in lower_content for k in ["tech", "language", "python", "javascript", "db", "docker", "git"]):
                category = "tech_stack"
            elif any(k in lower_content for k in ["user", "name", "developer", "age", "location", "email"]):
                category = "personal"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO facts (content, category, timestamp) VALUES (?, ?, ?)",
                    (content, category, time.time())
                )
                fact_id = cursor.lastrowid
                conn.commit()
                # Compute connections dynamically
                self.recalculate_similarities(conn)
                return fact_id
            except sqlite3.IntegrityError:
                # Fact already exists, retrieve ID
                cursor.execute("SELECT id FROM facts WHERE content = ?", (content,))
                row = cursor.fetchone()
                return row[0] if row else -1

    def remove_fact(self, fact_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            cursor.execute("DELETE FROM connections WHERE source_id = ? OR target_id = ?", (fact_id, fact_id))
            conn.commit()
            self.recalculate_similarities(conn)

    def add_connection(self, source_id: int, target_id: int, rel_type: str, weight: float = 1.0, description: str = None):
        if source_id == target_id:
            return
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO connections (source_id, target_id, type, weight, description)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, type) DO UPDATE SET
                    weight = excluded.weight,
                    description = excluded.description
            """, (source_id, target_id, rel_type, weight, description))
            conn.commit()

    def add_connection_by_content(self, source_content: str, target_content: str, rel_type: str, weight: float = 1.0, description: str = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM facts WHERE content = ?", (source_content.strip(),))
            s_row = cursor.fetchone()
            cursor.execute("SELECT id FROM facts WHERE content = ?", (target_content.strip(),))
            t_row = cursor.fetchone()
            if s_row and t_row:
                self.add_connection(s_row[0], t_row[0], rel_type, weight, description)

    def get_all_facts(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, content, category, timestamp FROM facts")
            return [{"id": r[0], "content": r[1], "category": r[2], "timestamp": r[3]} for r in cursor.fetchall()]

    def search_facts(self, query: str, limit: int = 10) -> list:
        facts = self.get_all_facts()
        if not facts or not query.strip():
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Recalculate TF-IDF scores dynamically
        docs_tokens = {f["id"]: tokenize(f["content"]) for f in facts}
        vocab = set()
        for tlist in docs_tokens.values():
            vocab.update(tlist)
        vocab.update(query_tokens)

        # Document frequencies
        N = len(facts)
        df = {}
        for term in vocab:
            df[term] = sum(1 for tlist in docs_tokens.values() if term in tlist)

        # IDF
        idf = {}
        for term in vocab:
            idf[term] = math.log(1.0 + N / (1.0 + df[term])) + 1.0

        # Query vector
        q_tf = {}
        for t in query_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1
        q_vec = {t: tf * idf[t] for t, tf in q_tf.items()}
        q_norm = math.sqrt(sum(v*v for v in q_vec.values()))

        results = []
        for fact in facts:
            fid = fact["id"]
            tokens = docs_tokens[fid]
            if not tokens:
                continue
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            doc_vec = {t: f * idf[t] for t, f in tf.items()}
            doc_norm = math.sqrt(sum(v*v for v in doc_vec.values()))
            
            if q_norm == 0 or doc_norm == 0:
                score = 0.0
            else:
                dot_product = sum(q_vec.get(t, 0) * doc_vec.get(t, 0) for t in doc_vec if t in q_vec)
                score = dot_product / (q_norm * doc_norm)
            
            if score > 0.0:
                results.append((score, fact))

        results.sort(key=lambda x: x[0], reverse=True)
        return [{"score": score, "fact": fact} for score, fact in results[:limit]]

    def recalculate_similarities(self, conn):
        cursor = conn.cursor()
        # Fetch all facts
        cursor.execute("SELECT id, content FROM facts")
        rows = cursor.fetchall()
        if len(rows) < 2:
            # Delete any similarity connections
            cursor.execute("DELETE FROM connections WHERE type = 'similarity'")
            return

        facts = [{"id": r[0], "content": r[1]} for r in rows]
        docs_tokens = {f["id"]: tokenize(f["content"]) for f in facts}
        vocab = set()
        for tlist in docs_tokens.values():
            vocab.update(tlist)

        N = len(facts)
        df = {}
        for term in vocab:
            df[term] = sum(1 for tlist in docs_tokens.values() if term in tlist)

        idf = {}
        for term in vocab:
            idf[term] = math.log(1.0 + N / (1.0 + df[term])) + 1.0

        # Build document vectors
        doc_vectors = {}
        doc_norms = {}
        for fact in facts:
            fid = fact["id"]
            tokens = docs_tokens[fid]
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            vec = {t: f * idf[t] for t, f in tf.items()}
            norm = math.sqrt(sum(v*v for v in vec.values()))
            doc_vectors[fid] = vec
            doc_norms[fid] = norm

        # Delete existing similarity connections
        cursor.execute("DELETE FROM connections WHERE type = 'similarity'")

        # Compute pairwise similarities
        similarity_threshold = 0.15
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                id1 = facts[i]["id"]
                id2 = facts[j]["id"]
                norm1 = doc_norms[id1]
                norm2 = doc_norms[id2]
                if norm1 == 0 or norm2 == 0:
                    continue
                vec1 = doc_vectors[id1]
                vec2 = doc_vectors[id2]
                dot_product = sum(vec1[t] * vec2[t] for t in vec1 if t in vec2)
                score = dot_product / (norm1 * norm2)
                if score >= similarity_threshold:
                    cursor.execute("""
                        INSERT INTO connections (source_id, target_id, type, weight, description)
                        VALUES (?, ?, 'similarity', ?, NULL)
                    """, (id1, id2, score))

    def export_graph_js(self, output_js_path: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Fetch facts
            cursor.execute("SELECT id, content, category, timestamp FROM facts")
            nodes = []
            for r in cursor.fetchall():
                nodes.append({
                    "id": r[0],
                    "label": r[1],
                    "category": r[2],
                    "timestamp": r[3]
                })

            # Fetch connections
            cursor.execute("""
                SELECT source_id, target_id, type, weight, description
                FROM connections
            """)
            edges = []
            for r in cursor.fetchall():
                edges.append({
                    "from": r[0],
                    "to": r[1],
                    "type": r[2],
                    "weight": r[3],
                    "description": r[4] or ""
                })

        data = {
            "nodes": nodes,
            "edges": edges,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        os.makedirs(os.path.dirname(output_js_path), exist_ok=True)
        # Write to JS file
        js_content = f"window.GRAPH_DATA = {json.dumps(data, indent=2)};"
        with open(output_js_path, "w", encoding="utf-8") as f:
            f.write(js_content)
        logger.info(f"Graph data successfully exported to {output_js_path}")
