#!/usr/bin/env python3
"""
Test driver for interview copilot strategy module.
Controls: c=checkpoint, g=generate, e=evaluate, s=show log, a=add snippet, q=quit
"""

import threading
import time
from datetime import datetime

import backend.src.online.strategies as strategies

# Flags controlled by terminal input
trigger_checkpoint = threading.Event()
trigger_generate = threading.Event()
trigger_evaluate = threading.Event()
stop_program = threading.Event()

SEED_CONVERSATION = """
Interviewer: Hi, welcome to the interview. Can you tell me about your experience with distributed systems?

Candidate: Thank you for having me. I have about 1 years of experience working with distributed systems.

Interviewer: Can you explain how backpropagation works in neural networks?

Candidate: Of course. Backpropagation is the algorithm used to calculate gradients in neural networks. It works by... um... computing the loss function and then... propagating the errors backward through the network layers.



"""

ADDITIONAL_SNIPPETS = [
    """
Interviewer: You mentioned you've worked with Kubernetes. Can you explain how pod scheduling works?

Candidate: Sure, Kubernetes uses a scheduler to assign pods to nodes. It considers resource requirements, affinity rules, and... various constraints.
""",
    """
Interviewer: Can you explain the CAP theorem?

Candidate: CAP theorem states that in a distributed system, you can only have two out of three guarantees: Consistency, Availability, and Partition tolerance.
"""
]

snippet_index = 0


def report_analysis(result, mode):
    """Callback to print analysis results."""
    print(f"\n{'='*60}")
    print(f"📊 ANALYSIS - {mode.upper()} @ {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    print(result)
    print(f"{'='*60}\n")


def if_checkpoint():
    if trigger_checkpoint.is_set():
        trigger_checkpoint.clear()
        return True
    return False


def if_generate():
    if trigger_generate.is_set():
        trigger_generate.clear()
        return True
    return False


def if_evaluate():
    if trigger_evaluate.is_set():
        trigger_evaluate.clear()
        return True
    return False


def terminal_loop():
    global snippet_index
    
    # Override device IDs in the module
    strategies.INTERVIEWER_DEVICE_ID = 2
    strategies.CANDIDATE_DEVICE_ID = 3
    
    print("\n" + "="*60)
    print("🎮 INTERVIEW COPILOT TEST DRIVER")
    print("c=checkpoint, g=generate, e=evaluate, s=show, a=add snippet, q=quit")
    print("="*60 + "\n")
    
    while not stop_program.is_set():
        cmd = input(">>> ").strip().lower()
        
        if cmd == 'c':
            trigger_checkpoint.set()
            print("✅ Checkpoint triggered")
        elif cmd == 'g':
            trigger_generate.set()
            print("✅ Generate triggered")
        elif cmd == 'e':
            trigger_evaluate.set()
            print("✅ Evaluate triggered")
        elif cmd == 's':
            with strategies.log_lock:
                print(f"\n📝 Log:\n{'-'*40}\n{strategies.conversation_log}\n{'-'*40}\n")
        elif cmd == 'a':
            if snippet_index < len(ADDITIONAL_SNIPPETS):
                with strategies.log_lock:
                    strategies.conversation_log += ADDITIONAL_SNIPPETS[snippet_index]
                print(f"✅ Added snippet {snippet_index + 1}/{len(ADDITIONAL_SNIPPETS)}")
                snippet_index += 1
            else:
                print("⚠️ No more snippets")
        elif cmd == 'q':
            print("👋 Shutting down...")
            stop_program.set()
            break


def main():
    print("\n🚀 Starting Test Driver...\n")
    
    # Seed conversation in the module
    with strategies.log_lock:
        strategies.conversation_log = SEED_CONVERSATION
    print("✅ Conversation seeded")
    
    # Start terminal input thread
    input_thread = threading.Thread(target=terminal_loop)
    input_thread.daemon = True
    input_thread.start()
    
    # Launch main threads
    stop_event = strategies.launch_threads(
        if_checkpoint=if_checkpoint,
        if_generate=if_generate,
        if_evaluate=if_evaluate,
        report_analysis=report_analysis
    )
    
    # Wait for quit
    while not stop_program.is_set():
        time.sleep(0.5)
    
    stop_event.set()
    print("\n✅ Done.")


if __name__ == "__main__":
    main()