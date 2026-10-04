import {build} from 'esbuild';
import {cpSync, rmSync, mkdirSync, readFileSync, writeFileSync, readdirSync} from 'node:fs';
import {join} from 'node:path';
rmSync('dist',{recursive:true,force:true});
mkdirSync('dist', {recursive:true});
await build({entryPoints:['src/app.jsx'],bundle:true,outfile:'dist/lab.js',format:'iife',conditions:['production'],minify:true,jsx:'automatic',define:{'process.env.NODE_ENV':'"production"','process.env.IS_PREACT':'"false"'},loader:{'.woff2':'file','.woff':'file','.ttf':'file'},assetNames:'fonts/[name]-[hash]',legalComments:'linked'});
const fonts='node_modules/@excalidraw/excalidraw/dist/prod/fonts';
cpSync(fonts,'dist/fonts',{recursive:true});
const notices=[];
function licenses(dir){for(const e of readdirSync(dir,{withFileTypes:true})){const p=join(dir,e.name);if(e.isDirectory() && e.name !== '.bin') licenses(p);else if(e.isFile() && /^(license|copying|notice)(\.|$)/i.test(e.name)) notices.push(p+'\n'+readFileSync(p,'utf8'));}}
licenses('node_modules');writeFileSync('dist/THIRD-PARTY-NOTICES.txt',notices.join('\n\n---\n\n'));
