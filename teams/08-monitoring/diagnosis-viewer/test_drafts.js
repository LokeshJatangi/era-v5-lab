// Exercise draft persistence and the real save/navigation functions with a
// stateful form model, shared browser storage, and controllable save responses.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const fixture=JSON.parse(fs.readFileSync(0,'utf8'));
const html=fs.readFileSync(path.join(__dirname,'viewer.html'),'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/\binit\(\);\s*$/,'');
const starting={read:'full',verdict:'fix',diseases:'A1',evidence:'starting evidence',hex:'U+200B',note:'starting note'};

class Element {
  constructor(){this.value='';this.textContent='';this.hidden=false;this.innerHTML='';}
  setAttribute(){}
  querySelectorAll(){return [];}
  querySelector(){return null;}
  append(){}
}

async function app(storage,pack='pack-a',saved={},options={}){
  const elements=new Map();
  const el=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const radio={rd:['full','partial'].map(value=>({value,checked:false})),
               vd:['clean','fix','drop'].map(value=>({value,checked:false}))};
  const codes=['A1','A6','D3','D4','H3','C1','C2','C5','E3','F1','G1','G2'].map(value=>({value,checked:false}));
  const listeners={};
  const state={saveMode:'ok',pending:[],posts:[],el,radio,codes};
  const docs=fixture.map((f,i)=>({i,doc_id:'synthetic-'+i,text:f.text,url:'',
    label:i===0?{doc_id:'synthetic-0',...starting}:null}));
  const sandbox={console,URL,AbortController,
    localStorage:{
      getItem:key=>storage.values.get(key)??null,
      setItem:(key,value)=>{if(storage.failWrites)throw new Error('Storage full');storage.values.set(key,String(value));},
      removeItem:key=>{if(storage.failWrites)throw new Error('Storage blocked');storage.values.delete(key);}
    },
    window:{addEventListener:(name,handler)=>{listeners[name]=handler;}},
    document:{getElementById:el,createElement:()=>new Element(),
      querySelector:selector=>{
        const box=selector.match(/^#codes input\[value="([^"]+)"\]$/);
        if(box)return codes.find(input=>input.value===box[1])||null;
        const value=selector.match(/^\[name=(rd|vd)\]\[value="([^"]+)"\]$/);
        if(value)return radio[value[1]].find(input=>input.value===value[2])||null;
        const name=selector.includes('name=rd')?'rd':'vd';return radio[name].find(input=>input.checked)||null;
      },
      querySelectorAll:selector=>{
        if(selector==='[name=rd]')return radio.rd;if(selector==='[name=vd]')return radio.vd;
        if(selector==='#codes input')return codes;if(selector==='#codes input:checked')return codes.filter(input=>input.checked);
        return [];
      }
    },
    fetch:async(url,requestOptions)=>{
      if(url==='data.json')return {ok:true,json:async()=>({pack:'same-name.parquet',pack_key:pack,codes:{A1:'Invisible junk',A6:'Mixed script',D3:'Mixed language',D4:'Bad translation',H3:'Other-source content',C1:'Boilerplate',C2:'Repeated lines',C5:'Teaser list',E3:'Secrets',F1:'Personal data',G1:'Split word',G2:'Lost joiner'},docs,...options})};
      if(url==='reviews')return {ok:true,json:async()=>({...saved})};
      if(url.startsWith('inspect?i='))return {ok:true,json:async()=>fixture[+url.split('=')[1]].inspection};
      if(url==='save'){
        const row=JSON.parse(requestOptions.body);state.posts.push(row);
        const success=()=>{saved[row.doc_id]=row;return {ok:true,json:async()=>({reviewed:Object.keys(saved).length})};};
        if(state.saveMode==='fail')return {ok:false,status:500};
        if(state.saveMode==='delay')return new Promise(resolve=>state.pending.push(()=>resolve(success())));
        return success();
      }
      throw new Error('Unexpected URL '+url);
    }
  };
  const context=vm.createContext(sandbox);state.run=source=>vm.runInContext(source,context);
  state.choose=(name,value)=>radio[name].forEach(input=>{input.checked=input.value===value;});
  state.chooseCodes=values=>codes.forEach(input=>{input.checked=values.includes(input.value);});
  state.fields=()=>JSON.parse(state.run('JSON.stringify(readForm())'));
  state.key=id=>state.run(`draftKey(${JSON.stringify(id)})`);
  state.input=()=>el('side').oninput();
  state.pagehide=()=>listeners.pagehide();
  state.submit=()=>state.run(`post({doc_id:D[cur].doc_id,...readForm(),
    evidence:$('ev').value.trim(),hex:$('hx').value.trim(),note:$('nt').value.trim()},readForm())`);
  state.run(script);el('flt').value='all';el('text-mode').value='visible';
  await state.run('init()');return state;
}

async function main(){
  const rowStorage={values:new Map([['cur:row-start','4']]),failWrites:false};
  const rowStart=await app(rowStorage,'row-start',{}, {initial_index:1,audit_open:true});
  assert.equal(rowStart.run('cur'),1);assert.equal(rowStart.el('audit').open,true);
  rowStart.el('ev').value='retain while jumping by row';rowStart.input();
  rowStart.run('openRow("3");');rowStart.run('openRow("2");');
  assert.equal(rowStart.el('ev').value,'retain while jumping by row');
  assert.equal(rowStart.posts.length,0);
  const storage={values:new Map(),failWrites:false},saved={};
  let a=await app(storage,'pack-a',saved);
  a.el('ev').value='  Kannada evidence\nsecond line  ';a.el('hx').value=' U+200B  ';a.el('nt').value='  first row note  ';
  a.choose('rd','partial');a.choose('vd','drop');a.chooseCodes(['A1','D3']);a.input();
  const first=a.fields();
  assert.deepEqual(JSON.parse(storage.values.get(a.key('synthetic-0'))).fields,first);
  assert.match(a.el('draft-status').textContent,/saved locally/);
  assert.equal(a.posts.length,0);
  a.run('go(1)');assert.equal(a.el('ev').value,'');
  a.el('ev').value=' row one evidence ';a.el('nt').value='row one note';
  a.choose('vd','clean');a.chooseCodes(['D3','H3']);a.el('side').onchange();const second=a.fields();
  a.run('go(-1)');assert.deepEqual(a.fields(),first);
  a.el('list').onclick({target:{closest:()=>({dataset:{i:'1'}})}});
  assert.deepEqual(a.fields(),second);
  // Filter navigation must flush the displayed row before restoring its target.
  a.el('nt').value='new note before filtering';const changedSecond=a.fields();
  a.el('q').value='window.viewerInjected';a.el('q').oninput();
  assert.equal(a.run('cur'),2);
  a.el('q').value='';a.el('q').oninput();a.run('go(1)');assert.deepEqual(a.fields(),changedSecond);
  a.pagehide();assert.equal(a.posts.length,0);

  // New JS context, same storage and origin: recover row, raw text and selections.
  a=await app(storage,'pack-a',saved);assert.equal(a.run('cur'),1);assert.deepEqual(a.fields(),changedSecond);
  const other=await app(storage,'pack-b',saved);
  assert.equal(other.el('ev').value,starting.evidence);other.run('go(1)');assert.equal(other.el('ev').value,'');
  assert.ok(storage.values.has(a.key('synthetic-0')));

  // Successful submission clears only that row and does not recreate a draft
  // from the form's pre-save, untrimmed whitespace during auto-navigation.
  assert.equal(await a.submit(),true);
  assert.equal(storage.values.has(a.key('synthetic-1')),false);
  assert.equal(a.el('ev').value,changedSecond.evidence.trim());
  a.run('go(1);go(-1)');assert.equal(a.el('ev').value,changedSecond.evidence.trim());
  assert.equal(storage.values.has(a.key('synthetic-1')),false);
  assert.ok(storage.values.has(a.key('synthetic-0')));

  a.el('ev').value='pending edit after saved review';a.input();a.saveMode='fail';
  assert.equal(await a.submit(),false);assert.ok(storage.values.has(a.key('synthetic-1')));
  assert.match(a.el('st').textContent,/Save failed/);
  const failedReload=await app(storage,'pack-a',saved);assert.equal(failedReload.el('ev').value,'pending edit after saved review');

  // An older successful save must preserve edits made while it was pending.
  a.saveMode='delay';a.el('ev').value='submitted edit';a.input();const pending=a.submit();
  a.el('ev').value='newer unsent edit';a.input();a.pending.shift()();
  assert.equal(await pending,false);assert.equal(a.el('ev').value,'newer unsent edit');
  assert.equal(JSON.parse(storage.values.get(a.key('synthetic-1'))).fields.evidence,'newer unsent edit');
  assert.equal(saved['synthetic-1'].evidence,'submitted edit');

  // Saving row 1 while the reviewer navigates to row 2 must not move row 2 or
  // clear its draft when the row 1 response eventually arrives.
  const navigatedSave=a.submit();a.run('go(1)');a.el('ev').value='row two unsaved';a.input();
  a.pending.shift()();assert.equal(await navigatedSave,false);
  assert.equal(a.run('cur'),2);assert.equal(a.el('ev').value,'row two unsaved');
  assert.ok(storage.values.has(a.key('synthetic-2')));assert.equal(storage.values.has(a.key('synthetic-1')),false);

  // Discard is explicit and affects just the displayed document.
  const posts=a.posts.length;a.el('discard-draft').onclick();assert.equal(a.el('ev').value,'');
  assert.equal(storage.values.has(a.key('synthetic-2')),false);assert.equal(a.posts.length,posts);
  assert.ok(storage.values.has(a.key('synthetic-0')));

  // Explicit C1 evidence action adds source quotes and code-point offsets to
  // a local draft, preserves existing text/codes, and never submits a review.
  const c1Storage={values:new Map(),failWrites:false},c1=await app(c1Storage,'c1-test');
  c1.run('go(5)');await c1.run('loadInspection(D[cur])');
  c1.el('ev').value='existing evidence';c1.choose('vd','clean');c1.chooseCodes(['H3']);
  assert.ok(c1.el('candidates').innerHTML.includes('Add C1 + C5 evidence'));
  c1.el('candidates').onclick({target:{closest:selector=>selector==='[data-action="append-navigation"]'?{}:null}});
  const evidence=c1.el('ev').value;
  assert.ok(evidence.startsWith('existing evidence | '));
  assert.ok(evidence.includes('C1: "Just In Don\'t Miss!" at offset 0'));
  assert.ok(evidence.includes('C5: "- News ಕರ್ನಾಟಕದಲ್ಲಿ 573 ಕೊರೊನಾ ಸೋಂಕಿತರು ಪತ್ತೆ" at offset 20'));
  assert.equal(c1.fields().verdict,'fix');assert.ok(c1.fields().diseases.includes('C1'));
  assert.ok(c1.fields().diseases.includes('H3'));assert.ok(c1.fields().diseases.includes('C5'));assert.equal(c1.posts.length,0);
  assert.equal(JSON.parse(c1Storage.values.get(c1.key('synthetic-5'))).fields.evidence,evidence);
  c1.run('appendNavigationEvidence()');assert.equal(c1.el('ev').value,evidence);
  c1.el('ev').value='';c1.choose('vd','drop');c1.chooseCodes(['C1','F1']);c1.run('appendC1Evidence()');
  assert.ok(c1.el('ev').value.includes('C1: navigation header at offset 0'));
  assert.ok(!c1.el('ev').value.includes('573'));assert.ok(!c1.el('ev').value.includes('Just In'));
  assert.equal(c1.fields().verdict,'drop');

  const extras=await app({values:new Map(),failWrites:false},'evidence-actions');
  extras.run('go(6)');await extras.run('loadInspection(D[cur])');
  assert.ok(extras.el('candidates').innerHTML.includes('Append C2 evidence'));
  assert.ok(extras.el('candidates').innerHTML.includes('Append G1 evidence'));
  extras.el('ev').value='existing evidence';extras.el('hx').value='U+200B';
  extras.choose('vd','clean');extras.chooseCodes(['H3']);extras.run('appendFindingEvidence("G1")');
  assert.ok(extras.el('ev').value.includes('G1: ಿ at offset 2'));
  assert.equal(extras.el('hx').value,'U+200B');assert.equal(extras.fields().verdict,'fix');
  assert.ok(extras.fields().diseases.includes('H3'));
  extras.run('appendFindingEvidence("G1")');assert.equal(extras.el('hx').value,'U+200B');
  extras.el('candidates').onclick({target:{closest:selector=>selector==='[data-action="append-evidence"]'?{dataset:{code:'C2'}}:null}});
  const combined=extras.el('ev').value;
  assert.ok(combined.includes('C2: "ಮಾದರಿ ಸಾಲು" at offset 4'));
  assert.equal((combined.match(/C2:/g)||[]).length,3);
  assert.ok(combined.includes('line content occurs 3 times'));
  extras.run('appendFindingEvidence("C2")');assert.equal(extras.el('ev').value,combined);
  assert.equal(extras.posts.length,0);

  // Reader-supplied words are one-click, per-occurrence actions. Neither
  // findings nor manual selections may populate hex or submit a review.
  const wordsStorage={values:new Map(),failWrites:false};
  const words=await app(wordsStorage,'reader-word-actions');
  words.run('openRow("15")');await words.run('loadInspection(D[cur])');
  words.el('hx').value='existing hex';words.choose('vd','drop');
  words.el('candidates').onclick({target:{closest:selector=>selector==='[data-action="append-evidence"]'?
    {dataset:{code:'G2',match:'1'}}:null}});
  const onlyDownload=words.el('ev').value;
  const downloadOffset=Array.from(fixture[14].text.slice(0,fixture[14].text.indexOf('ಡೌನ್ಲೋಡ್'))).length;
  assert.equal(onlyDownload,`G2: ಡೌನ್ಲೋಡ್ at offset ${downloadOffset}`);
  assert.ok(!onlyDownload.includes('ಹಾಲ್ನಲ್ಲಿ'));assert.equal(words.el('hx').value,'existing hex');
  assert.equal(words.fields().verdict,'drop');assert.equal(words.posts.length,0);
  words.run('appendFindingEvidence("G2",1)');assert.equal(words.el('ev').value,onlyDownload);
  words.run('appendFindingEvidence("G1",0)');
  assert.ok(words.el('ev').value.includes('G1: ವಣ ್ಸುವಾಗ at offset 2'));
  assert.equal(words.el('hx').value,'existing hex');
  words.run('pickWordAt(3);appendSelection("G1")');
  assert.ok(!words.el('ev').value.includes('U+'));
  words.run('appendFindingEvidence("A6",0)');
  assert.ok(words.el('ev').value.includes('A6: process ಾಯಾಚಿತ್ರದೊಂದಿಗೆ at offset '));
  const wordDraft=words.el('ev').value;
  words.run('openRow("1");openDocId("synthetic-14")');
  assert.equal(words.el('ev').value,wordDraft);assert.equal(words.posts.length,0);
  assert.ok(words.el('csv-preview').value.startsWith('doc_id,read,verdict,diseases,evidence,hex,note\nsynthetic-14,'));
  words.run('openDocId("synthetic-0")');await words.run('loadInspection(D[cur])');
  words.run('pickWordAt(3);appendSelection("G2")');
  assert.ok(words.el('ev').value.includes('G2: ಕನ್ನಡ at offset 2'));
  assert.equal(words.el('hx').value,'U+200B');assert.equal(words.posts.length,0);
  // The D4 toolbar button accepts a reader-selected phrase without requiring
  // an automatic finding, adds no hex, and keeps the review as a draft.
  words.choose('vd','clean');
  words.run('setSelectionRange(2,2+Array.from("ಕನ್ನಡ\\tಪಠ್ಯ").length)');
  words.el('selection-d4').onclick();
  const d4Evidence=words.el('ev').value;
  assert.ok(d4Evidence.includes('D4: ಕನ್ನಡ\tಪಠ್ಯ at offset 2'));
  assert.ok(words.fields().diseases.split(';').includes('D4'));
  assert.ok(words.fields().diseases.split(';').includes('G2'));
  assert.equal(words.fields().verdict,'fix');assert.equal(words.el('hx').value,'U+200B');
  assert.equal(words.posts.length,0);
  words.el('selection-d4').onclick();assert.equal(words.el('ev').value,d4Evidence);
  // C1 can also be marked manually when no automatic C1 candidate exists.
  words.el('selection-c1').onclick();
  const manualC1Evidence=words.el('ev').value;
  assert.ok(manualC1Evidence.includes('C1: ಕನ್ನಡ\tಪಠ್ಯ at offset 2'));
  assert.ok(words.fields().diseases.split(';').includes('C1'));
  assert.equal(words.el('hx').value,'U+200B');assert.equal(words.posts.length,0);
  words.el('selection-c1').onclick();assert.equal(words.el('ev').value,manualC1Evidence);
  const preview=words.run('markdownPreview("# Heading\\n<script>alert(1)</script>\\n[x](javascript:alert)")');
  assert.ok(preview.includes('<h1>Heading</h1>'));assert.ok(!preview.includes('<script>'));
  assert.ok(!preview.includes('href="javascript:'));
  const legacy={version:1,fields:{read:'full',verdict:'fix',diseases:'A7;A8;A9;C1',evidence:'A8: ಕೋಣೆ ಗಳ at offset 137',hex:'',note:'retain'}};
  wordsStorage.values.set(words.key('synthetic-13'),JSON.stringify(legacy));
  words.run('drafts.delete("synthetic-13");openDocId("synthetic-13")');
  assert.equal(words.fields().diseases,'C1;G1');assert.ok(words.el('ev').value.startsWith('G1:'));

  extras.run('go(1)');await extras.run('loadInspection(D[cur])');
  assert.ok(extras.el('candidates').innerHTML.includes('Append F1 evidence'));
  extras.el('ev').value='existing safe evidence';extras.el('hx').value='U+0CBF';extras.choose('vd','drop');
  extras.run('appendFindingEvidence("F1")');
  assert.ok(extras.el('ev').value.includes('F1: email-like token at offset '));
  assert.ok(!extras.el('ev').value.includes('example.invalid'));assert.ok(!extras.el('ev').value.includes('synthetic-contact'));
  assert.equal(extras.el('hx').value,'');assert.equal(extras.fields().verdict,'drop');
  extras.run('appendFindingEvidence("C2");appendFindingEvidence("G1")');
  assert.ok(!extras.el('ev').value.includes('ಮಾದರಿ ಸಾಲು'));assert.equal(extras.el('hx').value,'');
  const protectedEvidence=extras.el('ev').value;extras.run('appendFindingEvidence("F1")');
  assert.equal(extras.el('ev').value,protectedEvidence);assert.equal(extras.posts.length,0);
  // An email elsewhere must not replace a harmless manual selection with the
  // old "reader-selected word" placeholder, even when F1 is already checked.
  extras.el('ev').value+=' | A6: reader-selected word at offset 2';
  extras.run('setSelectionRange(2,3);appendSelection("A6")');
  assert.ok(extras.el('ev').value.includes('A6: ಿ at offset 2'));
  assert.ok(!extras.el('ev').value.includes('reader-selected word'));
  assert.equal(extras.el('hx').value,'');assert.equal(extras.posts.length,0);
  const sensitiveEmailMatch=fixture[7].inspection.findings.find(f=>f.code==='F1').matches[0];
  extras.run(`setSelectionRange(${sensitiveEmailMatch.start},${sensitiveEmailMatch.end});appendSelection("A6")`);
  assert.ok(!extras.el('ev').value.includes('example.invalid'));
  assert.ok(extras.el('ev').value.includes('selected text omitted (possible personal data or secret)'));
  assert.equal(extras.el('hx').value,'');

  extras.run('go(1)');await extras.run('loadInspection(D[cur])');extras.run('appendC1Evidence()');
  assert.ok(extras.el('ev').value.includes('C1: "Trending" at offset 0'));
  assert.ok(extras.el('ev').value.includes('C1: "ರಾಜಕೀಯ7 days ago" at offset 9'));
  assert.ok(extras.el('ev').value.includes('C1: "ರಾಜಕೀಯ6 days ago"'));
  assert.ok(extras.el('ev').value.includes('C1: "Title" at offset '));
  extras.run('go(1)');await extras.run('loadInspection(D[cur])');extras.run('appendC1Evidence()');
  assert.ok(extras.el('ev').value.includes('C1: "Team Udayavani, Feb 11, 2021, 3:27 PM IST" at offset 0'));
  assert.ok(extras.el('ev').value.includes('C1: "Last Modified ಶನಿವಾರ, 5 ಸೆಪ್ಟಂಬರ್ 2020 (10:08 IST)" at offset '));
  assert.equal(extras.posts.length,0);
  extras.run('go(1)');await extras.run('loadInspection(D[cur])');extras.run('appendC1Evidence()');
  assert.ok(extras.el('ev').value.includes('C1: "ಮುಖಪುಟ" at offset 0'));
  assert.ok(extras.el('ev').value.includes('C1: "First Published Jan 20, 2021, 2:58 PM IST" at offset '));
  extras.run('go(1)');await extras.run('loadInspection(D[cur])');extras.run('appendC1Evidence()');
  assert.ok(extras.el('ev').value.includes('C1: "ಬೆಂಗಳೂರು |" at offset '));
  assert.ok(extras.el('ev').value.includes('C1: "ಮೈಸೂರು|" at offset '));
  assert.ok(extras.el('ev').value.includes('C1: "ಜೀವ ರಕ್ಷಣೆಗಾಗಿ ಸಂಚಾರ ನಿಯಮ ಪಾಲಿಸಿ" at offset '));
  assert.equal(extras.posts.length,0);

  // Failed localStorage writes retain a per-row in-memory draft and warn the user.
  const blockedStorage={values:new Map(),failWrites:true};const blocked=await app(blockedStorage);
  blocked.el('ev').value='in-memory fallback';blocked.input();
  assert.match(blocked.el('draft-status').textContent,/this tab only/);
  blocked.run('go(1);go(-1)');assert.equal(blocked.el('ev').value,'in-memory fallback');

  // Unreadable stored drafts are not silently deleted on load/navigation.
  const damagedStorage={values:new Map(),failWrites:false};
  const key='diagnosis:draft:v1:'+JSON.stringify(['pack-a','synthetic-0']);damagedStorage.values.set(key,'{broken');
  const damaged=await app(damagedStorage);assert.match(damaged.el('draft-status').textContent,/Could not read/);
  damaged.run('go(1)');assert.equal(damagedStorage.values.get(key),'{broken');

  // c only selects clean; s submits that form and advances after success.
  const shortcuts=await app({values:new Map(),failWrites:false},'shortcut-test');
  shortcuts.run('go(1)');shortcuts.choose('vd','drop');shortcuts.chooseCodes(['D3','H3']);
  shortcuts.el('ev').value='keep this evidence';shortcuts.el('nt').value='keep this note';
  const pressKey=(letter,options={})=>shortcuts.run('document.onkeydown')(Object.assign({key:letter,target:{tagName:'BODY'}},options));
  pressKey('c');
  assert.equal(shortcuts.fields().verdict,'clean');assert.equal(shortcuts.posts.length,0);
  assert.equal(shortcuts.run('cur'),1);assert.equal(shortcuts.fields().evidence,'keep this evidence');
  assert.equal(shortcuts.fields().note,'keep this note');assert.equal(shortcuts.fields().diseases,'D3;H3');
  assert.equal(shortcuts.run('getDraft(D[cur].doc_id).fields.verdict'),'clean');
  pressKey('s');await new Promise(resolve=>setImmediate(resolve));
  assert.equal(shortcuts.posts.length,1);assert.equal(shortcuts.posts[0].verdict,'clean');
  assert.equal(shortcuts.posts[0].diseases,'D3;H3');assert.equal(shortcuts.posts[0].evidence,'keep this evidence');
  assert.equal(shortcuts.run('cur'),2);
  shortcuts.choose('vd','drop');shortcuts.chooseCodes(['C2']);pressKey('c');pressKey('s');
  assert.equal(shortcuts.fields().verdict,'clean');assert.equal(shortcuts.posts.length,1);
  assert.match(shortcuts.el('st').textContent,/clean allows only D3 and H3/);
  shortcuts.choose('vd','drop');pressKey('c',{ctrlKey:true});pressKey('s',{metaKey:true});
  pressKey('c',{target:{tagName:'TEXTAREA'}});pressKey('s',{repeat:true});
  assert.equal(shortcuts.fields().verdict,'drop');assert.equal(shortcuts.posts.length,1);
  shortcuts.el('clean').onclick();assert.equal(shortcuts.fields().verdict,'clean');assert.equal(shortcuts.posts.length,1);
  const footer=await app({values:new Map(),failWrites:false},'varthabharati-footer');
  footer.run('cur=12;render();');await footer.run('loadInspection(D[cur])');
  footer.el('ev').value='existing evidence';footer.input();
  footer.run('appendC1Evidence();');
  const footerMatch=fixture[12].inspection.findings.find(f=>f.code==='C1').matches[0];
  assert.ok(footer.el('ev').value.startsWith('existing evidence | C1:'));
  assert.ok(footer.el('ev').value.includes(`at offset ${footerMatch.start}`));
  assert.ok(footer.el('ev').value.includes('ಬೆಂಬಲಿಸಲು ಇಲ್ಲಿ ಕ್ಲಿಕ್ ಮಾಡಿ'));
  assert.equal(footer.fields().verdict,'fix');assert.equal(footer.fields().diseases,'C1');
  const footerEvidence=footer.el('ev').value;footer.run('appendC1Evidence();');
  assert.equal(footer.el('ev').value,footerEvidence);assert.equal(footer.posts.length,0);
  const news18=await app({values:new Map(),failWrites:false},'news18-metadata');
  news18.run('cur=13;render();');await news18.run('loadInspection(D[cur])');
  news18.run('appendC1Evidence();');
  assert.equal((news18.el('ev').value.match(/C1:/g)||[]).length,3);
  assert.ok(news18.el('ev').value.includes('news18-kannada Updated:'));
  assert.ok(news18.el('ev').value.includes('February 14, 2021, 6:22 PM IST'));
  assert.ok(news18.el('ev').value.includes('"India"'));
  assert.equal(news18.posts.length,0);assert.equal(news18.fields().diseases,'C1');
  console.log('Browser drafts: navigation, filters, reload, isolation, saves, races, discard and storage failures passed.');
}

main().catch(error=>{console.error(error);process.exitCode=1;});
