import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
const frontend=process.env.SOFT_EXAM_FRONTEND_ROOT||fileURLToPath(new URL('../skills/soft-exam-lab/assets/frontend/',import.meta.url));
const require=createRequire(resolve(frontend,'package.json'));
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const {Markdown,reviewAnnotations}=await import(pathToFileURL(resolve(frontend,'src/review-markdown.mjs')));
const render=(text,annotations=[])=>renderToStaticMarkup(React.createElement(Markdown,{text,annotations}));
function mark(text,quote,tone='good',from=0,id=tone){
 const at=text.indexOf(quote,from),start=[...text.slice(0,at)].length;
 assert.ok(at>=0);
 return {id,tone,comment:'测试评语',spans:[{start,end:start+[...quote].length,quote}]};
}
test('three colors mark only the reviewed phrases',()=>{
 const text='背景说明。成功提交。通常安全。绝不丢失。';
 const html=render(text,[mark(text,'成功提交'),mark(text,'通常安全','risk'),mark(text,'绝不丢失','error')]);
 for(const [tone,phrase] of [['good','成功提交'],['risk','通常安全'],['error','绝不丢失']])assert.match(html,new RegExp('class="review-mark review-'+tone+'"[^>]*>'+phrase+'</mark>'));
 assert.match(html,/<p>背景说明。<mark/);
});
test('lists, emphasis and tables retain their Markdown structure',()=>{
 const text='- 先**提交数据库**再删除。\n\n| 指标 | 值 |\n|---|---|\n| 吞吐量 | 10 |';
 const html=render(text,[mark(text,'提交数据库'),mark(text,'吞吐量')]);
 assert.match(html,/<ul>/);assert.match(html,/<strong><mark[^>]*>提交数据库<\/mark><\/strong>/);
 assert.match(html,/<table>/);assert.match(html,/<td><mark[^>]*>吞吐量<\/mark><\/td>/);
});
test('Python character offsets select the second occurrence after an emoji',()=>{
 const text='😀 重复词。背景。重复词。';
 const html=render(text,[mark(text,'重复词','error',text.indexOf('重复词')+3)]);
 assert.match(html,/<p>😀 重复词。背景。<mark/);
 assert.equal((html.match(/<mark/g)||[]).length,1);
});
test('escaped punctuation and entities do not shift later highlights',()=>{
 const text='A &amp; B，\\*字面星号\\*。正确机制。';
 const html=render(text,[mark(text,'&amp;'),mark(text,'正确机制')]);
 assert.match(html,/<mark[^>]*>&amp;<\/mark>/);
 assert.match(html,/\*字面星号\*。<mark[^>]*>正确机制<\/mark>/);
});
test('blockquotes and indented list continuation keep only visible text',()=>{
 const text='> 第一行\n> 第二行\n\n- 列表开头\n  列表续行';
 const html=render(text,[mark(text,'第二行'),mark(text,'列表续行')]);
 assert.match(html,/<blockquote>/);assert.match(html,/<mark[^>]*>第二行<\/mark>/);
 assert.match(html,/<mark[^>]*>列表续行<\/mark>/);
 assert.doesNotMatch(html,/&gt;/);
});
test('inline and fenced code keep code semantics while highlighting',()=>{
 const tick=String.fromCharCode(96),text='执行 '+tick+'commit(db)'+tick+'。\n\n'+tick.repeat(3)+'python\nif failed:\n    delete(cache)\n'+tick.repeat(3);
 const html=render(text,[mark(text,'commit'),mark(text,'delete','error')]);
 assert.match(html,/<code><mark[^>]*>commit<\/mark>\(db\)<\/code>/);
 assert.match(html,/<pre><code class="language-python">if failed:\n {4}<mark[^>]*>delete<\/mark>/);
});
test('inline code escapes remain literal',()=>{
 const tick=String.fromCharCode(96),text=tick+'A &amp; B'+tick;
 const html=render(text,[mark(text,'&amp;')]);
 assert.match(html,/<mark[^>]*>&amp;amp;<\/mark>/);
});
test('formulas remain KaTeX and are highlighted as complete notation',()=>{
 const text='效率为 $x^2$，结论成立。';
 const html=render(text,[mark(text,'x^2')]);
 assert.match(html,/<mark[^>]*><span class="katex">/);
 assert.match(html,/<annotation encoding="application\/x-tex">x\^2<\/annotation>/);
});
test('overlap prioritizes errors and retains both explanations',()=>{
 const text='成功提交之后删除';
 const html=render(text,[mark(text,'成功提交'),mark(text,'提交之后','error')]);
 assert.match(html,/<mark[^>]*review-good[^>]*>成功<\/mark>/);
 assert.match(html,/<mark[^>]*review-error[^>]*data-review-ids="good error"/);
 assert.equal(html.replace(/<[^>]*>/g,''),text);
});
test('warnings are explicit and omitted or pending points do not become red',()=>{
 const e={kind:'text',start:0,end:2,quote:'正文'};
 const grade={results:[{id:'a',question_id:'q',status:'awarded',evidence:[e]},
  {id:'b',question_id:'q',status:'omitted',evidence:[e]},{id:'c',question_id:'q',status:'pending',evidence:[e]}],
  warnings:[{question_id:'q',comment:'需限定前提',evidence:e}]};
 const annotations=reviewAnnotations(grade,'q');
 assert.deepEqual(annotations.map(a=>a.tone),['good','risk']);
 assert.deepEqual(reviewAnnotations(grade,'not-selected'),[]);
});
test('evidence focus leaves surrounding neutral context unmarked',()=>{
 const text='已提供背景，必须成功提交，随后删除。';
 const span=mark(text,'成功提交').spans[0];
 const grade={results:[{id:'a',question_id:'q',status:'awarded',evidence:[{kind:'text',start:0,end:[...text].length,quote:text,focus:[span]}]}]};
 const html=render(text,reviewAnnotations(grade,'q'));
 assert.match(html,/<p>已提供背景，必须<mark[^>]*>成功提交<\/mark>，随后删除。<\/p>/);
});
test('essay headings and a long body use the same precise marks',()=>{
 const text='## 摘要\n\n项目背景。\n\n## 正文\n\n'+('项目实施。'.repeat(500))+'最终满足性能指标。';
 const html=render(text,[mark(text,'最终满足性能指标')]);
 assert.match(html,/<h2>摘要<\/h2>/);assert.match(html,/<h2>正文<\/h2>/);
 assert.match(html,/<mark[^>]*>最终满足性能指标<\/mark>/);
 assert.equal((html.match(/<mark/g)||[]).length,1);
});
test('answer HTML stays text and remote Markdown images stay disabled',()=>{
 const text='<script>alert(1)</script>\n\n![外部图片](https://example.invalid/private.png)\n\n普通文本';
 const html=render(text,[mark(text,'普通文本')]);
 assert.doesNotMatch(html,/<script|<img/);
 assert.match(html,/<mark[^>]*>普通文本<\/mark>/);
});
