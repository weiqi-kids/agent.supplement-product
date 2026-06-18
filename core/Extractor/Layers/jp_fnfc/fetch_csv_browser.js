#!/usr/bin/env node
/*
 * jp_fnfc 瀏覽器自動下載器
 * ─────────────────────────────────────────────────────────────
 * 消費者庁「機能性表示食品検索」(cssc01) 是 Salesforce Lightning
 * 訪客社群，CSV 由前端 Aura 動作即時產生，Document ID 每次都不同，
 * 無法用固定 URL 下載（這是 fetch.sh 預設 URL 會失效的原因）。
 *
 * 此腳本以 puppeteer-core 驅動系統 Chrome，點擊
 * 「前日までの全届出の全項目出力(CSV出力)」按鈕，攔截分割下載的
 * 多個 CSV，合併成單一 CSV 輸出，供 fetch.sh --csv 轉換。
 *
 * 用法：
 *   node fetch_csv_browser.js [輸出CSV路徑]
 *   （預設輸出 docs/Extractor/jp_fnfc/raw/fnfc-YYYY-MM-DD.csv）
 *
 * 前置：
 *   npm i puppeteer-core   （使用系統 Chrome，不另下載 Chromium）
 *   並確認 CHROME 路徑正確。
 */
const fs = require('fs');
const path = require('path');

const CHROME = process.env.CHROME_PATH
  || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORTAL = 'https://www.fld.caa.go.jp/caaks/cssc01/';

function todayStr() {
  const d = new Date();
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

(async () => {
  let puppeteer;
  try { puppeteer = require('puppeteer-core'); }
  catch { console.error('需要 puppeteer-core：npm i puppeteer-core'); process.exit(2); }

  const rawDir = path.resolve(__dirname, '../../../../docs/Extractor/jp_fnfc/raw');
  const outCsv = process.argv[2] || path.join(rawDir, `fnfc-${todayStr()}.csv`);
  const tmpDir = fs.mkdtempSync('/tmp/fnfc_dl_');
  fs.mkdirSync(rawDir, { recursive: true });

  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--lang=ja-JP'],
  });
  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36');
  const client = await page.target().createCDPSession();
  await client.send('Page.setDownloadBehavior', { behavior: 'allow', downloadPath: tmpDir });

  console.error('→ 開啟 cssc01');
  await page.goto(PORTAL, { waitUntil: 'networkidle2', timeout: 90000 });
  await new Promise(r => setTimeout(r, 8000));

  console.error('→ 點擊「全項目出力(CSV出力)」');
  const clicked = await page.evaluate(() => {
    function* all(root){ for(const el of root.querySelectorAll('*')){ yield el; if(el.shadowRoot) yield* all(el.shadowRoot);} }
    for (const el of all(document)) {
      const t = (el.innerText || el.textContent || '').trim();
      if (/CSV出力/.test(t) && /^(A|BUTTON|SPAN|LIGHTNING-BUTTON)$/.test(el.tagName)) {
        (el.closest('a,button,lightning-button') || el).click();
        return true;
      }
    }
    return false;
  });
  if (!clicked) { console.error('找不到 CSV出力 按鈕'); await browser.close(); process.exit(1); }

  // 等待所有分割檔下載完成（連續 8 秒無新檔/無 .crdownload 視為完成）
  let stable = 0, lastSig = '';
  for (let i = 0; i < 150; i++) {
    await new Promise(r => setTimeout(r, 2000));
    const files = fs.readdirSync(tmpDir);
    const partial = files.filter(f => f.endsWith('.crdownload')).length;
    const done = files.filter(f => f.endsWith('.csv'));
    const sig = done.sort().join('|') + '#' + done.reduce((s,f)=>s+fs.statSync(path.join(tmpDir,f)).size,0);
    if (done.length && partial === 0 && sig === lastSig) { stable++; if (stable >= 4) break; }
    else stable = 0;
    lastSig = sig;
    if (i % 5 === 0) console.error(`  ...${i*2}s 完成${done.length}檔 partial=${partial}`);
  }
  await browser.close();

  // 合併分割檔（csv 解析，處理多行欄位；保留單一表頭）
  const parts = fs.readdirSync(tmpDir).filter(f => f.endsWith('.csv'))
    .sort((a,b) => (a.match(/_(\d+)\.csv$/)?.[1]||0) - (b.match(/_(\d+)\.csv$/)?.[1]||0));
  if (!parts.length) { console.error('無 CSV 下載'); process.exit(1); }

  // 用 Python csv 合併（Node 無內建 csv parser）— 改以簡易狀態機合併
  // 各分割檔表頭相同，去除非首檔的表頭首行
  const out = fs.createWriteStream(outCsv);
  let headerWritten = false, total = 0;
  for (const p of parts) {
    const content = fs.readFileSync(path.join(tmpDir, p), 'utf8');
    const nl = content.indexOf('\n');
    const header = content.slice(0, nl + 1);
    const body = content.slice(nl + 1);
    if (!headerWritten) { out.write(header); headerWritten = true; }
    out.write(body);
    if (!body.endsWith('\n')) out.write('\n');
    total++;
  }
  out.end();
  fs.rmSync(tmpDir, { recursive: true, force: true });
  console.error(`✅ 合併 ${total} 個分割檔 → ${outCsv}`);
  console.log(outCsv);
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
