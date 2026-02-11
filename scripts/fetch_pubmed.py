#!/usr/bin/env python3
"""PubMed 文獻擷取腳本 — 從 NCBI E-utilities API 查詢主題相關文獻"""
import json
import os
import sys
import argparse
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS_DIR = os.path.join(BASE_DIR, "core/Narrator/Modes/topic_tracking/topics")
RAW_DIR = os.path.join(BASE_DIR, "docs/Extractor/pubmed/raw")

# NCBI API endpoints
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# 載入環境變數
API_KEY = os.environ.get("NCBI_API_KEY", "")
EMAIL = os.environ.get("NCBI_EMAIL", "")

# 速率限制（無 API Key: 3/s, 有 API Key: 10/s）
RATE_LIMIT = 0.35 if API_KEY else 0.5


def load_topic_config(topic_id: str) -> dict:
    """載入主題設定檔"""
    import yaml
    topic_file = os.path.join(TOPICS_DIR, f"{topic_id}.yaml")
    if not os.path.exists(topic_file):
        print(f"主題設定檔不存在: {topic_file}", file=sys.stderr)
        sys.exit(1)

    with open(topic_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_pubmed_query(topic_config: dict) -> str:
    """從主題設定建構 PubMed 查詢"""
    # 檢查是否有自訂 pubmed 查詢
    if "pubmed" in topic_config and "query" in topic_config["pubmed"]:
        return topic_config["pubmed"]["query"]

    # 從 keywords 建構查詢
    keywords = topic_config.get("keywords", {})
    exact_terms = keywords.get("exact", [])
    fuzzy_terms = keywords.get("fuzzy", [])

    # 組合精確關鍵詞
    all_terms = exact_terms + fuzzy_terms
    if not all_terms:
        print("主題無關鍵詞定義", file=sys.stderr)
        sys.exit(1)

    # 建構查詢：關鍵詞 OR 組合 + 補充類型篩選
    term_parts = [f'"{term}"[Title/Abstract]' for term in all_terms[:10]]  # 限制最多 10 個
    base_query = " OR ".join(term_parts)

    # 加上補充品相關篩選
    supplement_filter = '(supplement*[Title/Abstract] OR nutraceutical*[Title/Abstract] OR "dietary supplement"[Title/Abstract])'

    return f"({base_query}) AND {supplement_filter}"


def esearch(query: str, max_results: int = 500, date_range_years: int = 5) -> list:
    """執行 ESearch 取得 PMID 列表"""
    # 計算日期範圍
    end_date = datetime.now()
    start_date = end_date - timedelta(days=date_range_years * 365)

    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "mindate": start_date.strftime("%Y/%m/%d"),
        "maxdate": end_date.strftime("%Y/%m/%d"),
        "datetype": "pdat",
        "usehistory": "n"
    }

    if API_KEY:
        params["api_key"] = API_KEY
    if EMAIL:
        params["email"] = EMAIL

    url = f"{ESEARCH_URL}?{urlencode(params)}"

    try:
        req = Request(url, headers={"User-Agent": "SupplementProductAgent/1.0"})
        with urlopen(req, timeout=30) as response:
            data = json.load(response)
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"ESearch 失敗: {e}", file=sys.stderr)
        return []

    result = data.get("esearchresult", {})
    pmids = result.get("idlist", [])
    count = result.get("count", "0")

    print(f"  找到 {count} 篇文獻，取得 {len(pmids)} 個 PMID")
    return pmids


def efetch_batch(pmids: list, batch_size: int = 100) -> list:
    """批次執行 EFetch 取得文獻詳細資料"""
    all_articles = []

    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        print(f"  取得文獻 {i+1}-{min(i+batch_size, len(pmids))}...")

        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "rettype": "xml",
            "retmode": "xml"
        }

        if API_KEY:
            params["api_key"] = API_KEY
        if EMAIL:
            params["email"] = EMAIL

        url = f"{EFETCH_URL}?{urlencode(params)}"

        try:
            req = Request(url, headers={"User-Agent": "SupplementProductAgent/1.0"})
            with urlopen(req, timeout=60) as response:
                xml_content = response.read()

            articles = parse_pubmed_xml(xml_content)
            all_articles.extend(articles)

        except (HTTPError, URLError, ET.ParseError) as e:
            print(f"  EFetch 批次失敗: {e}", file=sys.stderr)

        # 速率限制
        time.sleep(RATE_LIMIT)

    return all_articles


