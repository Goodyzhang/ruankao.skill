import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkBreaks from 'remark-breaks';
import rehypeKatex from 'rehype-katex';
import {decodeString} from 'micromark-util-decode-string';

export const annotationLabels={good:'得分依据',risk:'表述风险',error:'明确错误'};
const priority={good:1,risk:2,error:3};

// One evidence passage can contain several precise, independently highlighted phrases.
export function reviewAnnotations(grade,qid){
 const items=[];
 const add=(id,tone,e,comment,label)=>{
  if(e?.kind!=='text'||!tone)return;
  items.push({id,tone,evidence:e,comment,label,spans:e.focus?.length?e.focus:[e]});
 };
 for(const p of grade.results.filter(p=>p.question_id===qid)){
  p.evidence?.forEach((e,i)=>add('point-'+p.id+'-'+i,p.status==='awarded'?'good':p.status==='incorrect'?'error':null,e,p.comment,p.criterion));
 }
 for(const [name,tone] of [['warnings','risk'],['reference_penalties','error'],['penalties','error']]){
  grade[name]?.forEach((p,i)=>{if(p.question_id===qid)add(name+'-'+i,tone,p.evidence,p.comment,name==='warnings'?'表述建议':p.amount?'扣分 '+p.amount+' 分':'同因已计入');});
 }
 return items;
}

function properties(items,activeId){
 const tone=items.reduce((best,a)=>priority[a.tone]>priority[best]?a.tone:best,'good');
 return {className:['review-mark','review-'+tone,...(items.some(a=>a.id===activeId)?['review-active']:[])],
  'data-review-ids':items.map(a=>a.id).join(' '),
  title:items.map(a=>annotationLabels[a.tone]+'：'+a.comment).join('\n')};
}
const textNode=value=>({type:'text',value});
const markNode=(children,items,activeId)=>({type:'reviewMark',data:{hName:'mark',hProperties:properties(items,activeId)},children});
const codeChild=node=>node.type==='text'?node:{type:'element',tagName:'mark',properties:node.data.hProperties,children:node.children.map(codeChild)};

function splitMarked(value,map,annotations,activeId){
 const parts=[];
 let start=0,lastKey=null,lastItems=[];
 for(let i=0;i<=value.length;i++){
  const items=i===value.length?[]:annotations.filter(a=>a.ranges.some(r=>r.start<map[i][1]&&r.end>map[i][0]));
  const key=items.map(a=>a.id).join(' ');
  if(i===0){lastKey=key;lastItems=items;}
  if(key!==lastKey||i===value.length){
   if(i>start){const child=textNode(value.slice(start,i));parts.push(lastItems.length?markNode([child],lastItems,activeId):child);}
   start=i;lastKey=key;lastItems=items;
  }
 }
 return parts;
}

// Source positions belong to Markdown, so decoded entities and escaped punctuation
// keep their original range instead of shifting all later annotations.
function textMap(raw,offset,expected){
 const map=[];let value='';
 const atoms=/\\[!-/:-@\[-\x60{-~]|&(?:#x[\da-f]+|#\d+|[a-z][\da-z]+);|\r\n?|\n|[\s\S]/giu;
 for(const match of raw.matchAll(atoms)){
  const decoded=/^\r/.test(match[0])?'\n':decodeString(match[0]);
  value+=decoded;
  for(let i=0;i<decoded.length;i++)map.push([offset+match.index,offset+match.index+match[0].length]);
 }
 if(value===expected)return {value,map};
 // Continuation lines in lists and blockquotes omit their Markdown prefixes.
 const selected=[];let cursor=0;
 for(const line of expected.split('\n')){
  const at=value.indexOf(line,cursor);
  selected.push(...map.slice(at,at+line.length));
  cursor=at+line.length;
  if(selected.length<expected.length){const end=value.indexOf('\n',cursor);selected.push(map[end]);cursor=end+1;}
 }
 return {value:expected,map:selected};
}

function codeMap(node,source){
 const start=node.position.start.offset,raw=source.slice(start,node.position.end.offset);
 if(node.type==='inlineCode'){
  const ticks=raw.match(/^\x60+/)[0].length,body=raw.slice(ticks,-ticks),map=[];
  let value='';
  for(const match of body.matchAll(/\r\n?|\n|[\s\S]/gu)){
   const char=/^[\r\n]/.test(match[0])?' ':match[0];value+=char;
   for(let i=0;i<char.length;i++)map.push([start+ticks+match.index,start+ticks+match.index+match[0].length]);
  }
  if(value.startsWith(' ')&&value.endsWith(' ')&&/[^ ]/.test(value)){value=value.slice(1,-1);map.shift();map.pop();}
  return {value,map};
 }
 const opening=raw.match(/^(?:\x60{3,}|~{3,})[^\n]*\n/);
 let cursor=opening?opening[0].length:0;
 const map=[];
 const lines=node.value.split('\n');
 for(let n=0;n<lines.length;n++){
  const line=lines[n],at=raw.indexOf(line,cursor);
  for(let i=0;i<line.length;i++)map.push([start+at+i,start+at+i+1]);
  cursor=at+line.length;
  if(n<lines.length-1){const end=raw.indexOf('\n',cursor);map.push([start+end,start+end+1]);cursor=end+1;}
 }
 return {value:node.value,map};
}

export function remarkReview({annotations=[],activeId}={}){
 return (tree,file)=>{
  if(!annotations.length)return;
  const source=String(file),offsets=[0];let offset=0;
  for(const char of source){offset+=char.length;offsets.push(offset);}
  const mapped=annotations.map(a=>({...a,ranges:a.spans.map(s=>({start:offsets[s.start],end:offsets[s.end]}))}));
  function visit(parent){
   parent.children=parent.children.flatMap(node=>{
    const start=node.position?.start.offset,end=node.position?.end.offset;
    const relevant=mapped.filter(a=>a.ranges.some(r=>r.start<end&&r.end>start));
    if(!relevant.length)return node;
    if(node.type==='text'||node.type==='inlineCode'||node.type==='code'){
     const decoded=node.type==='text'?textMap(source.slice(start,end),start,node.value):codeMap(node,source);
     const children=splitMarked(decoded.value,decoded.map,relevant,activeId);
     if(node.type==='text')return children;
     // hChildren preserves code whitespace and avoids prose soft-break transforms.
     return {...node,data:{...node.data,hChildren:children.map(codeChild).concat(node.type==='code'?[textNode('\n')]:[])}};
    }
    // Mathematical notation is one rendered unit; mark the complete formula.
    if(node.type==='math'||node.type==='inlineMath')return markNode([node],relevant,activeId);
    if(node.children)visit(node);
    return node;
   });
  }
  visit(tree);
 };
}

export function Markdown({text='',annotations=[],activeId}){
 return React.createElement('div',{className:'markdown'},
  React.createElement(ReactMarkdown,{
   remarkPlugins:[remarkGfm,remarkMath,[remarkReview,{annotations,activeId}],remarkBreaks],
   rehypePlugins:[[rehypeKatex,{trust:false,throwOnError:false}]],disallowedElements:['img']
  },text));
}
