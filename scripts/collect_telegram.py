import json, os, re, hashlib
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from html import unescape

CHANNELS = ["web_fl", "job_webdev", "webfrl", "job_developer", "digitaltender"]
OUT = "data/leads.json"
KEYWORDS = re.compile(r"(сайт|лендинг|верстк|разработ|фронтенд|frontend|html|css|javascript|\bjs\b|wordpress|доработ|веб-прилож|web\s?site|landing|figma)", re.I)
NEGATIVE = re.compile(r"(ищу работу|ищу заказ|предлагаю услуги|моё портфолио|мое портфолио|резюме|ищем сотрудника|вакансия для разработчика)", re.I)
NOISE = re.compile(r"(подборка лучших постов|лучшие статьи|больше проектов в нашем боте|узнать больше|за последние сутки наш фриланс-бот наш[её]л|#реклама)", re.I)
VACANCY = re.compile(r"(компания\s*:|опыт работы\s*:|зарплата\s*:|требования\s*:|полная занятость|график работы|тип работы\s*:\s*постоянная)", re.I)
BUDGET = re.compile(r"(?:бюджет|оплата|стоимость|цена|до|от)?\s*([0-9][0-9\s.,]{2,})\s*(₽|руб(?:лей|ля)?|р\.?|usd|\$)", re.I)
BLOCKED_APPLY = ("kwork.ru",)
BLOCKED_HANDLES = set(CHANNELS + ["setjobs_bot", "job_webdev", "web_fl", "webfrl", "job_developer", "digitaltender", "digitaltenderbot"])

def clean(s):
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</div>|</p>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t]+", " ", unescape(s)).strip()

