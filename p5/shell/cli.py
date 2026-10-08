import requests


API_URL = "http://127.0.0.1:8000/api/task"


def send_task(prompt):
    payload = {
        "prompt": prompt,
        "agent_type": "general",
        "priority": 5,
        "estimated_tokens": 256,
        "complexity": 1,
        "risk_level": 1,
        "deadline_s": 10,
        "required_capabilities": []
    }

    try:
        response = requests.post(API_URL, json=payload)

        if response.ok:
            data = response.json()

            task = data.get("task", {})

            print("\n" + "-" * 50)
            print("                 AgentOS Response")
            print("-" * 50)

            print("\n" + data.get("response", "No response received."))

            print("\n" + "-" * 50)
            print("Task Information")
            print("-" * 50)

            print(f"Task ID      : {task.get('id', 'N/A')}")
            print(f"Status       : {task.get('status', 'N/A')}")
            print(f"Agent        : {data.get('agent', 'N/A')}")
            print(f"Model        : {data.get('model', 'N/A')}")
            print(f"Latency      : {data.get('latency_seconds', 0):.2f} seconds")
            print(f"Tokens Used  : {data.get('tokens_used', 'N/A')}")
            print(f"LLM Backend  : {data.get('llm_backend', 'N/A')}")

            print("-" * 50)

        else:
            print("\nAPI Error")
            print(f"Status Code: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("\n" + "-" * 50)
        print("ERROR: Could not connect to AgentOS backend.")
        print("Make sure the FastAPI server is running.")
        print("-" * 50)

    except requests.exceptions.Timeout:
        print("\n" + "-" * 50)
        print("ERROR: Request timed out.")
        print("The AgentOS backend took too long to respond.")
        print("-" * 50)

    except requests.exceptions.RequestException as e:
        print("\n" + "-" * 50)
        print("ERROR: Request failed.")
        print(e)
        print("-" * 50)

    except ValueError:
        print("\n" + "-" * 50)
        print("ERROR: Backend returned an invalid JSON response.")
        print("-" * 50)


def main():
    print("=" * 50)
    print("              AgentOS P5 Shell")
    print("=" * 50)
    print("Type a task to send it to AgentOS.")
    print("Type 'exit' or 'quit' to close the shell.")
    print("=" * 50)

    while True:
        try:
            prompt = input("\nAgentOS> ")

            if prompt.lower().strip() in ["exit", "quit"]:
                print("\nGoodbye!")
                break

            if not prompt.strip():
                print("Please enter a task.")
                continue

            print("\nSending task to AgentOS...")

            send_task(prompt)

        except KeyboardInterrupt:
            print("\n\nExiting AgentOS Shell...")
            break


if __name__ == "__main__":
    main()