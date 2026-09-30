const form=document.querySelector("#reading-form"),tabs=[...document.querySelectorAll("[role=tab]")],status=document.querySelector("#reading-status"),target=document.querySelector("#representation"),back=document.querySelector("#back-button");
let bundle=null,active="astrology";
function setStatus(message,loading=false){target.hidden=true;status.hidden=false;status.textContent=message;status.classList.toggle("is-loading",loading)}
function render(){
  if(!bundle)return;
  const visual=bundle.systems?.[active]?.visual?.html;
  // This page never rebuilds charts in browser CSS/JS. It displays only the
  // corresponding server-rendered visual produced by the canonical renderer.
  if(typeof visual!=="string"||!visual.trim()){setStatus("La representación solicitada no está disponible.");return}
  status.hidden=true;target.hidden=false;
  const frame=document.createElement("iframe");
  frame.title="Representación interna DharmaCodex";
  frame.sandbox="allow-same-origin";
  frame.srcdoc=visual;
  target.replaceChildren(frame);
}
tabs.forEach(tab=>tab.addEventListener("click",()=>{active=tab.dataset.system;tabs.forEach(item=>item.setAttribute("aria-selected",String(item===tab)));render()}));
form.addEventListener("submit",async event=>{event.preventDefault();const input=Object.fromEntries(new FormData(form));input.latitude=Number(input.latitude);input.longitude=Number(input.longitude);setStatus("Generando lectura…",true);try{const response=await fetch("/internal/api/reading",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(input),credentials:"same-origin"});if(!response.ok)throw new Error("READING_UNAVAILABLE");bundle=await response.json();render()}catch{setStatus("La lectura no puede procesarse ahora. Verifica el contexto e inténtalo de nuevo.")}});
back.addEventListener("click",()=>history.length>1?history.back():location.assign("../../index.html"));
