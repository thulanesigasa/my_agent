# elevate agent: text and voice conversations

The redesigned interaction screen is **http://localhost:3000/**. The outreach dashboard remains at `/dashboard`; its layout and sending approval flow are retained. Pull and restart both servers after updating. No new mandatory dependency is needed for text or browser voice.

## Conversation screen

The sidebar offers Elevate, Research, Outreach and Reports spaces, with separate conversation IDs and in-tab histories. Each space uses the existing central agent workflow; choosing a space keeps that conversation separate, rather than claiming that a different independent worker has been started. Text and voice within a space use the same server conversation ID. **New conversation** creates a fresh ID for that space. Histories remain in memory for the current page; refreshing starts a new browser conversation rather than storing business messages in browser storage.

Type a message and press Enter or Send. Shift+Enter inserts a new line. Responses can be copied or read aloud. A visible error replaces fabricated success when the backend is unavailable. Stop waiting cancels the browser request, not necessarily an already-running backend task; check Approvals before repeating an action. Chatting or using a wake phrase never grants email sending approval.

## Browser voice and wake phrase

Click **Voice conversation**, allow microphone/speech permission, then speak. Where supported, browser speech recognition sends the real recognized text through the same chat endpoint, and browser speech synthesis reads the returned answer. Recognition stops while processing or speaking, then resumes for your next turn. End voice stops the conversation microphone. Interrupt stops response playback and returns to listening. Every recognized turn and agent text response appears in the chat history.

Click **Enable wake phrase** to opt in to standby listening. Say **elevate agent** to enter voice conversation; you can also say the phrase followed by a command. Bare **agen**, **agent** or **Hey Agent** does not activate. Ambient standby speech is not submitted to the agent as a command. Disable wake listening when finished. If wake listening remains enabled, ending a conversation returns to standby; it does not pretend the microphone is completely off.

Browser recognition is not universally supported. Some browsers use a remote speech service and require internet access; this is not advertised as offline recognition or speaker authentication. The app checks capability and surfaces permission/service errors. See the [MDN SpeechRecognition reference](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition). Use headphones if room playback is picked up by your microphone. Real hardware/accent/environment accuracy must be tested on your PC.

If browser speech recognition is unavailable, the voice button retains the existing backend audio pipeline. That path requires your configured Groq speech-to-text and working speech output. Missing/failed transcription now raises a clear error and never substitutes a made-up command. Text responses remain visible when speech output fails. Server voice sessions have separate IDs by default and the interaction screen binds them to the selected text conversation. Existing protected WebSocket environments need their existing browser-accessible operator connection configuration; do not publish operator credentials on a public site.

## Desktop summon and double claps

The desktop listener still launches/focuses the app. Its launcher now defaults to **double claps**, retaining the existing detector thresholds/timing/cooldown; the reusable detector still supports explicitly selected single-clap mode. Run the existing Windows launcher or:

```powershell
.\.venv\Scripts\python.exe start_agent.py
```

The previous Python wake detector only measured sound energy and falsely claimed to recognize a word/authenticate a speaker. Loud sound alone no longer triggers it. For actual offline desktop recognition before a browser is open, optionally install Vosk and supply an English model:

```powershell
.\.venv\Scripts\python.exe -m pip install -r apps/agent/requirements-wake.txt
```

Download and extract an English model using the [official Vosk installation/model instructions](https://alphacephei.com/vosk/install), then set an absolute local directory in your existing root `.env`:

```dotenv
WAKE_MODEL_PATH=D:/models/your-extracted-english-vosk-model
```

Restart the desktop listener. It loads that local model once and resamples microphone chunks for recognized-word matching. It makes no provider requests or automatic model downloads. If Vosk/model setup is absent or fails, desktop voice activation stays disabled with a notice; **double claps still work**, and browser wake listening can be enabled on the open interaction screen. Wake detection is activation only, never identity verification or API authorization. A stopped PC/listener cannot hear a phrase or clap.

## Reduced automation interruptions

The approval-only coordinator now automatically recovers abandoned non-dispatching run bookkeeping. Existing deterministic approval/job IDs and durable per-day attempt reservations prevent duplicate or replayed draft steps. A transient unexpected failure is retried on a later normal tick; **three consecutive unexpected failures** pause the mode. Recorded progress and exact approvals are retained. This does not retry or resend a provider email submission.

For owned submissions held in sending/delivery_unknown for at least five minutes, the coordinator tries existing evidence-based Gmail reconciliation: at most two per tick and at least 15 minutes between attempts for the same approval. Only matching Gmail Sent evidence can confirm a submission. Missing, ambiguous, legacy or unavailable evidence leaves it held, and no resend is attempted. Reconciliation can consume Gmail API calls, not research/model credits.

Real missing recipient permission, unsupported qualification evidence, outages, powered-off hardware and unsuccessful live validation cannot be made true by code. The app continues to show or skip those exceptions. Live business results are not claimed from offline tests.

## Verification

Backend tests cover real wake-phrase boundaries, no loudness-based false activation, retained double-clap behaviour, no invented transcription commands, voice session isolation, recovery, repeated failures and bounded read-only reconciliation. `npm --prefix apps/web run test:voice` checks browser speech state with deterministic fakes, including wake-only capture, stale-event rejection, playback/microphone separation and cleanup. No real provider calls, microphones or emails are used by those tests.
