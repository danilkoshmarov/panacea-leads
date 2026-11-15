(() => {
  const KEY = "panacea_leads_v021";
  const statuses = [
    ["new","Новые"],["contacted","Связались"],["negotiation","Переговоры"],["won","Выиграно"],["lost","Проиграно"]
  ];
  let orders = load();
  const $ = (id) => document.getElementById(id);
  const money = (n) => new Intl.NumberFormat("ru-RU").format(Number(n)||0) + " ₽";
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  function load(){try{const v=JSON.parse(localStorage.getItem(KEY)||"[]");return Array.isArray(v)?v:[]}catch{return []}}
  function save(){localStorage.setItem(KEY,JSON.stringify(orders));render()}
  function toast(msg){const t=$("toast");t.textContent=msg;t.classList.add("show");clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.classList.remove("show"),2200)}
  function statusName(s){return statuses.find(x=>x[0]===s)?.[1]||"Новый"}
  function card(o){return `<div class="order"><div class="order-main"><strong>${esc(o.title)}</strong><p>${esc(o.description||o.contact||"Описание не добавлено")}</p></div><span class="badge ${o.status}">${statusName(o.status)}</span><div class="order-meta"><b>${money(o.budget)}</b><small>${esc(o.source||"Источник не указан")}</small></div><div class="row-actions"><button class="small" data-fav="${o.id}" title="Избранное">${o.favorite?"★":"☆"}</button><button class="small" data-edit="${o.id}">Изменить</button><button class="small" data-delete="${o.id}">✕</button></div></div>`}
  function empty(msg="Пока здесь пусто."){return `<div class="empty">${msg}</div>`}
  function render(){
    $("nav-count").textContent=orders.length;
    const total=orders.length, fresh=orders.filter(o=>o.status==="new").length, work=orders.filter(o=>["contacted","negotiation"].includes(o.status)).length, budget=orders.reduce((a,o)=>a+(Number(o.budget)||0),0);
    $("s-total").textContent=total;$("s-new").textContent=fresh;$("s-work").textContent=work;$("s-budget").textContent=money(budget);
    const recent=[...orders].sort((a,b)=>b.created-a.created).slice(0,5);
    $("recent-list").innerHTML=recent.length?recent.map(card).join(""):empty("Заказов пока нет. Добавь первый — и начни вести свою базу.");
    const q=($("search").value||"").toLowerCase(), st=$("filter-status").value, sort=$("sort").value;
    let list=orders.filter(o=>[o.title,o.description,o.contact,o.source].join(" ").toLowerCase().includes(q)&&(!st||o.status===st));
    list.sort(sort==="budget"?(a,b)=>(b.budget||0)-(a.budget||0):sort==="oldest"?(a,b)=>a.created-b.created:(a,b)=>b.created-a.created);
    $("orders-list").innerHTML=list.length?list.map(card).join(""):empty("Ничего не найдено. Измени фильтр или добавь заказ.");
    const fav=orders.filter(o=>o.favorite);$("favorites-list").innerHTML=fav.length?fav.map(card).join(""):empty("В избранном пока нет заказов.");
    $("crm-board").innerHTML=statuses.map(([key,label])=>{const rows=orders.filter(o=>o.status===key);return `<div class="crm-col"><h3>${label}<span>${rows.length}</span></h3>${rows.map(o=>`<div class="crm-card" data-edit="${o.id}"><b>${esc(o.title)}</b><small>${money(o.budget)}</small></div>`).join("")||'<div class="empty">Пусто</div>'}</div>`}).join("");
    const won=orders.filter(o=>o.status==="won").length, avg=total?Math.round(budget/total):0, closed=orders.filter(o=>["won","lost"].includes(o.status)).length;
    $("a-total").textContent=total;$("a-average").textContent=money(avg);$("a-won").textContent=won;$("a-rate").textContent=(closed?Math.round(won/closed*100):0)+"%";
    $("bars").innerHTML=statuses.map(([key,label])=>{const n=orders.filter(o=>o.status===key).length;return `<div class="bar-row"><span>${label}</span><div class="bar-track"><div class="bar-fill" style="width:${total?n/total*100:0}%"></div></div><b>${n}</b></div>`}).join("");
  }
  function showPage(page){
    document.querySelectorAll(".page").forEach(p=>p.classList.toggle("active",p.id==="page-"+page));
    document.querySelectorAll(".nav").forEach(b=>b.classList.toggle("active",b.dataset.page===page));
    $("crumb").textContent=({overview:"Обзор",orders:"Все заказы",crm:"CRM",favorites:"Избранное",sources:"Источники",analytics:"Аналитика",settings:"Настройки"})[page]||"Обзор";
    $("sidebar").classList.remove("open");
  }
  function openForm(id){
    const o=orders.find(x=>x.id===id);
    $("order-form").reset();$("edit-id").value=o?.id||"";
    $("modal-title").textContent=o?"Редактировать заказ":"Новый заказ";
    $("f-title").value=o?.title||"";$("f-budget").value=o?.budget??"";$("f-source").value=o?.source||"";
    $("f-contact").value=o?.contact||"";$("f-description").value=o?.description||"";
    $("f-status").value=o?.status||"new";$("f-date").value=o?.date||"";
    $("order-modal").showModal();
  }
  document.addEventListener("click",e=>{
    const page=e.target.closest("[data-page]")?.dataset.page||e.target.closest("[data-go]")?.dataset.go;
    if(page){showPage(page);return}
    if(e.target.closest("[data-add]")){openForm();return}
    const edit=e.target.closest("[data-edit]");if(edit){openForm(edit.dataset.edit);return}
    const fav=e.target.closest("[data-fav]");if(fav){const o=orders.find(x=>x.id===fav.dataset.fav);if(o){o.favorite=!o.favorite;save();toast(o.favorite?"Добавлено в избранное":"Убрано из избранного")}return}
    const del=e.target.closest("[data-delete]");if(del){const o=orders.find(x=>x.id===del.dataset.delete);if(o&&confirm("Удалить заказ «"+o.title+"»?")){orders=orders.filter(x=>x.id!==o.id);save();toast("Заказ удалён")}return}
  });
  $("order-form").addEventListener("submit",e=>{
    e.preventDefault();const id=$("edit-id").value;
    const data={title:$("f-title").value.trim(),budget:Number($("f-budget").value)||0,source:$("f-source").value.trim(),contact:$("f-contact").value.trim(),description:$("f-description").value.trim(),status:$("f-status").value,date:$("f-date").value};
    if(id){const o=orders.find(x=>x.id===id);Object.assign(o,data)}else{orders.push({...data,id:crypto.randomUUID(),favorite:false,created:Date.now()})}
    $("order-modal").close();save();toast(id?"Изменения сохранены":"Заказ добавлен");
  });
  $("close-modal").onclick=$("cancel-modal").onclick=()=>$("order-modal").close();
  ["search","filter-status","sort"].forEach(id=>$(id).addEventListener(id==="search"?"input":"change",render));
  $("export").onclick=()=>{const blob=new Blob([JSON.stringify({version:"0.2.1",exportedAt:new Date().toISOString(),orders},null,2)],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="panacea-leads-backup.json";a.click();URL.revokeObjectURL(a.href);toast("Резервная копия скачана")};
  $("import").onchange=async e=>{const file=e.target.files[0];if(!file)return;try{const data=JSON.parse(await file.text());const incoming=Array.isArray(data)?data:data.orders;if(!Array.isArray(incoming))throw Error("bad format");if(confirm("Импорт заменит текущую базу. Продолжить?")){orders=incoming.map(o=>({...o,id:o.id||crypto.randomUUID(),created:o.created||Date.now(),favorite:!!o.favorite}));save();toast("Данные импортированы")}}catch{alert("Не удалось прочитать файл. Выбери резервную копию Panacea Leads JSON.")}e.target.value=""};
  $("clear").onclick=()=>{if(confirm("Точно удалить все заказы? Это действие нельзя отменить.")){orders=[];save();toast("База очищена")}};
  $("tg-import").addEventListener("click",()=>{
    const raw=$("tg-text").value.trim(), link=$("tg-link").value.trim(), source=$("tg-source").value;
    if(raw.length<25){$("tg-result").textContent="Вставь полный текст объявления (минимум 25 символов).";return;}
    if(link&&!/^https?:\/\//i.test(link)){$("tg-result").textContent="Ссылка должна начинаться с http:// или https://.";return;}
    const lines=raw.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
    const title=(lines.find(x=>x.length>8&&!/^https?:\/\//i.test(x)&&!/^@[\w]+$/.test(x))||lines[0]||"Заказ из Telegram").slice(0,120);
    const budgetMatch=raw.match(/(?:бюджет|оплата|стоимость|цена|до|от)?\s*(\d[\d\s.,]{2,})\s*(₽|руб(?:лей|ля)?|р\.?|\$|usd)/i);
    const budget=budgetMatch?Number(budgetMatch[1].replace(/[\s.,]/g,"")):0;
    const handles=[...raw.matchAll(/@[a-zA-Z0-9_]{5,}/g)].map(x=>x[0]);
    const contact=link||handles.find(x=>x!==source)||"Контакт не найден в тексте";
    const id=crypto.randomUUID();
    orders.push({id,title,budget,source,contact,description:raw.slice(0,2000),status:"new",date:new Date().toISOString().slice(0,10),created:Date.now(),favorite:false,originLink:link,importMethod:"user_paste",needsReview:true});
    save();$("tg-result").textContent="Добавлено. Проверь название, бюджет и контакт перед откликом.";$("tg-text").value="";$("tg-link").value="";toast("Публикация добавлена в CRM");
  });
  $("menu-btn").onclick=()=>$("sidebar").classList.toggle("open");
  render();
})();