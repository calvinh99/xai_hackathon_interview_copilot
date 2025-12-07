/**
 * XAI Text-to-Speech (TTS) Example - Node.js/TypeScript
 * 
 * Converts text to speech using XAI's audio API.
 */

import "dotenv/config";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const XAI_API_KEY = process.env.XAI_API_KEY || "";
const BASE_URL = process.env.BASE_URL || "https://api.x.ai/v1";
const API_URL = `${BASE_URL}/audio/speech`;

// Output directory
const OUTPUT_DIR = path.join(__dirname, "..", "audio");
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

interface TTSOptions {
  text: string;
  voice?: string;
  responseFormat?: string;
  outputFile?: string;
}

/**
 * Convert text to speech using XAI API
 */
async function textToSpeech({
  text,
  voice = "Ara",
  responseFormat = "mp3",
  outputFile,
}: TTSOptions): Promise<string> {
  if (!XAI_API_KEY) {
    throw new Error("XAI_API_KEY not found in environment variables");
  }

  // Generate output filename if not provided
  if (!outputFile) {
    outputFile = `speech_${voice.toLowerCase()}.${responseFormat}`;
  }

  const outputPath = path.join(OUTPUT_DIR, outputFile);

  console.log(`Converting text to speech...`);
  console.log(`  Text: ${text.substring(0, 50)}${text.length > 50 ? "..." : ""}`);
  console.log(`  Voice: ${voice}`);
  console.log(`  Format: ${responseFormat}`);

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${XAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        input: text,
        voice: voice,
        response_format: responseFormat,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }

    // Save audio file
    const buffer = Buffer.from(await response.arrayBuffer());
    fs.writeFileSync(outputPath, buffer);

    console.log(`Audio saved to: ${outputPath}`);
    console.log(`   Size: ${buffer.length} bytes`);

    return outputPath;
  } catch (error) {
    console.error(`❌ Error: ${error}`);
    throw error;
  }
}

/**
 * Main function with examples
 */
async function main() {
  console.log("=".repeat(60));
  console.log("XAI Text-to-Speech Example");
  console.log("=".repeat(60));

  // Test text for all voices
  const testText = "Hello! This is a test of the XAI text-to-speech API. I hope you enjoy listening to my voice.";

  // Available voices
  const voices: Array<[string, string]> = [
    ["Ara", "Female"],
    ["Rex", "Male"],
    ["Sal", "Voice"],
    ["Eve", "Female"],
    ["Una", "Female"],
    ["Leo", "Male"],
  ];

  console.log(`\nTesting all ${voices.length} voices...`);
  console.log();

  // Test each voice
  for (const [voiceName, voiceType] of voices) {
    console.log(`Voice: ${voiceName} (${voiceType})`);
    await textToSpeech({
      text: testText,
      voice: voiceName,
      responseFormat: "mp3",
      outputFile: `${voiceName.toLowerCase()}_sample.mp3`,
    });
    console.log();
  }

  console.log("=".repeat(60));
  console.log(`All audio files saved to: ${OUTPUT_DIR}`);
  console.log("=".repeat(60));
}

// Run main function
main().catch(console.error);

