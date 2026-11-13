const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
function fixture(extra = {}) {
  const instances = [], states = [], finals = [], errors = [], utterances = [];
  let activations = 0;
  const audios = [], revoked = [];
  class Audio { constructor(url) { this.url = url; audios.push(this); } play() { this.played = true; return Promise.resolve(); } pause() { this.paused = true; } }
  class Recognition {
    constructor() { instances.push(this); }
    start() { this.started = true; }
    abort() { this.aborted = true; }
  }
  const target = { exports: {} };
  const code = ts.transpileModule(fs.readFileSync(require('node:path').join(__dirname, '../lib/browser-voice.ts'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2017 } }).outputText;
  vm.runInNewContext(code, { exports: target.exports, module: target, AbortController, Audio, URL: { createObjectURL: () => "blob:fixture", revokeObjectURL: (url) => revoked.push(url) }, window: { SpeechRecognition: Recognition, speechSynthesis: { cancel() {}, speak(u) { utterances.push(u); } } }, SpeechSynthesisUtterance: class { constructor(text) { this.text = text; } }, setTimeout: () => 1, clearTimeout() {}, console });
  const { BrowserVoice, wakeCommand } = target.exports;
  const voice = new BrowserVoice({ state: s => states.push(s), transcript() {}, final: s => finals.push(s), activated: () => activations++, error: s => errors.push(s), ...extra });
  const say = (text, instance = instances.at(-1)) => instance.onresult?.({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: text } }] });
  return { audios, revoked, voice, wakeCommand, instances, states, finals, errors, utterances, say, activations: () => activations };
}
test('requires the exact two-word elevate agent phrase', () => {
  const f = fixture();
  for (const text of ['agen', 'agent', 'elevate agen', 'Hey Agent', 'elevate agency', 'elevate']) assert.equal(f.wakeCommand(text), null);
  assert.equal(f.wakeCommand('elevate agent, show my progress'), 'show my progress');
  assert.equal(f.wakeCommand('elevate agent'), '');
});
test('microphone recognition is opt-in and ambient speech is never sent as a command', () => {
  const f = fixture(); assert.equal(f.instances.length, 0);
  f.voice.setWake(true); f.say('hello agent'); assert.equal(f.finals.length, 0); assert.equal(f.activations(), 0);
  f.say('elevate agent'); assert.equal(f.activations(), 1); assert.equal(f.finals.length, 0);
  f.say('Show my pending approvals'); assert.deepEqual(f.finals, ['Show my pending approvals']); assert.equal(f.states.at(-1), 'processing');
});
test('wake command suffix is submitted exactly once and stale recognition events are ignored', () => {
  const f = fixture(); f.voice.setWake(true);
  const stale = f.instances[0].onresult;
  f.say('elevate agent summarise my outreach');
  stale({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: 'send everything' } }] });
  assert.deepEqual(f.finals, ['summarise my outreach']);
});
test('recognition is stopped during speech and playback completion resumes the conversation', () => {
  const f = fixture(); f.voice.start(); const first = f.instances[0];
  f.voice.speak('Hello **there**'); assert.ok(first.aborted); assert.equal(f.states.at(-1), 'speaking');
  f.utterances[0].onend(); assert.equal(f.states.at(-1), 'listening'); assert.equal(f.instances.length, 2);
});
test('permission rejection disables recognition and does not replay a command', () => {
  const f = fixture(); f.voice.start(); f.instances[0].onerror({ error: 'not-allowed' });
  assert.equal(f.states.at(-1), 'idle'); assert.match(f.errors[0], /permission/); assert.equal(f.finals.length, 0);
});
test('stop/dispose invalidates speech callbacks and releases recognition', () => {
  const f = fixture(); f.voice.start(); f.voice.speak('response'); const callback = f.utterances[0].onend;
  f.voice.stop(); const count = f.instances.length; callback(); assert.equal(f.instances.length, count);
  f.voice.dispose(); assert.ok(f.instances[0].aborted);
});

