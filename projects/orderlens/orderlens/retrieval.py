"""외부 API 없이 재현할 수 있는 BM25 문서 검색 기준선입니다. 생성형 AI는 아닙니다."""

import math
import re
from collections import Counter

STOPWORDS = {"어떻게", "무엇", "알려주세요", "해주세요", "방법", "관련", "어떤"}


def tokenize(text: str) -> list[str]:
    result = []
    for word in re.findall(r"[a-z0-9]+|[가-힣]+", text.lower()):
        if word in STOPWORDS:
            continue
        if re.fullmatch(r"[가-힣]+", word):
            # 형태소 분석기 없이 조사 변화에 일부 대응하는 작은 기준선입니다.
            result.extend(word[index : index + 2] for index in range(len(word) - 1))
        else:
            result.append(word)
    return result


class BM25Index:
    def __init__(self, documents: list[dict]):
        self.documents = documents
        self.counts = [Counter(tokenize(doc["title"] + " " + doc["text"])) for doc in documents]
        self.lengths = [sum(count.values()) for count in self.counts]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 1
        self.document_frequency = Counter()
        for counts in self.counts:
            self.document_frequency.update(counts.keys())

    def search(self, query: str, top_k=3) -> list[dict]:
        tokens = set(tokenize(query))
        total = len(self.documents)
        matches = []
        for doc, counts, length in zip(self.documents, self.counts, self.lengths):
            score = 0.0
            for token in tokens:
                tf = counts[token]
                if not tf:
                    continue
                df = self.document_frequency[token]
                inverse_frequency = math.log(1 + (total - df + 0.5) / (df + 0.5))
                normalization = tf + 1.5 * (1 - 0.75 + 0.75 * length / self.average_length)
                score += inverse_frequency * tf * 2.5 / normalization
            if score > 0:
                matches.append(
                    {
                        "document_id": doc["id"],
                        "title": doc["title"],
                        "score": round(score, 6),
                        "excerpt": doc["text"],
                        "source": "bundled_demo_policy",
                        "version": doc["version"],
                    }
                )
        matches.sort(key=lambda item: (-item["score"], item["document_id"]))
        return matches[:top_k]
