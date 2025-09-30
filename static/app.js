// static/app.js
const usrEl = document.getElementById('usr')
const txtEl = document.getElementById('txt')
const outEl = document.getElementById('out')
const histEl = document.getElementById('hist')
const fEl = document.getElementById('f')
document.getElementById('ask').onclick = async () => {
  const u = usrEl.value||'guest'
  const t = txtEl.value||''
  outEl.textContent = "Thinking..."
  const form = new FormData()
  form.append('usr', u)
  form.append('txt', t)
  form.append('ocr', '')
  const res = await fetch('/api/ask', {method:'POST', body: form})
  const j = await res.json()
  if(j.ok) outEl.textContent = j.ans
  else outEl.textContent = "Err"
  loadHist(u)
}
document.getElementById('upbtn').onclick = ()=> fEl.click()
fEl.onchange = async (e)=>{
  const f = e.target.files[0]
  if(!f) return
  const fd = new FormData()
  fd.append('file', f)
  outEl.textContent = "OCR..."
  const r = await fetch('/api/ocr', {method:'POST', body: fd})
  const j = await r.json()
  if(j.ok){
    txtEl.value = (txtEl.value? txtEl.value + "\n\n" : "") + j.txt
    outEl.textContent = "OCR done. Paste/edit & Ask AI."
  } else outEl.textContent = "OCR err: " + j.err
}
async function loadHist(u='guest'){
  const r = await fetch(`/api/history?usr=${encodeURIComponent(u)}`)
  const j = await r.json()
  histEl.innerHTML = ''
  if(j.ok){
    j.rows.forEach(rw=>{
      const li = document.createElement('li')
      li.innerHTML = `<b>${new Date(rw.ts).toLocaleString()}</b>: ${escapeHtml(rw.q).slice(0,80)}<br/><small>${escapeHtml(rw.ai).slice(0,120)}</small>`
      histEl.appendChild(li)
    })
  }
}
function escapeHtml(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;') }
window.onload = ()=> loadHist(usrEl.value||'guest')
