# Voice input: ask a rule by voice, on-device

A blind fan can ask any Laws-of-the-Game question by **voice**, in their language, and hear the
answer through their screen reader. The transcript feeds the existing oracle (retrieve the Law ->
IBM Granite -> Granite Guardian -> the spoken answer), so the answer is rule-grounded and safety-
checked. This closes the voice loop: speak the question, hear the rule-grounded why.

## Two tiers (honest about each)

1. **On-device ASR (the default).** `apps/web/src/voice.ts` records the question and transcribes it
   **entirely in the browser** with **Whisper-base** (multilingual, ~150 MB) running in
   Transformers.js on **WebGPU**. The audio never leaves the device, and after the one-time model
   fetch it works offline. Whisper-base is the one confirmed, practically-sized in-browser
   multilingual ASR.
2. **Web Speech API (the zero-download floor).** Where on-device ASR is not available, the browser's
   `SpeechRecognition` is used. It is instant and needs no download, but it is **on-device only on
   recent Chrome (139+, opt-in)**; on other browsers it sends audio to the browser's speech service
   (Google / Apple / Azure). It is a progressive enhancement, not universally available (Firefox
   disables it).

The text box is always available, so voice is never required.

## The all-IBM angle, stated honestly

The rule **answer** is already all-IBM and available fully on-device (IBM Granite Nano + Granite
Guardian, the offline mode). For the ASR itself, **IBM Granite Speech**
(`onnx-community/granite-speech-4.1-2b-ONNX`) **does run on-device in the browser** via
Transformers.js (the `GraniteSpeechForConditionalGeneration` generate path on WebGPU, demonstrated in
a community Space), so a **fully on-device, all-IBM voice loop is achievable**. But Granite Speech is
a ~1.5 GB+ speech-conditioned LLM with no official ASR pipeline, so VARSITY ships **Whisper-base**
(~150 MB) as the practical default and treats Granite Speech as the **opt-in / experimental all-IBM**
ASR path rather than overstating it as the default. A self-hosted Granite Speech endpoint (the IBM
hosted ASR product is the separate Watson Speech to Text) is the server-side all-IBM option.

## Privacy

The on-device path keeps the microphone audio on the device (no server). This is consistent with
VARSITY's on-device posture (see `docs/LEGAL.md`): on the default tier there is no audio upload, no
account, and no analytics. The Web Speech floor is the only path that may route audio to a browser
speech service, and only where on-device ASR is unavailable.

## In concept

Voice is an input modality for the rule oracle: it asks about the Laws of the Game and answers from
the retrieved Law. It explains; it never adjudicates.
