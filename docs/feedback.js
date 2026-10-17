/* Lens It feedback pop-up. Nothing is sent from this page: "Send" opens the public GitHub feedback
   form with the answers filled in, and the visitor submits it there. No tracking, no cookies. */
(() => {
  const FORM = 'https://github.com/Wandercoil/lensit/issues/new';
  const WHO = ['Photographer / event organiser', 'Guest at an event', 'Just trying the website', 'Developer'];
  const WHERE = ['The "Try it" page on the website', 'The Windows app (LensIt.exe)', 'The guest page on my phone at an event', 'Just reading the website'];
  const RATING = ['1 - Not useful', '2 - Not really', '3 - OK', '4 - Useful', '5 - Love it'];

  const css = `
  .fb,.fb *{box-sizing:border-box}
  .fb-btn{position:fixed;right:20px;bottom:20px;z-index:60;display:flex;align-items:center;gap:8px;background:#04124c;color:#fff;border:0;border-radius:999px;padding:13px 20px;font:700 15px "Plus Jakarta Sans",system-ui,sans-serif;cursor:pointer;box-shadow:0 14px 30px -10px rgba(4,18,76,.55)}
  .fb-btn:hover{background:#0b1d66}
  .fb-back{position:fixed;inset:0;background:rgba(4,18,76,.45);z-index:70;display:flex;align-items:flex-end;justify-content:center;padding:16px}
  @media(min-width:640px){.fb-back{align-items:center}}
  .fb{background:#fff;color:#1d2030;width:100%;max-width:520px;max-height:92vh;overflow:auto;border-radius:24px;padding:24px;font-family:"Plus Jakarta Sans",system-ui,sans-serif;box-shadow:0 30px 70px -20px rgba(0,0,0,.45)}
  .fb h3{margin:0;color:#04124c;font-size:1.35rem;letter-spacing:-.02em}
  .fb .lead{margin:4px 0 16px;color:#5b606b;font-size:.92rem}
  .fb label.l{display:block;font-weight:700;color:#04124c;font-size:.9rem;margin:14px 0 6px}
  .fb select,.fb textarea{width:100%;font:inherit;font-size:.95rem;border:1.5px solid #e4e5e8;border-radius:12px;padding:10px 12px;background:#fff;color:#1d2030}
  .fb textarea{min-height:64px;resize:vertical}
  .fb select:focus,.fb textarea:focus{outline:none;border-color:#b84a06;box-shadow:0 0 0 4px rgba(184,74,6,.15)}
  .fb .stars{display:flex;gap:6px}
  .fb .stars button{width:44px;height:44px;border-radius:12px;border:1.5px solid #e4e5e8;background:#fff;font-size:1.3rem;cursor:pointer;color:#c9ccd3}
  .fb .stars button.on{color:#b84a06;border-color:#b84a06;background:#fff3ec}
  .fb .chk{display:flex;gap:10px;align-items:flex-start;margin-top:16px;font-size:.88rem;line-height:1.45;cursor:pointer}
  .fb .chk input{width:18px;height:18px;accent-color:#b84a06;flex:none;margin-top:2px}
  .fb .row{display:flex;gap:10px;justify-content:flex-end;margin-top:18px;flex-wrap:wrap}
  .fb .b{border:0;border-radius:999px;padding:12px 20px;font:700 .95rem "Plus Jakarta Sans",system-ui,sans-serif;cursor:pointer}
  .fb .b.go{background:#b84a06;color:#fff}.fb .b.go:hover{background:#9a3d05}
  .fb .b.no{background:#fff;color:#04124c;border:1.5px solid #e4e5e8}
  .fb .err{color:#b42318;font-weight:600;font-size:.88rem;margin:10px 0 0;min-height:1em}
  .fb .note{font-size:.8rem;color:#5b606b;margin:12px 0 0}
  .fb .done{text-align:center;padding:10px 0}.fb .done .big{font-size:2.6rem}
  `;
  const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);

  const btn = document.createElement('button');
  btn.className = 'fb-btn'; btn.type = 'button'; btn.innerHTML = '💬 Feedback';
  btn.setAttribute('aria-haspopup', 'dialog');
  document.body.appendChild(btn);

  const opt = list => '<option value="">Choose…</option>' + list.map(o => `<option>${o.replace(/"/g, '&quot;')}</option>`).join('');
  let rating = 0, lastFocus = null;

  function open() {
    lastFocus = document.activeElement; rating = 0;
    const back = document.createElement('div'); back.className = 'fb-back';
    back.innerHTML = `
    <div class="fb" role="dialog" aria-modal="true" aria-labelledby="fb-t">
      <div id="fb-form">
        <h3 id="fb-t">Help us make Lens It better</h3>
        <p class="lead">About a minute. Please don't include photos or anyone's personal details.</p>
        <label class="l" for="fb-who">I am a…</label><select id="fb-who">${opt(WHO)}</select>
        <label class="l" for="fb-where">Where did you use Lens It?</label><select id="fb-where">${opt(WHERE)}</select>
        <span class="l" style="display:block;font-weight:700;color:#04124c;font-size:.9rem;margin:14px 0 6px" id="fb-rl">How useful is it for you?</span>
        <div class="stars" role="radiogroup" aria-labelledby="fb-rl">${[1, 2, 3, 4, 5].map(n => `<button type="button" role="radio" aria-checked="false" aria-label="${RATING[n - 1]}" data-n="${n}">★</button>`).join('')}</div>
        <label class="l" for="fb-good">What worked well?</label><textarea id="fb-good"></textarea>
        <label class="l" for="fb-bad">What went wrong or was confusing?</label><textarea id="fb-bad" placeholder='e.g. "a sideways photo wasn&#39;t found"'></textarea>
        <label class="l" for="fb-wish">What should Lens It do next?</label><textarea id="fb-wish"></textarea>
        <label class="chk"><input type="checkbox" id="fb-ok"><span>I haven't included any photos, faces or other people's personal details.</span></label>
        <p class="err" id="fb-err"></p>
        <div class="row"><button class="b no" type="button" id="fb-cancel">Cancel</button><button class="b go" type="button" id="fb-send">Send feedback →</button></div>
        <p class="note">"Send" opens our public feedback page on GitHub with your answers filled in. Press <b>Submit</b> there (a free GitHub account is needed). Nothing is sent from this page.</p>
      </div>
      <div class="done" id="fb-done" hidden>
        <div class="big">🙏</div><h3>Thank you!</h3>
        <p class="lead">Your answers are open in a new tab on GitHub. Press <b>Submit new issue</b> there to send them.</p>
        <div class="row" style="justify-content:center"><button class="b go" type="button" id="fb-close">Close</button></div>
      </div>
    </div>`;
    document.body.appendChild(back);
    const $ = id => back.querySelector('#' + id);
    const close = () => { back.remove(); document.removeEventListener('keydown', onKey); lastFocus && lastFocus.focus(); };
    const onKey = e => { if (e.key === 'Escape') close(); };
    document.addEventListener('keydown', onKey);
    back.addEventListener('click', e => { if (e.target === back) close(); });
    back.querySelectorAll('.stars button').forEach(b => b.onclick = () => {
      rating = +b.dataset.n;
      back.querySelectorAll('.stars button').forEach(x => { const on = +x.dataset.n <= rating; x.classList.toggle('on', on); x.setAttribute('aria-checked', +x.dataset.n === rating); });
    });
    back.addEventListener('change', () => { $('fb-err').textContent = ''; });
    $('fb-cancel').onclick = close; $('fb-close').onclick = close;
    $('fb-send').onclick = () => {
      const err = m => { $('fb-err').textContent = m; };
      if (!$('fb-who').value) return err('Please choose who you are.');
      if (!$('fb-where').value) return err('Please choose where you used Lens It.');
      if (!rating) return err('Please give a star rating.');
      if (!$('fb-ok').checked) return err('Please tick the privacy box.');
      const q = new URLSearchParams({
        template: 'feedback.yml', title: `[Feedback] ${RATING[rating - 1].slice(4)} · ${$('fb-where').value}`.slice(0, 120),
        who: $('fb-who').value, where: $('fb-where').value, rating: RATING[rating - 1],
        good: $('fb-good').value.slice(0, 2000), bad: $('fb-bad').value.slice(0, 2000), wish: $('fb-wish').value.slice(0, 2000),
      });
      window.open(`${FORM}?${q}`, '_blank', 'noopener');
      $('fb-form').hidden = true; $('fb-done').hidden = false; $('fb-close').focus();
    };
    $('fb-who').focus();
  }
  btn.onclick = open;
  // Any link with data-feedback (e.g. in the footer or FAQ) opens the pop-up instead of navigating.
  document.addEventListener('click', e => { const a = e.target.closest('[data-feedback]'); if (a) { e.preventDefault(); open(); } });
})();
