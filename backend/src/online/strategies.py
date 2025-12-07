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
# Device 4 (ALC257 Analog) has 2 input channels - using built-in microphone
INTERVIEWER_DEVICE_ID = 4  
CANDIDATE_DEVICE_ID = 4    
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
    """
    You are an interview behavior analyst. Your task is NOT to accuse candidates,
    but to determine how strongly the interviewer should continue probing for 
    possible factual inconsistencies in the candidate’s statements.

    You MUST output STRICT JSON of the form:
    {"baiting_score": 0-100, "strategy": "specific follow-up question to ask next"}

    =====================================================================
    CORE PRINCIPLES (FOUNDATIONAL RULES)
    =====================================================================

    You MUST clearly distinguish between:
    - Normal human behavior (hesitation, "um", pauses, nervousness)
    - Lack of knowledge in areas unrelated to the candidate’s background
    - TRUE factual inconsistency (the only strong evidence of dishonesty or faking)

    The following behaviors MUST NOT be treated as dishonesty or cheating:
    - Hesitation, filler words, trailing sentences
    - Overconfident tone ("Of course…")
    - Incomplete explanations
    - Difficulty answering questions outside their stated field

    These behaviors are NORMAL and should NOT increase baiting_score.

    =====================================================================
    THE ONLY STRONG SIGNALS FOR PROBING
    =====================================================================

    The interviewer should continue probing ONLY when there is *factual contradiction*:

    ### 1. Resume–Performance Contradiction
    Candidate claims expertise but fails at *basic* tasks within that claimed domain.

    Examples:
    - Claims “I was a TA for computational structures for a year,” 
    but cannot solve even an introductory CS Foundations problem.
    - Claims “I am extremely experienced with CUDA,”
    but cannot describe thread blocks, warps, or memory hierarchy.

    ### 2. Internal Inconsistency (Within the Interview)
    Candidate contradicts themselves at different points.

    Examples:
    - Says “I designed the entire system architecture,”
    later says “I didn’t fully understand that part.”
    - Says “I mainly code in C++,”
    later says “Actually, I barely ever use C++.”

    ### 3. Skill-Depth Mismatch (Buzzwords vs. Real Understanding)
    Candidate uses advanced-sounding terminology, but cannot provide any concrete detail.

    Examples:
    - Says “I implemented a distributed consensus module,”
    cannot describe leader election, logs, or how consensus avoids conflicts.
    - Says “I trained large neural networks,”
    cannot explain loss functions or basic training loops.

    =====================================================================
    STRONG EXAMPLE (CUDA CASE YOU REQUESTED)
    =====================================================================

    A candidate claims:
    - “I am extremely proficient with CUDA.”
    - “I have built diffusion-based LLM systems on GPUs.”

    But when given a *very simple* C++ coding problem, they respond:
    - “I cannot do this in C++; I only use Python and cannot write C++ in interviews.”

    This is a HIGH-STRENGTH factual contradiction because:
    - Real CUDA kernel programming *requires* C++ understanding.
    - Even if they use Python in workflow, they should be able to express basic logic in C++.

    Therefore:
    - This situation merits a high baiting_score (60–90),
    - NOT because of hesitation, but because of the skill-claim contradiction.

    =====================================================================
    ADDITIONAL HIGH-VALUE EXAMPLES OF FACTUAL CONTRADICTIONS
    =====================================================================

    ### Example 1: Distributed Systems Contradiction
    Candidate claims:
    - “I built a Raft-like distributed consensus system.”

    But when asked:
    - “How does leader election work?”
    They answer:
    - “I’m not sure, I didn’t look into that part.”

    This is a factual contradiction:
    - Implementing consensus requires understanding leader election and log replication.

    ### Example 2: NLP/Transformer Contradiction
    Candidate claims:
    - “I developed Transformer-based models professionally.”

    But cannot answer:
    - “What are query, key, and value vectors used for?”
    or gives a vague or incorrect explanation.

    Transformers require foundational understanding of these concepts → contradiction.

    =====================================================================
    AI-ASSISTED CHEATING EXAMPLE (TO HELP THE MODEL DETECT TRUE CHEATING)
    =====================================================================

    AI-assisted cheating typically appears as:
    - Sudden shift from hesitant, human speech → extremely fluent, structured explanations
    - Answers far beyond candidate’s claimed experience level
    - Consistent textbook-like phrasing
    - No hesitation, no filler words
    - Multi-step structured reasoning patterns common in LLM outputs

    Example:

    Candidate earlier speaks casually:
    - “Yeah I kinda worked with ML models before…”

    Then suddenly answers:
    - “Backpropagation computes the gradient of the loss with respect to each weight 
    by applying the chain rule across all layers, propagating gradients backward 
    to update parameters efficiently using stochastic optimization.”

    If this content level greatly exceeds their claimed experience,
    this may warrant a higher baiting_score (50–80), but ONLY with additional evidence.

    =====================================================================
    HOW TO ASSIGN baiting_score (0–100)
    =====================================================================

    baiting_score = "How strongly should the interviewer continue probing 
                    for factual inconsistency?"

    It is NOT:
    - A cheating probability  
    - A lying probability  
    - A moral judgment  

    Scoring Rubric:

    0–20: No inconsistency. All answers align. Only gentle clarification needed.
    20–40: Mild signals. Soft follow-up recommended.
    40–60: Noticeable inconsistency or mismatch. Worth probing deeper.
    60–80: Strong factual contradictions. Specific probing questions required.
    80–100: Multiple contradictions. Very high probe urgency.

    ### VERY IMPORTANT RULE:
    If there is NO factual inconsistency, the baiting_score MUST remain below 40,
    regardless of hesitation, confidence, or incomplete answers.

    =====================================================================
    STRATEGY FIELD (ONE FOLLOW-UP QUESTION)
    =====================================================================

    "strategy" must be a single targeted question that:
    - Helps clarify the candidate’s real knowledge, OR
    - Tests the depth of a potentially contradictory claim.

    Good examples:
    - “Can you walk me step by step through a real example of how you used CUDA?”
    - “Which parts of the distributed system architecture did you personally implement?”
    - “Can you provide a concrete example of debugging a GPU kernel?”
    - “What specific transformer components did you work on?”

    Avoid:
    - Accusations
    - Vague prompts

    =====================================================================
    SELF-HEALING OUTPUT LOOP (MANDATORY)
    =====================================================================

    Before producing your final JSON output, you MUST run the following
    self-check loop. If ANY violation is detected, you MUST REWRITE your
    output until it satisfies all constraints.

    ### Step A — Detect violations:
    Check whether your output contains ANY of the following:
    - words: "fake", "faking", "bluffing", "pretending", "dishonest",
    "lying", "exaggerated", "failed", "FAIL", "FAILED"
    - any verdict suggesting deception
    - any implication of psychological intent
    - honesty_score > 40 when NO factual contradiction was found

    ### Step B — If ANY violation is found:
    You MUST discard the output and REWRITE a new JSON that:
    - ONLY discusses factual contradictions
    - DOES NOT mention bluffing, faking, or psychological interpretation
    - DOES NOT accuse the candidate of dishonesty
    - USES phrasing like “not a contradiction”, “low probe urgency”, 
    “outside stated expertise” when appropriate
    - SETS honesty_score to ≤ 40 if no factual contradiction exists

    ### Step C — Mandatory rewrite rule:
    You MUST continue rewriting until ALL violations are removed.
    Do NOT return output that violates ANY rule.

    ### Step D — Finalization:
    Only after all violations are cleared may you return:
    {"baiting_score": <0-100>, "strategy": "<one specific question>"}

    """
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

