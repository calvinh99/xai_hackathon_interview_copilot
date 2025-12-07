#!/usr/bin/env node
/**
 * Streaming Text-to-Speech Example
 *
 * This example demonstrates how to use XAI's streaming TTS API to convert text to speech
 * in real-time using WebSocket connections. The audio is played as it's received and
 * optionally saved to a file.
 *
 * API: wss://api.x.ai/v1/realtime/audio/speech
 * Audio format: PCM linear16, 24kHz, mono
 */

import WebSocket from "ws";
import fs from "fs/promises";
import path from "path";
import { spawn } from "child_process";
import dotenv from "dotenv";

dotenv.config();

interface ConfigMessage {
  type: "config";
  data: {
    voice_id: string;
  };
}

interface TextChunkMessage {
  type: "text_chunk";
  data: {
    text: string;
    is_last: boolean;
  };
}

interface AudioResponse {
  data: {
    data: {
      audio: string; // base64
      is_last: boolean;
    };
  };
}

/**
 * Stream text-to-speech from XAI API
 */
async function streamingTTS(
  text: string,
  voice: string = "ara",
  outputFile?: string,
  playAudio: boolean = true
): Promise<Buffer> {
  // Get API key
  const apiKey = process.env.XAI_API_KEY;
  if (!apiKey) {
    throw new Error("XAI_API_KEY not found in environment variables");
  }

  // Get base URL
  const baseUrl = process.env.BASE_URL || "https://api.x.ai/v1";
  const wsUrl = baseUrl.replace("https://", "wss://").replace("http://", "ws://");
  const uri = `${wsUrl}/realtime/audio/speech`;

  console.log(`🎤 Connecting to ${uri}`);
  console.log(`📝 Voice: ${voice}`);
  console.log(`📄 Text: ${text.substring(0, 50)}${text.length > 50 ? "..." : ""}`);

  return new Promise((resolve, reject) => {
    const ws = new WebSocket(uri, {
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
    });

    const audioChunks: Buffer[] = [];
    let chunkCount = 0;
    let ffplayProcess: any = null;

    // Start ffplay for audio playback if needed
    if (playAudio) {
      try {
        ffplayProcess = spawn(
          "ffplay",
          [
            "-f",
            "s16le", // signed 16-bit little-endian PCM
            "-ar",
            "24000", // 24kHz sample rate
            "-ac",
            "1", // mono
            "-nodisp", // no video display
            "-autoexit", // exit when done
            "-loglevel",
            "quiet", // suppress ffplay logs
            "-",
          ],
          {
            stdio: ["pipe", "inherit", "inherit"],
          }
        );

        ffplayProcess.on("error", (err: Error) => {
          console.warn(
            "⚠️  Could not start audio playback (ffplay not found):",
            err.message
          );
          ffplayProcess = null;
        });
      } catch (err) {
        console.warn("⚠️  Could not start audio playback:", err);
        ffplayProcess = null;
      }
    }

    ws.on("open", () => {
      console.log("✅ Connected to XAI streaming TTS API");

      // Send config message
      const configMessage: ConfigMessage = {
        type: "config",
        data: {
          voice_id: voice,
        },
      };
      ws.send(JSON.stringify(configMessage));
      console.log(`📤 Sent config:`, configMessage);

      // Send text chunk
      const textMessage: TextChunkMessage = {
        type: "text_chunk",
        data: {
          text: text,
          is_last: true,
        },
      };
      ws.send(JSON.stringify(textMessage));
      console.log(`📤 Sent text chunk`);
      console.log("🎵 Receiving audio...");
    });

    ws.on("message", (data: WebSocket.Data) => {
      try {
        const message: AudioResponse = JSON.parse(data.toString());

        // Extract audio data
        const audioB64 = message.data.data.audio;
        const isLast = message.data.data.is_last;

        // Decode audio
        const audioBuffer = Buffer.from(audioB64, "base64");
        audioChunks.push(audioBuffer);
        chunkCount++;

        // Play audio in real-time
        if (ffplayProcess && ffplayProcess.stdin && !ffplayProcess.stdin.destroyed) {
          ffplayProcess.stdin.write(audioBuffer);
        }

        const lastIndicator = isLast ? " (last)" : "";
        console.log(`  📦 Chunk ${chunkCount}: ${audioBuffer.length} bytes${lastIndicator}`);

        if (isLast) {
          ws.close();
        }
      } catch (err) {
        console.error("❌ Error parsing message:", err);
      }
    });

    ws.on("close", async () => {
      console.log(`\n✅ Received ${chunkCount} audio chunks`);

      // Close ffplay
      if (ffplayProcess && ffplayProcess.stdin && !ffplayProcess.stdin.destroyed) {
        ffplayProcess.stdin.end();
      }

      // Combine all chunks
      const fullAudio = Buffer.concat(audioChunks);
      console.log(`📊 Total audio size: ${fullAudio.length} bytes`);

      // Save to file if requested
      if (outputFile) {
        try {
          // Ensure directory exists
          const outputDir = path.dirname(outputFile);
          await fs.mkdir(outputDir, { recursive: true });

          // Create WAV header
          const wavHeader = createWavHeader(fullAudio.length, 24000, 1, 16);
          const wavFile = Buffer.concat([wavHeader, fullAudio]);

          await fs.writeFile(outputFile, wavFile);
          console.log(`💾 Saved audio to ${outputFile}`);
        } catch (err) {
          console.error(`❌ Error saving file:`, err);
        }
      }

      resolve(fullAudio);
    });

    ws.on("error", (err) => {
      console.error("❌ WebSocket error:", err);
      reject(err);
    });
  });
}