def parse_pubmed_xml(xml_content: bytes) -> list:
    """解析 PubMed XML 回應"""
    articles = []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        print(f"  XML 解析失敗: {e}", file=sys.stderr)
        return []

    for article_elem in root.findall(".//PubmedArticle"):
        article = {}

        # PMID
        pmid_elem = article_elem.find(".//PMID")
        article["pmid"] = pmid_elem.text if pmid_elem is not None else ""

        # 標題
        title_elem = article_elem.find(".//ArticleTitle")
        article["title"] = title_elem.text if title_elem is not None else ""

        # 期刊
        journal_elem = article_elem.find(".//Journal/Title")
        article["journal"] = journal_elem.text if journal_elem is not None else ""

        # 發表日期
        pub_date = article_elem.find(".//PubDate")
        if pub_date is not None:
            year = pub_date.findtext("Year", "")
            month = pub_date.findtext("Month", "01")
            day = pub_date.findtext("Day", "01")
            # 月份可能是文字
            month_map = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}
            month = month_map.get(month, month.zfill(2) if month.isdigit() else "01")
            article["pub_date"] = f"{year}-{month}-{day.zfill(2)}" if year else ""
        else:
            article["pub_date"] = ""

        # 作者
        authors = []
        for author in article_elem.findall(".//Author"):
            lastname = author.findtext("LastName", "")
            forename = author.findtext("ForeName", "")
            if lastname:
                authors.append(f"{lastname} {forename}".strip())
        article["authors"] = authors

        # 摘要
        abstract_texts = []
        for abstract_text in article_elem.findall(".//AbstractText"):
            label = abstract_text.get("Label", "")
            text = abstract_text.text or ""
            if label:
                abstract_texts.append(f"**{label}**: {text}")
            else:
                abstract_texts.append(text)
        article["abstract"] = "\n\n".join(abstract_texts)

        # 出版類型
        pub_types = []
        for pub_type in article_elem.findall(".//PublicationType"):
            if pub_type.text:
                pub_types.append(pub_type.text)
        article["publication_types"] = pub_types

        # MeSH 術語
        mesh_terms = []
        for mesh in article_elem.findall(".//MeshHeading/DescriptorName"):
            if mesh.text:
                mesh_terms.append(mesh.text)
        article["mesh_terms"] = mesh_terms

        # 關鍵詞
        keywords = []
        for keyword in article_elem.findall(".//Keyword"):
            if keyword.text:
                keywords.append(keyword.text)
        article["keywords"] = keywords

        articles.append(article)

    return articles


def save_to_jsonl(articles: list, topic_id: str) -> str:
    """將文獻資料儲存為 JSONL"""
    os.makedirs(RAW_DIR, exist_ok=True)

    today = datetime.now().strftime("%Y-%m")
    output_file = os.path.join(RAW_DIR, f"{topic_id}-{today}.jsonl")

    with open(output_file, "w", encoding="utf-8") as f:
        for article in articles:
            article["topic"] = topic_id
            article["fetched_at"] = datetime.now().isoformat()
            f.write(json.dumps(article, ensure_ascii=False) + "\n")

    return output_file


def list_topics() -> list:
    """列出所有可用主題"""
    import yaml
    topics = []
    if not os.path.exists(TOPICS_DIR):
        return topics

    for f in os.listdir(TOPICS_DIR):
        if f.endswith(".yaml"):
            topic_id = f.replace(".yaml", "")
            topics.append(topic_id)

    return topics


def main():
    parser = argparse.ArgumentParser(description="PubMed 文獻擷取")
    parser.add_argument("--topic", help="指定主題 ID")
    parser.add_argument("--all", action="store_true", help="擷取所有主題")
    parser.add_argument("--limit", type=int, default=500, help="每主題最大結果數")
    parser.add_argument("--years", type=int, default=5, help="查詢年數範圍")
    parser.add_argument("--list", action="store_true", help="列出可用主題")
    args = parser.parse_args()

    if args.list:
        topics = list_topics()
        print("可用主題:")
        for t in topics:
            print(f"  - {t}")
        return

    if args.all:
        topics = list_topics()
    elif args.topic:
        topics = [args.topic]
    else:
        print("請指定 --topic 或 --all", file=sys.stderr)
        sys.exit(1)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📚 PubMed 文獻擷取")
    print(f"   主題數：{len(topics)}")
    print(f"   每主題限制：{args.limit} 篇")
    print(f"   年數範圍：{args.years} 年")
    if API_KEY:
        print("   API Key：已設定")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    total_articles = 0

    for topic_id in topics:
        print(f"\n📖 處理主題: {topic_id}")

        try:
            config = load_topic_config(topic_id)
        except Exception as e:
            print(f"  載入設定失敗: {e}", file=sys.stderr)
            continue

        query = build_pubmed_query(config)
        print(f"  查詢: {query[:80]}...")

        # ESearch
        pmids = esearch(query, max_results=args.limit, date_range_years=args.years)
        if not pmids:
            print("  無結果")
            continue

        # EFetch
        articles = efetch_batch(pmids)
        if not articles:
            print("  取得文獻失敗")
            continue

        # 儲存
        output_file = save_to_jsonl(articles, topic_id)
        print(f"  ✅ 儲存 {len(articles)} 篇 → {output_file}")
        total_articles += len(articles)

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Fetch completed: pubmed")
    print(f"   總文獻數：{total_articles}")


if __name__ == "__main__":
    main()
