from backend.src.common.grok import call_grok

if __name__ == "__main__":
    print(call_grok("Hello, Grok!", "You are a helpful assistant.", model="grok-4-1-fast-reasoning"))