/**
 * Create WAV file header
 */
function createWavHeader(
  dataLength: number,
  sampleRate: number,
  channels: number,
  bitsPerSample: number
): Buffer {
  const header = Buffer.alloc(44);

  // RIFF header
  header.write("RIFF", 0);
  header.writeUInt32LE(36 + dataLength, 4);
  header.write("WAVE", 8);

  // fmt chunk
  header.write("fmt ", 12);
  header.writeUInt32LE(16, 16); // fmt chunk size
  header.writeUInt16LE(1, 20); // audio format (1 = PCM)
  header.writeUInt16LE(channels, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE((sampleRate * channels * bitsPerSample) / 8, 28); // byte rate
  header.writeUInt16LE((channels * bitsPerSample) / 8, 32); // block align
  header.writeUInt16LE(bitsPerSample, 34);

  // data chunk
  header.write("data", 36);
  header.writeUInt32LE(dataLength, 40);

  return header;
}

/**
 * Main entry point
 */
async function main() {
  const args = process.argv.slice(2);

  if (args.includes("--help") || args.includes("-h") || args.length === 0) {
    console.log(`
Streaming Text-to-Speech using XAI API

Usage:
  npm start -- <text> [options]

Options:
  --voice <voice>     Voice to use (default: ara)
                      Available: ara, rex, sal, eve, una, leo
  --output <file>     Save audio to file (e.g., output.wav)
  -o <file>          Short form of --output
  --no-play          Don't play audio (only save to file)
  --help, -h         Show this help message

Examples:
  # Basic usage with default voice (Ara)
  npm start -- "Hello, how are you today?"

  # Specify voice
  npm start -- "Hello!" --voice rex

  # Save to file
  npm start -- "Hello!" --output output.wav

  # Disable playback (only save to file)
  npm start -- "Hello!" --output output.wav --no-play

Available voices:
  ara - Female voice (default)
  rex - Male voice
  sal - Voice (likely Salathiel)
  eve - Female voice
  una - Female voice
  leo - Male voice

Note: Audio playback requires ffplay (part of ffmpeg).
      Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)
    `);
    process.exit(0);
  }

  // Parse arguments
  let text = "";
  let voice = "ara";
  let outputFile: string | undefined = undefined;
  let playAudio = true;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === "--voice") {
      voice = args[++i];
    } else if (arg === "--output" || arg === "-o") {
      outputFile = args[++i];
    } else if (arg === "--no-play") {
      playAudio = false;
    } else if (!arg.startsWith("--")) {
      text = arg;
    }
  }

  if (!text) {
    console.error("❌ Error: No text provided");
    process.exit(1);
  }

  if (!playAudio && !outputFile) {
    console.error("❌ Error: --no-play requires --output to be specified");
    process.exit(1);
  }

  const validVoices = ["ara", "rex", "sal", "eve", "una", "leo"];
  if (!validVoices.includes(voice)) {
    console.error(
      `❌ Error: Invalid voice "${voice}". Must be one of: ${validVoices.join(", ")}`
    );
    process.exit(1);
  }

  try {
    await streamingTTS(text, voice, outputFile, playAudio);
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

export { streamingTTS };