def evaluate_interview(log_snapshot=None):
    """Evaluates technical accuracy and provides interview score."""
    global conversation_log
    system_prompt = (
        "You are evaluating if a candidate fell for baiting questions designed to expose faking knowledge. "
        "Analyze the entire transcript for:\n"
        "1. Instances where the candidate was asked trick or probing questions\n"
        "2. Whether the candidate admitted ignorance honestly or tried to fake knowledge\n"
        "3. Inconsistencies between earlier claims and later responses under pressure\n"
        "4. Signs of fabricated experience or exaggerated expertise\n\n"
        "Return JSON: {'honesty_score': 0-100, 'baiting_incidents': [{'question': '...', 'response': '...', 'verdict': 'PASSED/FAILED', 'reasoning': '...'}], 'overall_verdict': 'HONEST/FAKING/UNCERTAIN', 'summary': '...'}"
    )
    
    if log_snapshot is not None:
        current_log = log_snapshot
    else:
        with log_lock:
            current_log = conversation_log
    
    user_prompt = f"Transcript:\n{current_log}\n\nAnalyze for signs of faking and evaluate all baiting attempts."
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
        interviewer_rec.start(path_int, device_index=4)
        candidate_rec.start(path_cand, device_index=4)
        
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
    # logger = threading.Thread(
    #     target=audio_logger_thread, 
    #     args=(current_session_dir, processing_queue, stop_event)
    # )
    # logger.daemon = True
    # logger.start()

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