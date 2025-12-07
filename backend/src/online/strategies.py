"""
Interview Copilot - Live interview strategies with streaming STT.

Uses xAI's WebSocket streaming STT for real-time transcription of
interviewer and candidate audio streams.
"""

import os
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ..common.grok import call_grok
from .streaming_stt import DualStreamingSTT

# --- Configuration ---
INTERVIEWER_DEVICE_ID = 2
CANDIDATE_DEVICE_ID = 1

# Session directory base (relative to backend/)
SESSION_BASE_DIR = Path(__file__).parent.parent.parent / "online_logs"

# --- Global State ---
conversation_log = ""
current_session_dir = ""
_session_start_time: Optional[datetime] = None
log_lock = threading.Lock()

# Callback for transcript updates (set by launch_threads)
_transcript_callback: Optional[Callable[[str, str, bool], None]] = None


def create_session_directory():
    """Creates a unique folder for this interview session."""
    global _session_start_time
    _session_start_time = datetime.now()
    timestamp = _session_start_time.strftime("%Y%m%d_%H%M%S")
    session_dir = SESSION_BASE_DIR / f"interview_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return str(session_dir)


def checkpoint_conversation():
    """Save transcript to the session folder."""
    global conversation_log, current_session_dir
    if not current_session_dir:
        return

    filepath = os.path.join(current_session_dir, "full_transcript.txt")
    try:
        with log_lock:
            current_log = conversation_log

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(current_log)
    except Exception as e:
        print(f"Error saving checkpoint: {e}")


# --- AI Logic ---

def _get_log(snapshot=None):
    if snapshot is not None:
        return snapshot
    with log_lock:
        return conversation_log


def bait(log_snapshot=None):
    """Generates deception detection strategy."""
    system_prompt = (
        "You are a lie-detection expert. Analyze the transcript for inconsistencies. "
        "Return JSON: {'baiting_score': 0-100, 'strategy': 'Specific trick question to ask'}"
    )
    return call_grok(
        f"Transcript:\n{_get_log(log_snapshot)}\n\nAnalyze for deception and provide a baiting strategy.",
        system_prompt, is_reasoning=True
    )


def hint(log_snapshot=None):
    """Generates technical follow-up questions."""
    system_prompt = (
        "You are a technical interviewer assistant. Based on the candidate's last answer, "
        "generate 3 deep technical follow-up questions that probe their actual understanding. "
        "Focus on areas where they might be faking knowledge."
    )
    return call_grok(
        f"Transcript:\n{_get_log(log_snapshot)}\n\nGenerate technical follow-up questions.",
        system_prompt, is_reasoning=True
    )


def evaluate_interview(log_snapshot=None):
    """Evaluates interview for signs of faking knowledge."""
    system_prompt = (
        "You are evaluating if a candidate fell for baiting questions designed to expose faking knowledge. "
        "Analyze the entire transcript for:\n"
        "1. Instances where the candidate was asked trick or probing questions\n"
        "2. Whether the candidate admitted ignorance honestly or tried to fake knowledge\n"
        "3. Inconsistencies between earlier claims and later responses under pressure\n"
        "4. Signs of fabricated experience or exaggerated expertise\n\n"
        "Return JSON: {'honesty_score': 0-100, 'baiting_incidents': [...], 'overall_verdict': 'HONEST/FAKING/UNCERTAIN', 'summary': '...'}"
    )
    return call_grok(
        f"Transcript:\n{_get_log(log_snapshot)}\n\nAnalyze for signs of faking and evaluate all baiting attempts.",
        system_prompt, is_reasoning=True
    )


# --- Streaming STT Callback ---

def _get_timestamp():
    """Get elapsed time since session start as [MM:SS]."""
    if not _session_start_time:
        return "[00:00]"
    elapsed = datetime.now() - _session_start_time
    mins, secs = divmod(int(elapsed.total_seconds()), 60)
    return f"[{mins:02d}:{secs:02d}]"


