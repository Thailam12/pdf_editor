import pymupdf


class ArticleService:
    def __init__(self, editor):
        self.editor = editor
        self._threads = {}
        self._next_thread_id = 1

    def create_article_thread(self, pages_and_positions):
        """Create an article thread from a list of (page_num, [rect_tuples])."""
        try:
            thread_id = self._next_thread_id
            self._next_thread_id += 1
            self._threads[thread_id] = {
                "id": thread_id,
                "articles": []
            }
            for page_num, rects in pages_and_positions:
                for rect_tuple in rects:
                    if len(rect_tuple) == 4:
                        self._threads[thread_id]["articles"].append({
                            "page": page_num,
                            "rect": list(rect_tuple)
                        })
            doc = self.editor.pdf_utils.doc
            if doc is not None:
                for entry in self._threads[thread_id]["articles"]:
                    page_num = entry["page"]
                    if 0 <= page_num < len(doc):
                        page = doc[page_num]
                        rect = pymupdf.Rect(*entry["rect"])
                        try:
                            page.insert_textbox(
                                rect, "",
                                fontsize=1,
                                fontname="helv",
                                color=(0, 0, 0)
                            )
                        except Exception:
                            pass
            return thread_id
        except Exception as e:
            raise RuntimeError(f"Cannot create article thread: {e}")

    def add_to_thread(self, thread_id, page_num, rect):
        """Add a new article frame to an existing thread."""
        try:
            if thread_id not in self._threads:
                raise ValueError(f"Thread {thread_id} not found")
            self._threads[thread_id]["articles"].append({
                "page": page_num,
                "rect": list(rect) if not isinstance(rect, list) else rect
            })
        except Exception as e:
            raise RuntimeError(f"Cannot add to thread: {e}")

    def navigate_thread(self, thread_id):
        """Navigate through a thread. Returns list of rects in order."""
        try:
            if thread_id not in self._threads:
                return []
            articles = self._threads[thread_id]["articles"]
            return [
                {
                    "page": a["page"],
                    "rect": a["rect"]
                }
                for a in sorted(articles, key=lambda x: (x["page"], x["rect"][1]))
            ]
        except Exception as e:
            return []

    def delete_thread(self, thread_id):
        """Delete an article thread."""
        try:
            if thread_id in self._threads:
                del self._threads[thread_id]
        except Exception as e:
            raise RuntimeError(f"Cannot delete thread: {e}")

    def list_threads(self):
        """Return list of all thread IDs and their article counts."""
        return [
            {
                "id": tid,
                "article_count": len(t["articles"])
            }
            for tid, t in self._threads.items()
        ]