function audioFixture(deferred = false) {
  const sockets = [], recorders = [], tracks = [];
  let resolveCapture;
  class Socket {
    static OPEN = 1;
    constructor(){this.readyState=1;this.sent=[];sockets.push(this)}
    send(data){this.sent.push(data)} close(){this.readyState=3;this.onclose?.()}
  }
  class Recorder {
    static isTypeSupported(){return true}
    constructor(){this.state='inactive';recorders.push(this)}
    start(){this.state='recording'} stop(){this.state='inactive'}
  }
  const stream = () => {const track={enabled:true,stopped:false,stop(){this.stopped=true}};tracks.push(track);return {getAudioTracks:()=>[track],getTracks:()=>[track]}};
  class Context {
    createMediaStreamSource(){return {connect(){}}}
    createAnalyser(){return {frequencyBinCount:128,getByteFrequencyData(){}}}
    close(){return Promise.resolve()}
  }
  const target={exports:{}};
  const code=ts.transpileModule(fs.readFileSync(require('node:path').join(__dirname,'../lib/audio.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2017}}).outputText;
  vm.runInNewContext(code,{exports:target.exports,module:target,process:{env:{}},URL,WebSocket:Socket,MediaRecorder:Recorder,Blob,window:{location:{hostname:'localhost'},AudioContext:Context,setInterval:()=>1,setTimeout:()=>1},navigator:{mediaDevices:{getUserMedia:()=>deferred?new Promise(resolve=>{resolveCapture=resolve}):Promise.resolve(stream())}},setTimeout:()=>1,clearTimeout(){},clearInterval(){},console:{log(){},warn(){},error(){}}});
  return {manager:new target.exports.AudioStreamManager(),sockets,recorders,tracks,resolve:()=>resolveCapture(stream())};
}
test('server voice stops a microphone permission request that resolves after disconnect',async()=>{
  const f=audioFixture(true);const connecting=f.manager.connect(undefined,'shared_chat');f.sockets[0].onopen();assert.equal(await connecting,true);
  const capture=f.manager.startStreaming();f.manager.disconnect();f.resolve();assert.equal(await capture,false);assert.ok(f.tracks[0].stopped);assert.equal(f.recorders.length,0);
});
test('stale discarded recording is never transmitted into a new recording turn',async()=>{
  const f=audioFixture();const connecting=f.manager.connect(undefined,'shared_chat');f.sockets[0].onopen();await connecting;
  await f.manager.startStreaming();const old=f.recorders[0];old.ondataavailable({data:new Blob(['discarded'])});
  await f.manager.startStreaming();await old.onstop();assert.equal(f.sockets[0].sent.length,1);
  const current=f.recorders[1];current.ondataavailable({data:new Blob(['current'])});f.manager.stopStreaming(true);await current.onstop();assert.equal(f.sockets[0].sent.length,2);f.manager.disconnect();
});

test('ElevenLabs playback keeps recognition stopped until audio ends and releases its URL', async () => {
  const f = fixture({ speech: async () => new Blob(['audio']) });
  f.voice.start(); const recognition = f.instances.at(-1);
  await f.voice.speak('Hello');
  assert.ok(recognition.aborted); assert.equal(f.utterances.length, 0);
  assert.equal(f.audios.length, 1); assert.ok(f.audios[0].played);
  f.audios[0].onended(); assert.equal(f.states.at(-1), 'listening');
  assert.ok(f.audios[0].paused); assert.deepEqual(f.revoked, ['blob:fixture']);
});
test('ending voice aborts pending ElevenLabs speech and rejects late audio', async () => {
  let resolve, signal;
  const f = fixture({ speech: (_text, s) => { signal = s; return new Promise(r => resolve = r); } });
  f.voice.start(); const request = f.voice.speak('Hello');
  f.voice.stop(); assert.ok(signal.aborted);
  resolve(new Blob(['late audio'])); await request;
  assert.equal(f.audios.length, 0); assert.equal(f.states.at(-1), 'idle');
});
test('a paid speech failure stays visible and never silently switches to browser speech', async () => {
  const f = fixture({ speech: async () => { throw new Error('provider quota'); } });
  f.voice.start(); await f.voice.speak('Hello');
  assert.equal(f.errors.length, 1); assert.equal(f.utterances.length, 0);
  assert.equal(f.states.at(-1), 'listening');
});
