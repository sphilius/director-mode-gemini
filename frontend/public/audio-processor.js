/**
 * AudioWorklet processor for capturing mic audio as PCM 16-bit 24kHz.
 *
 * The browser's AudioContext typically captures at 44.1kHz or 48kHz.
 * This processor downsamples to 24kHz and converts float32 → int16
 * before posting the buffer to the main thread.
 */

const TARGET_SAMPLE_RATE = 24000;

class AudioCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    // sampleRate is the AudioContext's native rate (e.g. 48000)
    this._ratio = sampleRate / TARGET_SAMPLE_RATE;
    this._inputSampleIndex = 0;
  }

  /**
   * Downsample from native rate to 24kHz using nearest-neighbour,
   * then quantise float32 [-1,1] → int16 [-32768,32767].
   */
  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0]; // mono — channel 0
    const downsampled = [];

    for (let i = 0; i < channelData.length; i++) {
      this._inputSampleIndex++;
      if (this._inputSampleIndex >= this._ratio) {
        this._inputSampleIndex -= this._ratio;

        // Clamp and convert to int16
        const s = Math.max(-1, Math.min(1, channelData[i]));
        downsampled.push(s < 0 ? s * 0x8000 : s * 0x7fff);
      }
    }

    if (downsampled.length > 0) {
      const pcm = new Int16Array(downsampled);
      this.port.postMessage(
        { type: "audio", pcm: pcm.buffer },
        [pcm.buffer],
      );
    }

    return true;
  }
}

registerProcessor("audio-capture-processor", AudioCaptureProcessor);
