import threading
import time
import sys
from flask import Flask, request, jsonify
from werkzeug.serving import make_server

# --- App Configuration ---
app = Flask(__name__)
PORT = 0  # Will be set from command line
SERVER_ID = "default"  # Will be set from command line

# --- In-Memory State ---
# This dictionary will store session data for each student
# Format: {session_id: {'username': str, 'score': int, 'question_index': int, 'deadline': float}}
student_sessions = {}
sessions_lock = threading.Lock()
MAX_CONCURRENT_SESSIONS = 2
EXAM_TITLE = "Java Basics Exam"
# list of {username, score, total, session_id, ended_reason, ended_at}
student_results = []

# --- Exam Content ---
QUESTIONS = [
    {
        "id": 1,
        "question": "Which keyword is used to inherit a class in Java?",
        "options": ["A) this", "B) super", "C) extends", "D) implements"],
        "answer": "C"
    },
    {
        "id": 2,
        "question": "Which of these is not a Java primitive type?",
        "options": ["A) int", "B) float", "C) boolean", "D) string"],
        "answer": "D"
    },
    {
        "id": 3,
        "question": "Which package contains the Scanner class?",
        "options": ["A) java.util", "B) java.io", "C) java.lang", "D) java.text"],
        "answer": "A"
    },
]
EXAM_DURATION = 60  # 60 seconds

# --- Helper Functions ---


def get_question_by_index(index):
    """Safely gets a question by its index."""
    if 0 <= index < len(QUESTIONS):
        return QUESTIONS[index]
    return None


def create_session(username):
    """Creates a new exam session for a user."""
    with sessions_lock:
        if len(student_sessions) >= MAX_CONCURRENT_SESSIONS:
            return None  # Server is at capacity

        session_id = f"session_{int(time.time())}_{username}"
        student_sessions[session_id] = {
            "username": username,
            "score": 0,
            "question_index": 0,
            "deadline": time.time() + EXAM_DURATION
        }
        return session_id

# --- API Endpoints ---


@app.route('/start_exam', methods=['POST'])
def start_exam():
    """Starts a new exam session for a user."""
    username = request.json.get('username')
    if not username:
        return jsonify({"error": "Username is required."}), 400

    print(f"[{SERVER_ID}] Received request to start exam for {username}")
    session_id = create_session(username)

    if not session_id:
        print(f"[{SERVER_ID}] CRASH! Overload detected. Refusing connection.")
        # In a real-world scenario, you wouldn't crash, just refuse.
        # This simulates the original project's behavior.
        return jsonify({"error": "Server is at maximum capacity."}), 503

    first_question = get_question_by_index(0)
    print(f"[{SERVER_ID}] Session {session_id} created for {username}. Current load: {len(student_sessions)}/{MAX_CONCURRENT_SESSIONS}")
    return jsonify({
        "message": f"Welcome, {username}! You have {EXAM_DURATION} seconds.",
        "session_id": session_id,
        "question": first_question
    })


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """Submits an answer for the current question in a session."""
    data = request.get_json()
    session_id = data.get('session_id')
    user_answer = data.get('answer')

    with sessions_lock:
        session = student_sessions.get(session_id)
        if not session:
            return jsonify({"error": "Invalid session ID."}), 404

        # Check if the time is up
        if time.time() > session['deadline']:
            # Clean up the session
            final_score = session['score']
            username = session['username']
            del student_sessions[session_id]
            # record result
            student_results.append({
                "username": username,
                "score": final_score,
                "total": len(QUESTIONS),
                "session_id": session_id,
                "ended_reason": "timeout",
                "ended_at": time.time()
            })
            print(
                f"[{SERVER_ID}] Session {session_id} for {username} ended due to time limit.")
            return jsonify({
                "message": "Time is up! Your exam has ended.",
                "final_score": f"{final_score}/{len(QUESTIONS)}"
            })

        # Process the answer
        current_question_index = session['question_index']
        correct_answer = QUESTIONS[current_question_index]['answer']
        feedback = "Incorrect!"
        if user_answer and user_answer.upper() == correct_answer:
            session['score'] += 1
            feedback = "Correct!"

        # Move to the next question
        session['question_index'] += 1
        next_question_index = session['question_index']

        # Check if the exam is finished
        if next_question_index >= len(QUESTIONS):
            final_score = session['score']
            username = session['username']
            del student_sessions[session_id]  # End of exam, clean up
            # record result
            student_results.append({
                "username": username,
                "score": final_score,
                "total": len(QUESTIONS),
                "session_id": session_id,
                "ended_reason": "completed",
                "ended_at": time.time()
            })
            print(
                f"[{SERVER_ID}] Session {session_id} for {username} finished.")
            return jsonify({
                "message": "Exam finished!",
                "feedback": feedback,
                "final_score": f"{final_score}/{len(QUESTIONS)}"
            })
        else:
            # Send the next question
            next_question = get_question_by_index(next_question_index)
            return jsonify({
                "feedback": feedback,
                "next_question": next_question
            })


