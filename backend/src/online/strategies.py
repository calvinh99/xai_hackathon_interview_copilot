import os
import time
import threading
import shutil
from datetime import datetime
from queue import Queue, Empty

# Importing your specific audio recorder
from ..online.audio import SystemAudioRecorder
from ..online.audio import audio_to_text
from ..common.grok import call_grok

# --- Configuration ---
INTERVIEWER_DEVICE_ID = 5  
CANDIDATE_DEVICE_ID = 2    
CHUNK_DURATION = 8         

# --- Global State ---
conversation_log = ""
current_session_dir = ""
log_lock = threading.Lock() 

def create_session_directory():
    """Creates a unique folder for this interview session."""
    # todo: allow it to go from existing session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join("logs", f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    os.makedirs(os.path.join(session_dir, "audio_interviewer"), exist_ok=True)
    os.makedirs(os.path.join(session_dir, "audio_candidate"), exist_ok=True)
    return session_dir

def checkpoint_conversation():
    """Save transcript to the session folder."""
    global conversation_log, current_session_dir
    if not current_session_dir: return
    
    filepath = os.path.join(current_session_dir, "full_transcript.txt")
    try:
        with log_lock:
            current_log = conversation_log
            
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(current_log)
    except Exception as e:
        print(f"Error saving checkpoint: {e}")
        
def restore_conversation():
    """Restores the last conversation log if exists."""
    global conversation_log, current_session_dir
    if not current_session_dir: return
    
    filepath = os.path.join(current_session_dir, "full_transcript.txt")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                with log_lock:
                    conversation_log = f.read()
        except Exception as e:
            print(f"Error restoring conversation: {e}")


# --- AI Logic (FIXED) ---
# Now accepts optional log_snapshot parameter to use thread-safe snapshots

def bait(log_snapshot=None):
    """Generates deception detection strategy.
    
    Returns JSON with baiting_score (0-100) and strategy (trick question to ask).
    """
    global conversation_log
    system_prompt = (
        "You are a lie-detection expert. Analyze the transcript for inconsistencies. "
        "Return JSON: {'baiting_score': 0-100, 'strategy': 'Specific trick question to ask'}"
    )
    
    if log_snapshot is not None:
        current_log = log_snapshot
    else:
        with log_lock:
            current_log = conversation_log
        
    user_prompt = f"Transcript:\n{current_log}\n\nAnalyze for deception and provide a baiting strategy."
    # print(user_prompt)
    return call_grok(user_prompt, system_prompt, is_reasoning=True) 

def hint(log_snapshot=None):
    """Generates technical follow-up questions based on candidate's answers."""
    global conversation_log
    system_prompt = (
        "You are a technical interviewer assistant. Based on the candidate's last answer, "
        "generate 3 deep technical follow-up questions that probe their actual understanding. "
        "Focus on areas where they might be faking knowledge."
    )
    
    if log_snapshot is not None:
        current_log = log_snapshot
    else:
        with log_lock:
            current_log = conversation_log
        
    user_prompt = f"Transcript:\n{current_log}\n\nGenerate technical follow-up questions."
    return call_grok(user_prompt, system_prompt, is_reasoning=True)

def eval_baiting(response, strategy):
    """Evaluates if the candidate fell for the bait."""
    system_prompt = (
        "You are evaluating if a candidate fell for a baiting question designed to expose faking. "
        "Did the candidate admit ignorance honestly, or did they try to fake knowledge? "
        "Verdict: PASSED (honest) or FAILED (tried to fake it). Explain your reasoning."
    )
    user_prompt = f"Baiting Strategy Used: {strategy}\nCandidate's Response: {response}\n\nEvaluate."
    return call_grok(user_prompt, system_prompt, is_reasoning=True)

def evaluate_interview(log_snapshot=None):
    """Evaluates technical accuracy and provides interview score."""
    global conversation_log
    system_prompt = (
        "You are an expert interview evaluator. Analyze the transcript and evaluate:\n"
        "1. Technical depth and accuracy of the candidate's answers\n"
        "2. Consistency of their claims throughout the interview\n"
        "3. Signs of genuine knowledge vs potential faking\n"
        "Return JSON: {'interview_score': 0-100, 'strengths': [...], 'concerns': [...], 'recommendation': 'PASS/FAIL/UNCERTAIN'}"
    )
    
    if log_snapshot is not None:
        current_log = log_snapshot
    else:
        with log_lock:
            current_log = conversation_log
    
    user_prompt = f"Transcript:\n{current_log}\n\nProvide comprehensive evaluation."
    return call_grok(user_prompt, system_prompt, is_reasoning=True)


# --- Dedicated Audio Logging Thread (Producer) ---

