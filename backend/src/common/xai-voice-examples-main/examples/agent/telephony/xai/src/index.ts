import "dotenv-flow/config";
import express from "express";
import ExpressWs from "express-ws";
import * as crypto from "crypto";
import bot from "./bot";
import log from "./logger";
import type { CallStatus } from "./twilio";
import { TwilioMediaStreamWebsocket } from "./twilio";

const { app } = ExpressWs(express());
app.use(express.urlencoded({ extended: true })).use(express.json());

// ========================================
// Configuration
// ========================================
const XAI_API_KEY = process.env.XAI_API_KEY || "";
const API_URL = process.env.API_URL || "wss://api.x.ai/v1/realtime";

// ========================================
// Secure Event Logger (async, structured)
// ========================================
// NOTE: Use Winston or similar logging library in production
// This is a simple structured logger replacement for the insecure file logging
function logWebSocketEvent(callId: string, direction: 'SEND' | 'RECV', event: any) {
  const eventCopy = typeof event === 'string' ? JSON.parse(event) : event;

  // Skip logging raw audio chunks
  if (eventCopy.type === 'input_audio_buffer.append' ||
    eventCopy.type === 'response.output_audio.delta') {
    return;
  }

  // Log to console with structure (in production, use Winston/Bunyan)
  log.app.debug({
    timestamp: new Date().toISOString(),
    callId,
    direction,
    eventType: eventCopy.type,
    // Don't log full event to avoid sensitive data exposure
  });
}

// Helper to generate cryptographically secure IDs
function generateSecureId(prefix: string): string {
  return `${prefix}_${crypto.randomBytes(16).toString('hex')}`;
}

// ========================================
// Health Check Endpoint
// ========================================
app.get("/health", (req, res) => {
  const health = {
    status: "ok",
    timestamp: new Date().toISOString(),
  };
  res.json(health);
});

