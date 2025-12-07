/**
 * XAI Speech-to-Text (STT) Example - Node.js/TypeScript
 * 
 * Converts audio files to text using XAI's transcription API.
 */

import "dotenv/config";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import FormData from "form-data";
import axios from "axios";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const XAI_API_KEY = process.env.XAI_API_KEY || "";
const BASE_URL = process.env.BASE_URL || "https://api.x.ai/v1";
const API_URL = `${BASE_URL}/audio/transcriptions`;

// Audio directory
const AUDIO_DIR = path.join(__dirname, "..", "audio");

interface TranscriptionResult {
  text: string;
  [key: string]: any;
}

/**
 * Transcribe an audio file using XAI API
 */
async function transcribeAudio(audioFilePath: string): Promise<TranscriptionResult> {
  if (!XAI_API_KEY) {
    throw new Error("XAI_API_KEY not found in environment variables");
  }

  if (!fs.existsSync(audioFilePath)) {
    throw new Error(`Audio file not found: ${audioFilePath}`);
  }

  const fileName = path.basename(audioFilePath);
  const fileStats = fs.statSync(audioFilePath);

  console.log(`Transcribing audio file: ${fileName}`);
  console.log(`  Size: ${fileStats.size} bytes`);

  try {
    // Create form data
    const formData = new FormData();
    formData.append("file", fs.createReadStream(audioFilePath), {
      filename: fileName,
      contentType: fileName.endsWith(".mp3") ? "audio/mpeg" : "audio/wav",
    });

    // Make API request using axios (handles FormData better than fetch)
    const response = await axios.post(API_URL, formData, {
      headers: {
        Authorization: `Bearer ${XAI_API_KEY}`,
        ...formData.getHeaders(),
      },
    });

    const result = response.data;

    console.log(`Transcription complete`);
    console.log(`   Text: ${result.text || "N/A"}`);

    return result;
  } catch (error: any) {
    if (error.response) {
      console.error(`❌ Error: API Error: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
      throw new Error(`API Error: ${error.response.status} - ${JSON.stringify(error.response.data)}`);
    } else {
      console.error(`❌ Error: ${error}`);
      throw error;
    }
  }
}

/**
 * Main function with examples
 */
async function main() {
  console.log("=".repeat(60));
  console.log("XAI Speech-to-Text Example");
  console.log("=".repeat(60));

  // Test all audio files
  const audioFiles = ["mono.mp3", "mono.wav", "stereo.mp3", "stereo.wav"];

  const results: Array<{
    file: string;
    success: boolean;
    text?: string;
    error?: string;
  }> = [];

  for (const audioFile of audioFiles) {
    const audioPath = path.join(AUDIO_DIR, audioFile);
    if (fs.existsSync(audioPath)) {
      console.log();
      try {
        const result = await transcribeAudio(audioPath);
        results.push({
          file: audioFile,
          success: true,
          text: result.text || "",
        });
      } catch (error) {
        console.error(`Failed to transcribe ${audioFile}: ${error}`);
        results.push({
          file: audioFile,
          success: false,
          error: String(error),
        });
      }
    } else {
      console.log(`\n⚠️  Audio file not found: ${audioFile}`);
    }
  }

  // Summary
  console.log();
  console.log("=".repeat(60));
  console.log("Summary");
  console.log("=".repeat(60));
  for (const result of results) {
    const status = result.success ? "✅" : "❌";
    console.log(`${status} ${result.file}`);
    if (result.success && result.text) {
      const truncated = result.text.substring(0, 80);
      console.log(`   ${truncated}${result.text.length > 80 ? "..." : ""}`);
    }
  }
  console.log("=".repeat(60));
}

// Run main function
main().catch(console.error);

