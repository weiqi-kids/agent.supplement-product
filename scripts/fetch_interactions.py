#!/usr/bin/env python3
"""交互作用文獻擷取腳本 — 從 PubMed 查詢 DDI/DFI/DHI 文獻"""
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
from http.client import IncompleteRead
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# 載入 .env 檔案
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# NCBI API endpoints
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# 載入環境變數
API_KEY = os.environ.get("NCBI_API_KEY", "")
EMAIL = os.environ.get("NCBI_EMAIL", "")

# 速率限制（無 API Key: 3/s, 有 API Key: 10/s）
RATE_LIMIT = 0.35 if API_KEY else 0.5

# 交互作用類型查詢設定
INTERACTION_QUERIES = {
    "ddi": {
        "name": "Drug-Drug Interactions",
        "queries": [
            {
                "name": "general",
                "query": '(drug drug interaction[Title]) AND (adverse[Title/Abstract] OR safety[Title/Abstract] OR risk[Title/Abstract])'
            },
            {
                "name": "anticoagulant",
                "query": '(warfarin[Title] OR anticoagulant[Title]) AND (drug interaction[Title])'
            },
            {
                "name": "statin",
                "query": '(statin[Title] OR atorvastatin[Title] OR simvastatin[Title]) AND (drug interaction[Title])'
            },
            {
                "name": "antihypertensive",
                "query": '(antihypertensive[Title] OR blood pressure[Title]) AND (drug interaction[Title])'
            }
        ]
    },
    "dfi": {
        "name": "Drug-Food Interactions",
        "queries": [
            {
                "name": "general",
                "query": '(drug food interaction[Title]) AND (bioavailability[Title/Abstract] OR absorption[Title/Abstract])'
            },
            {
                "name": "grapefruit",
                "query": '(grapefruit[Title]) AND (drug interaction[Title] OR CYP3A4[Title/Abstract])'
            },
            {
                "name": "vitamin_k",
                "query": '(vitamin K[Title] OR leafy green[Title]) AND (warfarin[Title] OR anticoagulant[Title])'
            },
            {
                "name": "dairy",
                "query": '(dairy[Title] OR milk[Title] OR calcium[Title]) AND (antibiotic[Title] OR drug absorption[Title])'
            },
            {
                "name": "alcohol",
                "query": '(alcohol[Title] OR ethanol[Title]) AND (drug interaction[Title])'
            }
        ]
    },
    "dhi": {
        "name": "Drug-Herb/Supplement Interactions",
        "queries": [
            {
                "name": "general",
                "query": '(herb drug interaction[Title] OR supplement drug interaction[Title] OR natural product drug interaction[Title])'
            },
            {
                "name": "fish_oil",
                "query": '(fish oil[Title] OR omega-3[Title] OR EPA[Title] OR DHA[Title]) AND (drug interaction[Title] OR warfarin[Title] OR anticoagulant[Title])'
            },
            {
                "name": "ginkgo",
                "query": '(ginkgo[Title] OR ginkgo biloba[Title]) AND (drug interaction[Title] OR bleeding[Title/Abstract])'
            },
            {
                "name": "st_johns_wort",
                "query": '(st john wort[Title] OR hypericum[Title]) AND (drug interaction[Title])'
            },
            {
                "name": "curcumin",
                "query": '(curcumin[Title] OR turmeric[Title]) AND (drug interaction[Title] OR CYP450[Title/Abstract])'
            },
            {
                "name": "ginseng",
                "query": '(ginseng[Title]) AND (drug interaction[Title])'
            },
            {
                "name": "garlic",
                "query": '(garlic[Title] OR allicin[Title]) AND (drug interaction[Title] OR anticoagulant[Title])'
            },
            {
                "name": "vitamin_e",
                "query": '(vitamin E[Title]) AND (drug interaction[Title] OR anticoagulant[Title])'
            }
        ]
    }
}