def fetch(channel, suffix=""):
    url = f"https://t.me/s/{channel}" + suffix
    req = Request(url, headers={"User-Agent":"Mozilla/5.0 (compatible; PanaceaLeads/1.0)"})
    with urlopen(req, timeout=25) as r:
        html = r.read().decode("utf-8", "replace")
    raw_blocks = re.findall(r'(<div class="tgme_widget_message_wrap[^>]*>.*?)(?=<div class="tgme_widget_message_wrap|<div class="tgme_channel_bottom|$)', html, re.S)
    blocks = []
    for block in raw_blocks:
        post_match = re.search(r'data-post="([^"]+)"', block)
        if post_match:
            blocks.append((post_match.group(1), block))
    items = []
    for post, block in blocks:
        m = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
        if not m:
            continue
        body = clean(m.group(1))
        if len(body) < 35 or not KEYWORDS.search(body) or NEGATIVE.search(body) or NOISE.search(body) or VACANCY.search(body):
            continue
        dm = re.search(r'<time[^>]*datetime="([^"]+)"', block)
        date = dm.group(1) if dm else ""
        links = []
        for attrs, label_html in re.findall(r'<a\b([^>]*)>(.*?)</a>', block, re.S):
            hm = re.search(r'href="([^"]+)"', attrs)
            if hm:
                href = unescape(hm.group(1)).replace("&amp;", "&")
                if href.startswith(("https://", "http://", "tg://")):
                    links.append({"text":clean(label_html)[:100], "url":href})
        handles = re.findall(r'(?<![\w])@([A-Za-z0-9_]{5,})', body)
        external = []
        application_links = []
        for link in links:
            mt = re.fullmatch(r'https?://t\.me/([A-Za-z0-9_]{5,})/?(?:\?[^#]*)?(?:#.*)?', link["url"])
            if mt and mt.group(1).lower() != channel.lower():
                external.append(mt.group(1))
            elif link["url"].startswith(("https://","http://")) and "t.me/" not in link["url"]:
                application_links.append(link)
        contacts = list(dict.fromkeys("@" + h for h in handles + external if h.lower() not in BLOCKED_HANDLES and not h.lower().endswith("bot")))
        phone_matches = re.findall(r"(?<!\w)(?:\+7|8|\+\d{1,3})[\s(\-]*\d[\d\s()\-]{7,}\d", body)
        phones = list(dict.fromkeys(re.sub(r"\s+", " ", p).strip() for p in phone_matches))
        direct_contact = bool(contacts or phones)
        bm = BUDGET.search(body)
        budget = int(re.sub(r"[^0-9]", "", bm.group(1))) if bm else 0
        post_url = "https://t.me/" + post
        fingerprint = hashlib.sha256((post_url + "|" + body[:250]).encode()).hexdigest()
        title = next((x.strip(" -*•—") for x in body.splitlines() if len(x.strip()) > 8), "Заказ на разработку")[:120]
        try:
            posted = datetime.fromisoformat(date.replace("Z","+00:00"))
            age_days = max(0, (datetime.now(timezone.utc)-posted).total_seconds()/86400)
        except Exception:
            age_days = 999
        low_scope = re.search(r"(две страницы|2 страницы|одностранич|лендинг|верстк|исправить|доработать|правк)", body, re.I) is not None
        hard_stack = re.search(r"(react|next\.?js|vue|angular|php|python|fastapi|node\.?js|postgres|api|битрикс|opencart|woocommerce|asp\.net|knockout)", body, re.I) is not None
        blocked_application = any(any(host in x["url"].lower() for host in BLOCKED_APPLY) for x in application_links)
        score = 0
        score += 25 if direct_contact else 0
        score += 20 if age_days <= 2 else 14 if age_days <= 7 else 6 if age_days <= 14 else 0
        score += 20 if low_scope else 5
        score += 10 if budget else 0
        score -= 25 if hard_stack else 0
        score -= 35 if blocked_application else 0
        score -= 30 if age_days > 14 else 0
        eligible = direct_contact and not blocked_application and age_days <= 14 and score >= 35
        best_reason = []
        if contacts: best_reason.append("есть личный Telegram-контакт")
        if phones: best_reason.append("есть номер телефона заказчика")
        if age_days <= 7: best_reason.append("публикация не старше 7 дней")
        if low_scope: best_reason.append("объём похож на доступную HTML/CSS/JS-задачу")
        if blocked_application: best_reason.append("есть только ссылка на биржу, а не прямой контакт")
        items.append({
            "id":fingerprint,"title":title,"text":body[:5000],"channel":"@"+channel,
            "date":date,"url":post_url,"contacts":contacts,"phones":phones,"hasDirectContact":direct_contact,"applicationLinks":application_links,
            "budget":budget,"score":score,"eligible":eligible,"best":False,
            "bestReason":best_reason,
            "questions":["Какой точный объём и какие страницы/функции входят в задачу?","Есть ли макет Figma/PSD и готовые материалы?","Какой срок и порядок оплаты?"],
            "advice":"До согласования попроси макет/ТЗ, зафиксируй объём, срок и этапы оплаты. Не начинай без согласованных условий.",
            "fetchedAt":datetime.now(timezone.utc).isoformat()
        })
    return items

all_items, errors = [], []
for channel in CHANNELS:
    try:
        all_items.extend(fetch(channel))
        if channel == "web_fl":
            all_items.extend(fetch(channel, "?after=604"))
    except Exception as e:
        errors.append({"channel":channel,"error":str(e)[:240]})

# Deduplicate by source post and keep only dated, recent, actionable client requests.
cutoff = datetime.now(timezone.utc) - timedelta(days=14)
unique = {}
for item in all_items:
    try:
        posted = datetime.fromisoformat(item["date"].replace("Z","+00:00"))
    except Exception:
        continue
    if posted < cutoff:
        continue
    if NOISE.search(item["text"]) or NEGATIVE.search(item["text"]) or VACANCY.search(item["text"]):
        continue
    unique[item["id"]] = item

leads = sorted(unique.values(), key=lambda x:(x["score"], x["date"]), reverse=True)[:300]
best = next((x for x in leads if x["eligible"]), None)
if best:
    best["best"] = True
for x in leads:
    x["isBestAvailable"] = bool(best and x["id"] == best["id"])

os.makedirs("data", exist_ok=True)
with open(OUT,"w",encoding="utf-8") as f:
    json.dump({"updatedAt":datetime.now(timezone.utc).isoformat(),"count":len(leads),
               "bestLeadId":best["id"] if best else None,"channels":CHANNELS,
               "errors":errors,"leads":leads},f,ensure_ascii=False,indent=2)
print(f"Fetched {len(all_items)} matching posts; stored {len(leads)} recent leads; best={'yes' if best else 'no'}; errors={len(errors)}")