def audio_logger_thread(session_dir, processing_queue, stop_event):
    global INTERVIEWER_DEVICE_ID, CANDIDATE_DEVICE_ID
    interviewer_rec = SystemAudioRecorder()
    candidate_rec = SystemAudioRecorder()
    chunk_index = 0
    
    print(f"🎙️ [Audio Logger] Started in: {session_dir}")

    while not stop_event.is_set():
        filename = f"chunk_{chunk_index:04d}.wav"
        path_int = os.path.join(session_dir, "audio_interviewer", filename)
        path_cand = os.path.join(session_dir, "audio_candidate", filename)
        
        # 1. Start Recording
        # print(conversation_log, "!!!!!!!!!!!!!!!!")
        interviewer_rec.start(path_int, device_index=INTERVIEWER_DEVICE_ID)
        candidate_rec.start(path_cand, device_index=CANDIDATE_DEVICE_ID)
        
        # 2. Record
        time.sleep(CHUNK_DURATION)
        
        # 3. Stop
        interviewer_rec.stop()
        candidate_rec.stop()
        
        # 4. Notify Consumer
        processing_queue.put((path_int, path_cand))
        chunk_index += 1

# --- Main Driver ---

def launch_threads(if_checkpoint, if_generate, if_evaluate, report_analysis):
    """
    Launch the interview copilot threads.
    
    Args:
        if_checkpoint: Function that returns True when checkpoint should happen
        if_generate: Function that returns True when hints/baiting strategies should be generated
        if_evaluate: Function that returns True when interview evaluation should run
        report_analysis: Callback to report analysis results to frontend - signature: report_analysis(result, mode)
    """
    global conversation_log, current_session_dir
    
    current_session_dir = create_session_directory()
    # restore_conversation()  
    stop_event = threading.Event()
    processing_queue = Queue()

    # --- 1. Audio Logger Thread ---
    logger = threading.Thread(
        target=audio_logger_thread, 
        args=(current_session_dir, processing_queue, stop_event)
    )
    logger.daemon = True
    logger.start()

    def analysis_worker(snapshot_log, mode):
        """
        Helper for AI calls, runs in its own ephemeral thread.
        
        Calls the appropriate AI functions (bait, hint, evaluate_interview)
        and reports results via report_analysis callback.
        """
        try:
            if mode == "generate":
                # Generate baiting strategies & score
                bait_result = bait(snapshot_log)
                report_analysis(bait_result, "bait")
                
                # Generate technical follow-up hints
                hint_result = hint(snapshot_log)
                report_analysis(hint_result, "hint")
                
            elif mode == "evaluate":
                # Evaluate interview with score
                eval_result = evaluate_interview(snapshot_log)
                report_analysis(eval_result, "evaluate")
                
        except Exception as e:
            print(f"⚠️ [Analysis Error in {mode}]: {e}")

    # --- 2. Transcriber Loop (Consumer) ---
    def transcription_loop():
        global conversation_log
        print("🧠 [Transcriber] Waiting for audio chunks...")
        
        while not stop_event.is_set():
            try:
                path_int, path_cand = processing_queue.get(timeout=1)
                
                txt_int = audio_to_text(path_int)
                txt_cand = audio_to_text(path_cand)
                
                with log_lock:
                    if txt_int and len(txt_int.strip()) > 0:
                        line = f"Interviewer: {txt_int}"
                        conversation_log += f"\n{line}"
                        print(f"🗣️ You: {txt_int}")

                    if txt_cand and len(txt_cand.strip()) > 0:
                        line = f"Candidate: {txt_cand}"
                        conversation_log += f"\n{line}"
                        print(f"👤 They: {txt_cand}")
                
                if if_checkpoint():
                    checkpoint_conversation()
                
                processing_queue.task_done()

            except Empty:
                continue 
            except Exception as e:
                print(f"⚠️ [Processing Error]: {e}")

    # --- 3. UI Monitor Loop (Controller) ---
    def ui_monitor_loop():
        global conversation_log
        print("⚡ [UI Monitor] Watching for user triggers...")

        while not stop_event.is_set():
            try:
                trigger_gen = if_generate()
                trigger_eval = if_evaluate()

                if trigger_gen or trigger_eval:
                    # Snapshot the current log immediately for thread safety
                    with log_lock:
                        current_snapshot = conversation_log

                    if trigger_gen:
                        t = threading.Thread(target=analysis_worker, args=(current_snapshot, "generate"))
                        t.daemon = True
                        t.start()
                    
                    if trigger_eval:
                        t = threading.Thread(target=analysis_worker, args=(current_snapshot, "evaluate"))
                        t.daemon = True
                        t.start()
                
                time.sleep(0.1)

            except Exception as e:
                print(f"⚠️ [UI Monitor Error]: {e}")
                time.sleep(1)

    # Start threads
    processor = threading.Thread(target=transcription_loop)
    processor.daemon = True
    processor.start()

    monitor = threading.Thread(target=ui_monitor_loop)
    monitor.daemon = True
    monitor.start()

    return stop_event