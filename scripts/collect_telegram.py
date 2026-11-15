import json, os, re, hashlib
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from html import unescape
from html.parser import HTMLParser

CHANNELS = ["web_fl", "job_webdev", "webfrl", "job_developer"]
OUT = "data/leads.json"
KEYWORDS = re.compile(r"\\b(сайт|лендинг|верстк|разработ|фронтенд|frontend|html|css|javascript|\\bjs\\b|wordpress|бот|интернет-магазин|доработ|веб-прилож|web\\s?site|landing|figma)\\b", re.I)
NEGATIVE = re.compile(r"(ищу работу|ищу заказ|предлагаю услуги|моё портфолио|мое портфолио|резюме|вакансия для разработчика)", re.I)
BUDGET = re.compile(r"(?:бюджет|оплата|стоимость|цена|до|от)?\\s*([0-9][0-9\\s.,]{2,})\\s*(₽|руб(?:лей|ля)?|р\\.?|usd|\\$)", re.I)

class MessageParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.messages=[]; self.current=None; self.capture=0; self.capture_link=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs); cls=a.get("class","")
        if tag=="div" and "tgme_widget_message_wrap" in cls:
            self.current={"post":a.get("data-post",""),"text":"","date":"","links":[]}
        elif self.current is not None:
            if tag=="div" and "tgme_widget_message_text" in cls: self.capture+=1
            if tag=="time" and a.get("datetime"): self.current["date"]=a["datetime"]
            if tag=="a" and a.get("href"): self.current["links"].append(a["href"])
    def handle_endtag(self, tag):
        if self.current is not None and tag=="div" and self.capture: self.capture-=1
    def handle_data(self, data):
        if self.current is not None and self.capture: self.current["text"] += data
    def close(self):
        super().close()
        # Message boundaries are parsed by a second, robust block parser below.

def strip_tags(s):
    s=re.sub(r"<br\\s*/?>","\\n",s,flags=re.I)
    s=re.sub(r"</div>|</p>","\\n",s,flags=re.I)
    s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"[ \\t]+"," ",unescape(s)).strip()

def fetch(channel):
    url=f"https://t.me/s/{channel}"
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; PanaceaLeads/1.0)"})
    with urlopen(req,timeout=25) as r: html=r.read().decode("utf-8","replace")
    blocks=re.findall(r'<div class="tgme_widget_message_wrap[^"]*"[^>]*data-post="([^"]+)"[^>]*>(.*?)(?=<div class="tgme_widget_message_wrap|<div class="tgme_channel_bottom|$)',html,re.S)
    if not blocks:
        blocks=re.findall(r'<div class="tgme_widget_message_wrap[^>]*>(.*?)(?=<div class="tgme_widget_message_wrap|<div class="tgme_channel_bottom|$)',html,re.S)
        blocks=[(re.search(r'data-post="([^"]+)"',b).group(1) if re.search(r'data-post="([^"]+)"',b) else "",b) for b in blocks]
    items=[]
    for post, block in blocks:
        m=re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',block,re.S)
        if not m: continue
        body=strip_tags(m.group(1))
        if len(body)<35 or not KEYWORDS.search(body) or NEGATIVE.search(body): continue
        date_m=re.search(r'<time[^>]*datetime="([^"]+)"',block)
        date=date_m.group(1) if date_m else ""
        links=re.findall(r'<a[^>]+href="([^"]+)"',block)
        handles=list(dict.fromkeys(re.findall(r'(?<![\\w])@[A-Za-z0-9_]{5,}',body)))
        external=[]
        for link in links:
            mt=re.search(r'https?://t\\.me/([A-Za-z0-9_]{5,})(?:[/?#]|$)',link)
            if mt and mt.group(1).lower()!=channel.lower(): external.append("@"+mt.group(1))
        contacts=list(dict.fromkeys(handles+external))
        bm=BUDGET.search(body)
        budget=int(re.sub(r"[^0-9]","",bm.group(1))) if bm else 0
        post_url="https://t.me/"+post if post else url
        fingerprint=hashlib.sha256((post_url+"|"+body[:250]).encode()).hexdigest()
        title=next((x.strip(" -*•—") for x in body.splitlines() if len(x.strip())>8), "Заказ на разработку")[:120]
        questions=["Какой результат нужен и какие страницы/функции входят в объём?","Есть ли примеры или референсы желаемого результата?","Какой срок сдачи и есть ли промежуточные этапы?","Кто предоставляет тексты, изображения и доступы?"]
        if not budget: questions.insert(0,"Какой бюджет предусмотрен на задачу?")
        advice="Проверь объём, сроки и оплату до согласования. Не начинай работу без зафиксированного ТЗ и понятного порядка оплаты."
        if contacts: advice+=" Контакт найден в публикации — сначала уточни детали в личных сообщениях."
        else: advice+=" Прямой личный контакт в посте не обнаружен: открой оригинальную публикацию и проверь способ связи."
        items.append({"id":fingerprint,"title":title,"text":body[:5000],"channel":"@"+channel,"date":date,"url":post_url,"contacts":contacts,"budget":budget,"questions":questions,"advice":advice,"fetchedAt":datetime.now(timezone.utc).isoformat()})
    return items

all_items=[]
errors=[]
for channel in CHANNELS:
    try: all_items.extend(fetch(channel))
    except Exception as e: errors.append({"channel":channel,"error":str(e)[:240]})

old={}
if os.path.exists(OUT):
    try:
        for x in json.load(open(OUT,encoding="utf-8")).get("leads",[]): old[x["id"]]=x
    except Exception: pass
for item in all_items: old[item["id"]]=item
leads=sorted(old.values(),key=lambda x:x.get("date",""),reverse=True)[:500]
os.makedirs("data",exist_ok=True)
with open(OUT,"w",encoding="utf-8") as f:
    json.dump({"updatedAt":datetime.now(timezone.utc).isoformat(),"count":len(leads),"channels":CHANNELS,"errors":errors,"leads":leads},f,ensure_ascii=False,indent=2)
print(f"Fetched {len(all_items)} matching posts; stored {len(leads)} leads; errors={len(errors)}")
