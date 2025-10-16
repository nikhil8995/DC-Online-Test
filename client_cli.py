import requests
import sys

# The single entry point for the client is the load balancer
LOAD_BALANCER_URL = "http://localhost:5555"


def main():
    """Main function to run the CLI exam client."""
    print("--- Welcome to the Online Exam ---")

    try:
        username = input("Please enter your username to begin: ").strip()
        if not username:
            print("Username cannot be empty. Exiting.")
            return

        # --- 1. Start the Exam ---
        print("\nConnecting to the server to start your exam...")
        start_response = requests.post(
            f"{LOAD_BALANCER_URL}/start_exam", json={"username": username})

        if start_response.status_code != 200:
            print(
                f"Error: Could not start exam. Server says: {start_response.json().get('error', 'Unknown error')}")
            return

        exam_data = start_response.json()
        session_id = exam_data.get('session_id')
        current_question = exam_data.get('question')

        print(f"\n{exam_data.get('message')}")

        # --- 2. Exam Loop ---
        while current_question:
            print("\n----------------------------------")
            print(f"Question: {current_question['question']}")
            for opt in current_question['options']:
                print(f"  {opt}")

            answer = input("Your answer (e.g., A, B, C, D): ").strip()

            # Submit answer
            submit_payload = {
                "session_id": session_id,
                "question_id": current_question['id'],
                "answer": answer
            }
            submit_response = requests.post(
                f"{LOAD_BALANCER_URL}/submit_answer", json=submit_payload)

            if submit_response.status_code != 200:
                print(
                    f"Error submitting answer: {submit_response.json().get('error', 'Unknown error')}")
                break

            result = submit_response.json()

            # Print feedback
            if 'feedback' in result:
                print(f"\n>>> Feedback: {result['feedback']}")

            # Check if exam is finished
            if 'final_score' in result:
                print("\n==================================")
                print(result.get('message', "Exam Over!"))
                print(f"Your Final Score: {result['final_score']}")
                print("==================================")
                current_question = None  # End the loop
            elif 'next_question' in result:
                current_question = result['next_question']
            else:
                # Handle time up case
                print(f"\n{result.get('message', 'An event occurred.')}")
                if 'final_score' in result:
                    print(f"Final Score: {result['final_score']}")
                current_question = None

    except requests.ConnectionError:
        print("\n[CLIENT] Error: Could not connect to the load balancer.")
        print("Please ensure the load_balancer.py script is running.")
    except Exception as e:
        print(f"\n[CLIENT] An unexpected error occurred: {e}")
    finally:
        print("\nThank you for taking the exam!")


if __name__ == "__main__":
    main()