@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint for the load balancer."""
    return "OK", 200


@app.route('/metrics', methods=['GET'])
def metrics():
    """Provides metrics about the server's current load."""
    with sessions_lock:
        active_count = len(student_sessions)
    return jsonify({"active_sessions": active_count, "capacity": MAX_CONCURRENT_SESSIONS})


@app.route('/configure_exam', methods=['POST'])
def configure_exam():
    """Configures the current exam: title, questions, duration, capacity.
    Resets any existing sessions to ensure consistency with the new config.
    """
    data = request.get_json(silent=True) or {}

    title = data.get('title')
    questions = data.get('questions')
    duration = data.get('duration')
    capacity = data.get('capacity')

    # Basic validation
    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title (string) is required"}), 400
    if not isinstance(questions, list) or len(questions) == 0:
        return jsonify({"error": "questions (non-empty list) is required"}), 400
    if not isinstance(duration, int) or duration <= 0:
        return jsonify({"error": "duration (positive integer seconds) is required"}), 400
    if not isinstance(capacity, int) or capacity <= 0:
        return jsonify({"error": "capacity (positive integer) is required"}), 400

    # Validate questions minimally
    for q in questions:
        if not isinstance(q, dict):
            return jsonify({"error": "each question must be an object"}), 400
        if not all(k in q for k in ['id', 'question', 'options', 'answer']):
            return jsonify({"error": "each question needs id, question, options, answer"}), 400
        if not isinstance(q['options'], list) or len(q['options']) < 2:
            return jsonify({"error": "each question must have at least 2 options"}), 400

    global EXAM_TITLE, QUESTIONS, EXAM_DURATION, MAX_CONCURRENT_SESSIONS
    with sessions_lock:
        EXAM_TITLE = title.strip()
        QUESTIONS = questions
        EXAM_DURATION = duration
        MAX_CONCURRENT_SESSIONS = capacity
        # Reset any existing sessions on config change
        student_sessions.clear()
        student_results.clear()

    print(f"[{SERVER_ID}] Exam configured: '{EXAM_TITLE}', questions={len(QUESTIONS)}, duration={EXAM_DURATION}s, capacity={MAX_CONCURRENT_SESSIONS}")
    return jsonify({
        "message": "Exam configuration applied",
        "server_id": SERVER_ID,
        "questions": len(QUESTIONS),
        "duration": EXAM_DURATION,
        "capacity": MAX_CONCURRENT_SESSIONS
    })


@app.route('/exam_info', methods=['GET'])
def exam_info():
    """Returns current exam metadata for discovery/listing purposes."""
    with sessions_lock:
        active_count = len(student_sessions)
        num_questions = len(QUESTIONS)
        title = EXAM_TITLE
        duration = EXAM_DURATION
        capacity = MAX_CONCURRENT_SESSIONS

    return jsonify({
        "server_id": SERVER_ID,
        "title": title,
        "num_questions": num_questions,
        "duration": duration,
        "capacity": capacity,
        "active_sessions": active_count
    })


@app.route('/results', methods=['GET'])
def results():
    """Returns completed results for this server."""
    with sessions_lock:
        results_copy = list(student_results)
    return jsonify({"results": results_copy})

# --- Server Class to run Flask in a thread ---


class ServerThread(threading.Thread):
    def __init__(self, flask_app, port):
        super().__init__()
        self.server = make_server('0.0.0.0', port, flask_app)
        self.ctx = flask_app.app_context()
        self.ctx.push()

    def run(self):
        print(f"[{SERVER_ID}] Exam server running on port {self.server.port}")
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python exam_server.py <port> <server_id>")
        sys.exit(1)

    PORT = int(sys.argv[1])
    SERVER_ID = sys.argv[2]

    server_thread = ServerThread(app, PORT)
    server_thread.start()
