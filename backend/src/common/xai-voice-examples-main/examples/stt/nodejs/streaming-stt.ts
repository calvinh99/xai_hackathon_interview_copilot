#!/usr/bin/env node
/**
 * Streaming Speech-to-Text Example
 *
 * This example demonstrates how to use XAI's streaming STT API to transcribe speech
 * in real-time using WebSocket connections. Audio is captured from the microphone
 * and transcribed as you speak.
 *
 * API: wss://api.x.ai/v1/realtime/audio/transcriptions
 * Audio format: PCM linear16, 16kHz, mono
 */

import WebSocket from "ws";
import { spawn } from "child_process";
import dotenv from "dotenv";

dotenv.config();

interface ConfigMessage {
  type: "config";
  data: {
    encoding: string;
    sample_rate_hertz: number;
    enable_interim_results: boolean;
  };
}

interface AudioMessage {
  type: "audio";
  data: {
    audio: string; // base64
  };
}

interface TranscriptResponse {
  data: {
    type: "speech_recognized";
    data: {
      transcript: string;
      is_final: boolean;
    };
  };
}

/**
 * Streaming Speech-to-Text handler
 */
class StreamingSTT {
  private sampleRate: number;
  private channels: number;
  private enableInterim: boolean;
  private running: boolean = false;
  private finalTranscript: string = "";
  private currentInterim: string = "";

  constructor(
    sampleRate: number = 16000,
    channels: number = 1,
    enableInterim: boolean = true
  ) {
    this.sampleRate = sampleRate;
    this.channels = channels;
    this.enableInterim = enableInterim;
  }

  /**
   * Stream audio from microphone to XAI API
   */
  async streamAudio(): Promise<void> {
    // Get API key
    const apiKey = process.env.XAI_API_KEY;
    if (!apiKey) {
      throw new Error("XAI_API_KEY not found in environment variables");
    }

    // Get base URL
    const baseUrl = process.env.BASE_URL || "https://api.x.ai/v1";
    const wsUrl = baseUrl.replace("https://", "wss://").replace("http://", "ws://");
    const uri = `${wsUrl}/realtime/audio/transcriptions`;

    console.log(`🎤 Connecting to ${uri}`);
    console.log(`📊 Sample rate: ${this.sampleRate} Hz`);
    console.log(`🎵 Channels: ${this.channels}`);
    console.log(
      `⏱️  Interim results: ${this.enableInterim ? "enabled" : "disabled"}`
    );

    return new Promise((resolve, reject) => {
      // Start recording audio with ffmpeg
      const ffmpeg = spawn(
        "ffmpeg",
        [
          "-f",
          "avfoundation", // Use 'pulse' on Linux or 'dshow' on Windows
          "-i",
          ":0", // Default audio input (use ':0' for default mic on macOS)
          "-f",
          "s16le", // signed 16-bit little-endian PCM
          "-ar",
          this.sampleRate.toString(), // sample rate
          "-ac",
          this.channels.toString(), // channels
          "-acodec",
          "pcm_s16le", // PCM 16-bit
          "-loglevel",
          "error", // suppress ffmpeg logs
          "-",
        ],
        {
          stdio: ["ignore", "pipe", "inherit"],
        }
      );

      ffmpeg.on("error", (err) => {
        console.error("❌ Error starting audio capture:", err);
        reject(err);
      });

      console.log("✅ Microphone ready");

      // Connect to WebSocket
      const ws = new WebSocket(uri, {
        headers: {
          Authorization: `Bearer ${apiKey}`,
        },
      });

      let chunkCount = 0;

      ws.on("open", () => {
        console.log("✅ Connected to XAI streaming STT API");
        console.log("\n🎙️  Speak now... (Press Ctrl+C to stop)\n");

        // Send config message
        const configMessage: ConfigMessage = {
          type: "config",
          data: {
            encoding: "linear16",
            sample_rate_hertz: this.sampleRate,
            enable_interim_results: this.enableInterim,
          },
        };
        ws.send(JSON.stringify(configMessage));
        console.log("📤 Sent config");

        this.running = true;

        // Read audio from ffmpeg stdout
        ffmpeg.stdout!.on("data", (audioData: Buffer) => {
          if (!this.running) return;

          // Convert to base64
          const audioB64 = audioData.toString("base64");

          // Send audio message
          const audioMessage: AudioMessage = {
            type: "audio",
            data: {
              audio: audioB64,
            },
          };

          ws.send(JSON.stringify(audioMessage));

          chunkCount++;
          if (chunkCount % 50 === 0) {
            process.stdout.write(`  📤 Sent ${chunkCount} audio chunks...\r`);
          }
        });
      });

      ws.on("message", (data: WebSocket.Data) => {
        try {
          const message: TranscriptResponse = JSON.parse(data.toString());

          // Check if it's a transcript
          if (message.data?.type === "speech_recognized") {
            const { transcript, is_final } = message.data.data;

            if (is_final) {
              // Final transcript
              this.finalTranscript += transcript + " ";
              this.currentInterim = "";
              console.log(`\r✅ ${transcript}`);
            } else {
              // Interim transcript
              this.currentInterim = transcript;
              process.stdout.write(`\r💭 ${transcript}`);
            }
          }
        } catch (err) {
          console.error("❌ Error parsing message:", err);
        }
      });

      ws.on("close", () => {
        console.log("\n\n✅ Connection closed");
        this.running = false;
        ffmpeg.kill();

        if (this.finalTranscript) {
          console.log(`\n📝 Final transcript:\n${this.finalTranscript}`);
        }

        resolve();
      });

      ws.on("error", (err) => {
        console.error("❌ WebSocket error:", err);
        this.running = false;
        ffmpeg.kill();
        reject(err);
      });

      // Handle Ctrl+C
      process.on("SIGINT", () => {
        console.log("\n\n⚠️  Interrupted by user");
        this.running = false;
        ffmpeg.kill();
        ws.close();
        process.exit(0);
      });
    });
  }
}