// ========================================
// Twilio Voice Webhook Endpoints
// ========================================
app.post("/twiml", async (req, res) => {
  const from = req.body.From;
  const to = req.body.To;
  log.twl.info(`twiml from ${from} to ${to}`);

  try {
    // Generate a cryptographically secure call ID
    const callId = generateSecureId('call');
    log.app.info(`[${callId}] Processing incoming call`);

    res.status(200);
    res.type("text/xml");

    // Extract domain from HOSTNAME (remove https:// if present)
    const hostname = process.env.HOSTNAME!.replace(/^https?:\/\//, '');
    const streamUrl = `wss://${hostname}/media-stream/${callId}`;
    log.app.info(`[${callId}] Generated WebSocket URL: ${streamUrl}`);
    log.app.info(`[${callId}] Using HOSTNAME: ${process.env.HOSTNAME}`);

    // The <Stream/> TwiML noun tells Twilio to send the call to the websocket endpoint below.
    const twimlResponse = `\
<Response>
  <Connect>
    <Stream url="${streamUrl}" />
  </Connect>
</Response>
`;
    log.app.info(`[${callId}] Sending TwiML response`);
    res.end(twimlResponse);
    log.app.info(`[${callId}] Incoming call processed successfully`);
  } catch (error) {
    log.app.error(`[${req.body.From}] Incoming call webhook failed:`, error);
    res.status(500).send();
  }
});

app.post("/call-status", async (req, res) => {
  const status = req.body.CallStatus as CallStatus;
  const callSid = req.body.CallSid;
  const from = req.body.From;
  const to = req.body.To;

  if (status === "error") {
    log.twl.error(`[${callSid}] call-status ERROR from ${from} to ${to}`);
  } else {
    log.twl.info(`[${callSid}] call-status ${status} from ${from} to ${to}`);
  }

  res.status(200).send();
});

// ========================================
// Twilio Media Stream Websocket Endpoint
// ========================================
app.ws("/media-stream/:callId", async (ws, req) => {
  const callId = req.params.callId;
  log.twl.info(`[${callId}] WebSocket initializing`);

  const tw = new TwilioMediaStreamWebsocket(ws);

  // Set up Twilio start event handler IMMEDIATELY (before async operations)
  tw.on("start", (msg) => {
    tw.streamSid = msg.start.streamSid;
    log.app.info(`[${callId}] Twilio WebSocket ready - streamSid: ${tw.streamSid}`);
  });

  // Create raw WebSocket connection to x.ai (since RealtimeClient doesn't work)
  log.app.info(`[${callId}] Connecting to XAI API...`);

  const WebSocket = require('ws');
  const xaiWs = new WebSocket(API_URL, {
    headers: {
      'Authorization': `Bearer ${XAI_API_KEY}`,
      'Content-Type': 'application/json'
    }
  });

  // Wait for x.ai WebSocket to be ready
  await new Promise((resolve, reject) => {
    const wsTimeout = setTimeout(() => {
      xaiWs.close();
      reject(new Error("x.ai WebSocket connection timeout"));
    }, 10000);

    xaiWs.on('open', () => {
      clearTimeout(wsTimeout);
      log.app.info(`[${callId}] x.ai WebSocket connected successfully`);
      log.app.info(`[${callId}] x.ai WebSocket readyState: ${xaiWs.readyState}`);
      resolve(null);
    });

    xaiWs.on('error', (error: any) => {
      clearTimeout(wsTimeout);
      log.app.error(`[${callId}] ❌ x.ai WebSocket error:`, error);
      reject(error);
    });
  });

  // ========================================
  // Audio Orchestration
  // ========================================
  log.app.info(`[${callId}] Setting up audio event handlers`);
  log.app.info(`[${callId}] 🎙️  Server-side VAD enabled`);

  // Handle messages from x.ai WebSocket
  xaiWs.on('message', (data: Buffer) => {
    try {
      const message = JSON.parse(data.toString());

      // Log to debug file (will filter out audio chunks)
      logWebSocketEvent(callId, 'RECV', message);

      // Log all events to console except raw audio chunks
      if (message.type !== 'response.output_audio.delta' && message.type !== 'input_audio_buffer.append') {
        log.app.info(`[${callId}] 📩 ${message.type}`);
      }

      if (message.type === 'response.output_audio.delta' && message.delta) {
        // Bot is speaking - sending audio to Twilio (PCMU format)
        // XAI sends μ-law directly (native PCMU support), pass through without conversion
        tw.send({
          event: "media",
          media: { payload: message.delta },  // Pass through base64 μ-law directly
          streamSid: tw.streamSid!,
        });
      } else if (message.type === 'response.output_audio_transcript.delta') {
        // Log bot's speech transcript (PCMU format uses output_audio_transcript)
        log.app.info(`[${callId}] 🤖 Bot: "${message.delta}"`);
      } else if (message.type === 'response.output_audio_transcript.delta') {
        // Log bot's speech transcript
        log.app.info(`[${callId}] 🤖 Bot: "${message.delta}"`);
      } else if (message.type === 'response.created') {
        log.app.info(`[${callId}] 🤖 BOT STARTED SPEAKING`);
      } else if (message.type === 'response.done') {
        log.app.info(`[${callId}] 🤖 BOT FINISHED SPEAKING - Listening for user...`);
      } else if (message.type === 'session.updated') {
        log.app.info(`[${callId}] ⚙️ Session updated - PCMU format confirmed`);

        // Now that session is configured, send initial greeting
        // TODO: why?
        // const commitMessage = { type: 'input_audio_buffer.commit' };
        // logWebSocketEvent(callId, 'SEND', commitMessage);
        // xaiWs.send(JSON.stringify(commitMessage));

        const conversationItem = {
          type: 'conversation.item.create',
          item: {
            type: 'message',
            role: 'user',
            content: [
              {
                type: 'input_text',
                text: 'Say hello and introduce yourself'
              }
            ]
          }
        };
        logWebSocketEvent(callId, 'SEND', conversationItem);
        xaiWs.send(JSON.stringify(conversationItem));

        const responseCreate = { type: 'response.create' };
        logWebSocketEvent(callId, 'SEND', responseCreate);
        xaiWs.send(JSON.stringify(responseCreate));

        log.app.info(`[${callId}] Initial greeting requested after session confirmation`);
        // TODO: hmm this is not an OAI event
        // Also remove input_audio_buffer.received_forced_commit
      } else if (message.type === 'conversation.created') {
        log.app.info(`[${callId}] 📞 Call connected - Using SERVER-SIDE VAD`);
        log.app.info(`[${callId}] 🆔 x.ai conversation_id: ${message.conversation?.id || 'unknown'}`);

        // Send session configuration
        const sessionConfig = {
          type: 'session.update',
          session: {
            instructions: bot.instructions,
            // TODO: confirm that this is taken from here and not query param
            voice: 'ara',
            audio: {
              input: {
                format: {
                  type: 'audio/pcmu',  // Native μ-law (PCMU) support
                },
              },
              output: {
                format: {
                  type: 'audio/pcmu',  // Native μ-law (PCMU) support
                },
              },
            },
            turn_detection: {
              type: 'server_vad',
            }
          }
        };
        logWebSocketEvent(callId, 'SEND', sessionConfig);
        xaiWs.send(JSON.stringify(sessionConfig));

        log.app.info(`[${callId}] Server-side VAD configured, waiting for session.updated...`);
      } else if (message.type === 'input_audio_buffer.speech_started') {
        log.app.info(`[${callId}] 🎤 USER STARTED SPEAKING (server VAD)`);
        log.app.info(`[${callId}]    VAD triggered at audio_start_ms: ${message.audio_start_ms}`);

        // Clear Twilio's audio buffer (interrupt bot if speaking)
        tw.send({ event: "clear", streamSid: tw.streamSid! });

      } else if (message.type === 'input_audio_buffer.speech_stopped') {
        log.app.info(`[${callId}] 🛑 USER STOPPED SPEAKING (server VAD detected ${message.audio_end_ms || message.audio_start_ms}ms of audio)`);
        log.app.info(`[${callId}] 🔄 Server will automatically process speech...`);

      } else if (message.type === 'input_audio_buffer.committed') {
        log.app.info(`[${callId}] Audio buffer committed (${message.item_id || 'no item_id'})`);
      } if (message.type === 'ping') {
        // Silently handle pings
      } else if (message.type === 'error') {
        log.app.error(`[${callId}] ❌ x.ai API ERROR:`);
        log.app.error(`[${callId}]    Type: ${message.error?.type || 'unknown'}`);
        log.app.error(`[${callId}]    Code: ${message.error?.code || 'unknown'}`);
        log.app.error(`[${callId}]    Message: ${message.error?.message || JSON.stringify(message)}`);
        log.app.error(`[${callId}]    Event ID: ${message.event_id || 'none'}`);
      } else if (message.type === 'conversation.item.added') {
        // Silently handle - conversation item added (same as created)
      } else if (message.type === 'response.output_item.added') {
        // Silently handle - output item added to response
      } else if (message.type === 'response.output_item.done') {
        // Silently handle - output item completed
      } else if (message.type === 'response.content_part.added') {
        // Silently handle - content part added
      } else if (message.type === 'response.content_part.done') {
        // Silently handle - content part completed
      } else if (message.type === 'response.output_audio.done') {
        // Silently handle - audio generation completed
      } else if (message.type === 'response.output_audio_transcript.done') {
        // Silently handle - transcript completed
      } else {
        // Log unknown events for debugging
        log.app.debug(`[${callId}] ❓ Unknown: ${message.type}`);
      }
    } catch (error) {
      log.app.error(`[${callId}] Error processing message from x.ai:`, error);
    }
  });

  // Send human speech to x.ai
  let audioPacketCount = 0;
  tw.on("media", (msg) => {
    try {
      audioPacketCount++;

      if (msg.media.track === 'inbound') {
        // XAI accepts μ-law (PCMU) natively - pass through without conversion
        const mulawBase64 = msg.media.payload;

        // Log periodically
        if (audioPacketCount === 1 || audioPacketCount % 100 === 0) {
          log.app.info(`[${callId}] 🎚️  Audio packet #${audioPacketCount} (server-side VAD active)`);
        }

        // Send μ-law audio directly to XAI (no conversion or buffering needed)
        const audioMessage = {
          type: "input_audio_buffer.append",
          audio: mulawBase64
        };

        // Check WebSocket state before sending
        if (xaiWs.readyState !== 1) {
          log.app.error(`[${callId}] ❌ Cannot send audio! x.ai WebSocket not connected (state: ${xaiWs.readyState})`);
          return;
        }

        // Note: Audio chunks are not logged to debug file (filtered in logWebSocketEvent)
        xaiWs.send(JSON.stringify(audioMessage));
      }
    } catch (error) {
      log.app.error(`[${callId}] Error processing audio from Twilio:`, error);
    }
  });

  // Handle x.ai WebSocket errors
  xaiWs.on('error', (error: any) => {
    log.app.error(`[${callId}] ❌ x.ai WebSocket ERROR:`, error);
  });

  xaiWs.on('close', (code: number, reason: Buffer) => {
    const reasonStr = reason.toString() || 'No reason provided';
    log.app.error(`[${callId}] ❌ x.ai WebSocket CLOSED - Code: ${code}, Reason: ${reasonStr}`);
  });

  // Handle Twilio WebSocket errors
  ws.on("error", (error) => {
    log.app.error(`[${callId}] Twilio WebSocket error:`, error);
  });

  // Handle x.ai WebSocket close
  ws.on("close", () => {
    log.app.info(`[${callId}] Twilio WebSocket closed, disconnecting x.ai`);
    xaiWs.close();
  });
});

/****************************************************
 Start Server
****************************************************/
const port = process.env.PORT || "3000";
app.listen(port, () => {
  log.app.info(`server running on http://localhost:${port}`);
});
