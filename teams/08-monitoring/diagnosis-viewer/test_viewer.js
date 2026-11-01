// Exercise the actual viewer script using a minimal DOM. Browser layout and
// Kannada font shaping still need the manual demo checks in README.md.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor() { this.value=''; this.hidden=false; this.textContent=''; this.attributes={}; this.previews=[]; }
  set innerHTML(value) {
    this.html=value;
    this.previews=[...value.matchAll(/data-preview="(\d+)"/g)].map(m=>{
      const el=new Element();el.dataset={preview:m[1]};return el;
    });
  }
  get innerHTML() { return this.html||''; }
  setAttribute(key,value) { this.attributes[key]=value; }
  querySelectorAll(selector) { return selector==='[data-preview]'?this.previews:[]; }
  querySelector(selector) {
    if(selector==='[data-candidate-start]'&&this.innerHTML.includes('data-candidate-start')){
      this.focusTarget=new Element();return this.focusTarget;
    }
    return null;
  }
  scrollIntoView(options) { this.scrollOptions=options; }
  focus(options) { this.focusOptions=options; }
  append() {}
}

async function main() {
  const fixture=JSON.parse(fs.readFileSync(0,'utf8'));
  const html=fs.readFileSync(path.join(__dirname,'viewer.html'),'utf8');
  const script=html.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/\binit\(\);\s*$/, '');
  const elements=new Map();
  const element=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const sandbox={fixture,console,URL,AbortController,
    localStorage:{setItem(){},getItem(){return null;}},
    document:{getElementById:element,querySelector:()=>null,querySelectorAll:()=>[],createElement:()=>new Element()},
    fetch:()=>{throw new Error('Unexpected network request');}
  };
  const context=vm.createContext(sandbox);
  const run=code=>vm.runInContext(code,context);
  run(script);
  run(`D=fixture.map((f,i)=>({i,doc_id:'synthetic-'+i,text:f.text,label:null}));`);
  element('text-mode').value='visible';

  run('cur=0;inspection=fixture[0].inspection;renderText();');
  const visible=element('text').innerHTML;
  // Each marker has its own tooltip span. Check the displayed sequence
  // independently of those HTML wrappers (source text is HTML-escaped).
  const visibleContent=visible.replace(/<[^>]*>/g,'');
  assert.ok(visibleContent.startsWith('@0⟦SPACE⟧⟦SPACE⟧'));
  assert.ok(visibleContent.includes('⟦TAB⟧'));
  assert.ok(visibleContent.includes('⟦CR⟧⟦LF⟧\n'));
  assert.ok(visible.endsWith(`<span class="ln">@${Array.from(fixture[0].text).length}</span>`));
  element('text-mode').value='original';run('renderText();');
  assert.equal(element('text').textContent,fixture[0].text);

  element('ev').value='unsaved evidence';
  element('hx').value='unsaved hex';
  run('toggleHex();');
  assert.equal(element('ev').value,'unsaved evidence');
  assert.equal(element('hx').value,'unsaved hex');
  assert.equal(element('scan').hidden,false);
  assert.equal(element('toggle-hex').attributes['aria-expanded'],'true');
  assert.match(element('scan').textContent,/U\+0020\s+SPACE/);
  assert.match(element('scan').textContent,/U\+000A\s+LINE FEED/);
  assert.ok(element('scan').textContent.includes("'\\n'"));
  assert.ok(element('scan').textContent.includes('[Cc]'));
  element('unicode-start').value='1';element('unicode-end').value='4';
  run('showUnicodeRange();');
  assert.ok(element('scan').textContent.includes('range [1, 4)'));
  assert.equal(element('scan').textContent.split('\n').length,4);
  assert.ok(element('scan').textContent.split('\n')[1].startsWith('     1'));
  assert.equal(element('ev').value,'unsaved evidence');
  element('unicode-start').value='4';element('unicode-end').value='1';run('showUnicodeRange();');
  assert.ok(element('range-status').textContent.includes('start ≤ end'));
  element('unicode-start').value='1.5';run('showUnicodeRange();');
  assert.ok(element('range-status').textContent.includes('integer'));
  run('inventoryRange=null;');

  element('text-mode').value='visible';
  run(`cur=2;inspection=fixture[2].inspection;D[2].label={...EMPTY,evidence:'offset 3 "ಮ <script>"'};renderText();`);
  const astral=element('text').innerHTML;
  const astralContent=astral.replace(/<[^>]*>/g,'');
  assert.ok(astralContent.includes('@3▸ಮ'));
  assert.ok(astral.includes('😀'));
  assert.ok(astralContent.includes('&lt;script&gt;'));
  assert.ok(astralContent.includes('&lt;|im_start|&gt;'));
  run('renderAudit();');
  assert.ok(element('audit-result').innerHTML.includes('ZERO WIDTH SPACE'));
  assert.ok(element('audit-result').innerHTML.includes('occurrence(s), first at'));
  assert.ok(element('audit-result').innerHTML.includes('Jump ['));
  assert.ok(!astral.includes('<script>'));
  assert.ok(!astral.includes('\ud83d<')); // never split the emoji's surrogate pair
  for(const marker of ['U+0000','ZWSP','BOM','SHY','RLO','PDI','COMBINING GRAPHEME JOINER','VARIATION SELECTOR-16'])
    assert.ok(astral.includes(marker),marker);

  run('C={A2:"Control characters",G2:"Lost joiners",F1:"Personal data"};renderCandidates();');
  assert.ok(element('candidates').innerHTML.includes('A2'));
  assert.ok(element('candidates').innerHTML.includes('Jump ['));
  assert.ok(element('candidate-status').textContent.includes('not confirmed diseases'));
  assert.ok(element('manual-list').innerHTML.includes('G2'));
  assert.ok(element('manual-list').innerHTML.includes('Absence of ZWJ/ZWNJ alone proves nothing.'));
  element('ev').value='draft before inspecting';element('hx').value='draft hex';
  run('jumpToCandidate(-1,0);');assert.equal(run('candidateFocus'),null);
  const target=fixture[2].inspection.findings.find(f=>f.code==='A2').matches[0];
  run(`jumpToCandidate(${target.start},${target.end});`);
  assert.ok(element('text').innerHTML.includes(`title="candidate offset ${target.start}"`));
  assert.ok(element('text').focusTarget.scrollOptions);
  assert.ok(element('text').focusTarget.focusOptions);
  assert.equal(element('ev').value,'draft before inspecting');
  assert.equal(element('hx').value,'draft hex');
  assert.equal(run('Object.keys(R).length'),0);

  run('cur=1;inspection=fixture[1].inspection;renderText();renderNormalization();');
  assert.match(element('text').innerHTML,/class="hid neutral"[^>]*valid Indic character[^>]*>⟦ZWJ⟧/);
  assert.match(element('text').innerHTML,/class="hid neutral"[^>]*valid Indic character[^>]*>⟦ZWNJ⟧/);
  const normalization=element('normalization-result');
  assert.ok(normalization.innerHTML.includes('Compatibility changes beyond NFC'));
  assert.ok(normalization.innerHTML.includes('NFC baseline offsets'));
  assert.ok(normalization.innerHTML.includes('KANNADA VOWEL SIGN O'));
  assert.equal(normalization.previews[0].textContent,fixture[1].inspection.nfc.text);

  // Use the actual render() path to check code-point metadata and preservation
  // of CRLF in normalized preview text nodes.
  run('cur=0;inspection=fixture[0].inspection;render();');
  assert.ok(element('meta').textContent.endsWith(`${Array.from(fixture[0].text).length} code points`));
  assert.equal(normalization.previews[0].textContent,fixture[0].text);
  run('cur=2;inspection=fixture[2].inspection;render();');
  assert.ok(element('meta').textContent.endsWith(`${Array.from(fixture[2].text).length} code points`));

  run('cur=3;inspection=fixture[3].inspection;renderInventory();');
  const lines=element('scan').textContent.split('\n');
  assert.equal(lines.length,Array.from(fixture[3].text).length+1);
  assert.ok(lines.at(-1).startsWith(String(Array.from(fixture[3].text).length-1).padStart(6)));
  assert.ok(lines.at(-1).endsWith('LINE FEED  [Cc]'));
  element('ev').value='before row jump';
  run('openRow("0");');assert.equal(run('cur'),3);
  run('openRow("99999");');assert.equal(run('cur'),3);
  run('inspection=fixture[1].inspection;openRow("2");');
  assert.equal(run('cur'),1);
  assert.equal(element('row-number').value,'2');
  assert.ok(element('meta').textContent.includes('row 2/'));
  run('cur=4;inspection=fixture[4].inspection;renderCandidates();');
  // The standalone test fixture has no pack context; its manual guidance must
  // explicitly say that H1 was not automatically checked.
  assert.ok(!element('checked-codes').textContent.includes('H1'));
  run('cur=0;inspection={...fixture[0].inspection,findings:[]};renderCandidates();');
  assert.ok(element('candidate-status').textContent.includes('Continue full-document and manual checks.'));

  // A slow inspection must never replace a newer document or its form edits.
  const pending=[];
  sandbox.fetch=(url,options)=>new Promise(resolve=>pending.push({url,options,resolve}));
  run('inspection=null;cur=0;');const first=run('loadInspection(D[0]);');
  run('cur=1;');const second=run('loadInspection(D[1]);');
  assert.equal(pending[0].options.signal.aborted,true);
  pending[1].resolve({ok:true,json:async()=>fixture[1].inspection});await second;
  pending[0].resolve({ok:true,json:async()=>fixture[0].inspection});await first;
  assert.equal(run('inspection.i'),1);
  element('ev').value='draft during fetch';
  run('cur=2;');const third=run('loadInspection(D[2]);');
  run('cur=1;');await run('loadInspection(D[1]);');
  assert.equal(pending[2].options.signal.aborted,true);
  pending[2].resolve({ok:true,json:async()=>fixture[2].inspection});await third;
  assert.equal(run('inspection.i'),1);
  assert.equal(element('ev').value,'draft during fetch');

  // Exercise saveMine itself: descriptive D3/H3 labels may accompany clean,
  // while adding any other code must still prevent a save.
  let selectedCodes=[];
  sandbox.document.querySelector=selector=>({value:selector==='[name=vd]:checked'?'clean':'full'});
  sandbox.document.querySelectorAll=selector=>selector==='#codes input:checked'?selectedCodes.map(value=>({value})):[];
  sandbox.savedRows=[];
  run('post=r=>{savedRows.push(r);return Promise.resolve();};go=()=>{};cur=0;');
  for(const codes of [[],['D3'],['H3'],['D3','H3'],['H3','D3']]){
    selectedCodes=codes;const before=sandbox.savedRows.length;run('saveMine();');
    assert.equal(sandbox.savedRows.length,before+1);
    assert.equal(sandbox.savedRows.at(-1).verdict,'clean');
    assert.equal(sandbox.savedRows.at(-1).diseases,codes.join(';'));
  }
  for(const codes of [['A1'],['D3','A1'],['H3','C2'],['D3','H3','A4']]){
    selectedCodes=codes;const before=sandbox.savedRows.length;run('saveMine();');
    assert.equal(sandbox.savedRows.length,before);
    assert.ok(element('st').textContent.includes('clean allows only D3 and H3'));
  }
  console.log('Frontend character, offset, draft, escaping and request-race checks passed.');
}

main().catch(error=>{console.error(error);process.exitCode=1;});