def _on_transcript(speaker: str, text: str, is_final: bool):
    """Called when a transcript arrives from streaming STT."""
    global conversation_log, _transcript_callback

    if is_final:
        timestamp = _get_timestamp()
        with log_lock:
            conversation_log += f"\n{timestamp} {speaker}: {text}"
            print(f"{'🗣️' if speaker == 'Interviewer' else '👤'} {timestamp} {speaker}: {text}")

    if _transcript_callback:
        _transcript_callback(speaker, text, is_final)


# --- Main Driver ---

def launch_threads(
    if_checkpoint: Callable[[], bool],
    if_generate: Callable[[], bool],
    if_evaluate: Callable[[], bool],
    report_analysis: Callable[[str, str], None],
    report_transcript: Optional[Callable[[str, str, bool], None]] = None,
):
    """
    Launch the interview copilot with streaming STT.

    Args:
        if_checkpoint: Function that returns True when checkpoint should happen
        if_generate: Function that returns True when strategies should be generated
        if_evaluate: Function that returns True when interview evaluation should run
        report_analysis: Callback to report analysis results - signature: (result, mode)
        report_transcript: Callback to report transcript updates - signature: (speaker, text, is_final)
    """
    global conversation_log, current_session_dir, _transcript_callback, INTERVIEWER_DEVICE_ID, CANDIDATE_DEVICE_ID

    current_session_dir = create_session_directory()
    _transcript_callback = report_transcript

    stop_event = threading.Event()

    # --- 1. Start Streaming STT (with audio saving) ---
    dual_stt = DualStreamingSTT(
        interviewer_device_id=INTERVIEWER_DEVICE_ID,
        candidate_device_id=CANDIDATE_DEVICE_ID,
        on_transcript=_on_transcript,
        session_dir=current_session_dir,
    )
    dual_stt.start()
    print(f"🎙️ [Streaming STT] Started for devices {INTERVIEWER_DEVICE_ID} and {CANDIDATE_DEVICE_ID}")
    print(f"📁 Session: {current_session_dir}")

    # --- 2. Analysis Worker ---
    def save_strategy(result: str, strategy_type: str):
        """Save strategy result to session directory."""
        if not current_session_dir:
            return
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{strategy_type}_{timestamp}.txt"
        filepath = Path(current_session_dir) / filename
        try:
            filepath.write_text(result, encoding="utf-8")
            print(f"📝 Saved {strategy_type} to {filename}")
        except Exception as e:
            print(f"⚠️ Failed to save {strategy_type}: {e}")

    def analysis_worker(snapshot_log, mode):
        """Run AI analysis in a separate thread."""
        try:
            if mode == "generate":
                bait_result = bait(snapshot_log)
                report_analysis(bait_result, "bait")
                save_strategy(bait_result, "bait")

                hint_result = hint(snapshot_log)
                report_analysis(hint_result, "hint")
                save_strategy(hint_result, "hint")

            elif mode == "evaluate":
                eval_result = evaluate_interview(snapshot_log)
                report_analysis(eval_result, "evaluate")
                save_strategy(eval_result, "evaluate")

        except Exception as e:
            print(f"⚠️ [Analysis Error in {mode}]: {e}")

    # --- 3. UI Monitor Loop ---
    def ui_monitor_loop():
        print("⚡ [UI Monitor] Watching for user triggers...")

        while not stop_event.is_set():
            try:
                if if_checkpoint():
                    checkpoint_conversation()

                do_gen, do_eval = if_generate(), if_evaluate()
                if do_gen or do_eval:
                    with log_lock:
                        snapshot = conversation_log
                    if do_gen:
                        threading.Thread(target=analysis_worker, args=(snapshot, "generate"), daemon=True).start()
                    if do_eval:
                        threading.Thread(target=analysis_worker, args=(snapshot, "evaluate"), daemon=True).start()

                time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ [UI Monitor Error]: {e}")
                time.sleep(1)

        dual_stt.stop()
        checkpoint_conversation()  # Save final transcript
        print(f"🛑 [Streaming STT] Stopped - session saved to {current_session_dir}")

    threading.Thread(target=ui_monitor_loop, daemon=True).start()
    return stop_event