def esearch(query: str, max_results: int = 200, date_range_years: int = 10) -> list:
    """執行 ESearch 取得 PMID 列表"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=date_range_years * 365)

    # 加入 humans 和 English 過濾
    full_query = f"({query}) AND humans[MH] AND English[Language]"

    params = {
        "db": "pubmed",
        "term": full_query,
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
        print(f"    ESearch 失敗: {e}", file=sys.stderr)
        return []

    result = data.get("esearchresult", {})
    pmids = result.get("idlist", [])
    count = result.get("count", "0")

    print(f"    找到 {count} 篇，取得 {len(pmids)} 個 PMID")
    return pmids


def efetch_batch(pmids: list, batch_size: int = 100, max_retries: int = 3) -> list:
    """批次執行 EFetch 取得文獻詳細資料"""
    all_articles = []

    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]

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

        for retry in range(max_retries):
            try:
                req = Request(url, headers={"User-Agent": "SupplementProductAgent/1.0"})
                with urlopen(req, timeout=60) as response:
                    xml_content = response.read()

                articles = parse_pubmed_xml(xml_content)
                all_articles.extend(articles)
                break

            except (HTTPError, URLError, ET.ParseError, IncompleteRead) as e:
                if retry < max_retries - 1:
                    time.sleep(2 * (retry + 1))
                else:
                    print(f"    EFetch 失敗: {e}", file=sys.stderr)

        time.sleep(RATE_LIMIT)

    return all_articles


def parse_pubmed_xml(xml_content: bytes) -> list:
    """解析 PubMed XML 回應"""
    articles = []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
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

        articles.append(article)

    return articles


def save_to_jsonl(articles: list, interaction_type: str, category: str) -> str:
    """將文獻資料儲存為 JSONL"""
    raw_dir = BASE_DIR / "docs" / "Extractor" / interaction_type / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    output_file = raw_dir / f"{category}-{today}.jsonl"

    with open(output_file, "w", encoding="utf-8") as f:
        for article in articles:
            article["interaction_type"] = interaction_type.upper()
            article["category"] = category
            article["fetched_at"] = datetime.now().isoformat()
            f.write(json.dumps(article, ensure_ascii=False) + "\n")

    return str(output_file)


def fetch_interaction_type(interaction_type: str, limit: int = 200, category: str = None):
    """擷取特定類型的交互作用文獻"""
    config = INTERACTION_QUERIES.get(interaction_type)
    if not config:
        print(f"未知的交互類型: {interaction_type}", file=sys.stderr)
        sys.exit(1)

    print(f"\n📚 擷取 {config['name']}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    queries = config["queries"]

    # 如果指定了 category，只擷取該類別
    if category:
        queries = [q for q in queries if q["name"] == category]
        if not queries:
            print(f"未知的類別: {category}", file=sys.stderr)
            sys.exit(1)

    total_articles = 0
    all_pmids = set()

    for query_config in queries:
        query_name = query_config["name"]
        query = query_config["query"]

        print(f"\n  📖 類別: {query_name}")
        print(f"     查詢: {query[:60]}...")

        # ESearch
        pmids = esearch(query, max_results=limit)

        # 去重
        new_pmids = [p for p in pmids if p not in all_pmids]
        all_pmids.update(new_pmids)

        if not new_pmids:
            print("     無新結果")
            continue

        # EFetch
        print(f"     取得 {len(new_pmids)} 篇文獻...")
        articles = efetch_batch(new_pmids)

        if not articles:
            print("     取得文獻失敗")
            continue

        # 儲存
        output_file = save_to_jsonl(articles, interaction_type, query_name)
        print(f"     ✅ 儲存 {len(articles)} 篇 → {output_file}")
        total_articles += len(articles)

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ 完成 {config['name']}")
    print(f"   總文獻數：{total_articles}")
    print(f"   唯一 PMID：{len(all_pmids)}")


def list_categories(interaction_type: str):
    """列出可用類別"""
    config = INTERACTION_QUERIES.get(interaction_type)
    if not config:
        print(f"未知的交互類型: {interaction_type}", file=sys.stderr)
        return

    print(f"📋 {config['name']} 可用類別：")
    for q in config["queries"]:
        print(f"  - {q['name']}")


def main():
    parser = argparse.ArgumentParser(description="交互作用文獻擷取")
    parser.add_argument("--type", required=True, choices=["ddi", "dfi", "dhi"],
                       help="交互類型")
    parser.add_argument("--all", action="store_true", help="擷取所有類別")
    parser.add_argument("--category", help="指定類別")
    parser.add_argument("--limit", type=int, default=200, help="每類別最大結果數")
    parser.add_argument("--list", action="store_true", help="列出可用類別")
    args = parser.parse_args()

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("💊 交互作用文獻擷取")
    print(f"   類型：{args.type.upper()}")
    if API_KEY:
        print("   API Key：已設定")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if args.list:
        list_categories(args.type)
        return

    if args.all or args.category:
        fetch_interaction_type(args.type, args.limit, args.category)
    else:
        # 預設擷取所有
        fetch_interaction_type(args.type, args.limit)


if __name__ == "__main__":
    main()
