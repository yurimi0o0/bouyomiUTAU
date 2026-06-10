const $ = id => document.getElementById(id);
const voicebank = $('voicebank'), text = $('text'), status = $('voiceStatus'), error = $('error');
voicebank.value = localStorage.getItem('voicebank') || '';
text.addEventListener('input', () => $('count').textContent = [...text.value].length);
$('speed').addEventListener('input', e => $('speedOut').textContent = Number(e.target.value).toFixed(1) + '×');
$('check').addEventListener('click', async () => {
  status.className = 'notice'; status.textContent = '音源を確認しています…'; error.textContent = '';
  try { const r = await fetch('/api/inspect?voicebank=' + encodeURIComponent(voicebank.value)); const d = await r.json(); if (!r.ok || !d.ready) throw new Error(d.error || 'oto.ini が見つかりません'); status.className = 'notice ok'; status.textContent = `✓ ${d.name} — ${d.sounds} 個のエイリアスを読み込みました`; localStorage.setItem('voicebank', voicebank.value); }
  catch (e) { status.textContent = '音源を確認できませんでした'; error.textContent = e.message; }
});
$('talk').addEventListener('click', async () => {
  const button = $('talk'); error.textContent = '';
  if (!voicebank.value || !text.value) { error.textContent = '音源フォルダーと、しゃべらせる言葉を入力してください。'; return; }
  button.disabled = true; button.textContent = '音声をつないでいます…';
  try { const q = new URLSearchParams({voicebank: voicebank.value, text: text.value, speed: $('speed').value}); const r = await fetch('/api/talk?' + q); if (!r.ok) { const d = await r.json(); throw new Error(d.error); } const audio = $('audio'); audio.src = URL.createObjectURL(await r.blob()); audio.style.display = 'block'; await audio.play(); localStorage.setItem('voicebank', voicebank.value); }
  catch (e) { error.textContent = e.message; }
  finally { button.disabled = false; button.innerHTML = '<span>▶</span> この声でしゃべる'; }
});