/**
 * Main entry point
 */
async function main() {
  const args = process.argv.slice(2);

  if (args.includes("--help") || args.includes("-h")) {
    console.log(`
Streaming Speech-to-Text using XAI API

Usage:
  npm start [options]

Options:
  --sample-rate <hz>  Audio sample rate in Hz (default: 16000)
  --channels <n>      Number of audio channels (default: 1 for mono)
  --no-interim        Disable interim results (only show final transcripts)
  --help, -h          Show this help message

Examples:
  # Basic usage with default settings
  npm start

  # Disable interim results (only show final transcripts)
  npm start -- --no-interim

  # Custom sample rate
  npm start -- --sample-rate 24000

Notes:
  - Press Ctrl+C to stop recording
  - Interim results show partial transcripts in real-time
  - Final results are confirmed transcripts
  - Requires ffmpeg to be installed

Install ffmpeg:
  macOS:   brew install ffmpeg
  Linux:   apt install ffmpeg
  Windows: Download from ffmpeg.org

Platform-specific audio input:
  - macOS: Uses 'avfoundation' (default mic is ':0')
  - Linux: Change '-f avfoundation' to '-f pulse' and '-i :0' to 'default'
  - Windows: Change '-f avfoundation' to '-f dshow' and '-i :0' to 'audio=Microphone'
    `);
    process.exit(0);
  }

  // Parse arguments
  let sampleRate = 16000;
  let channels = 1;
  let enableInterim = true;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === "--sample-rate") {
      sampleRate = parseInt(args[++i], 10);
    } else if (arg === "--channels") {
      channels = parseInt(args[++i], 10);
    } else if (arg === "--no-interim") {
      enableInterim = false;
    }
  }

  const stt = new StreamingSTT(sampleRate, channels, enableInterim);

  try {
    await stt.streamAudio();
  } catch (err) {
    console.error("❌ Error:", err);
    process.exit(1);
  }
}

// Run if called directly
const isMainModule = process.argv[1] === new URL(import.meta.url).pathname;
if (isMainModule) {
  main().catch((err) => {
    console.error("❌ Unhandled error:", err);
    process.exit(1);
  });
}

export { StreamingSTT };

