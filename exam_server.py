import threading
import time
import sys
import threading
import time
import sys
from flask import Flask, request, jsonify
from clock_sync import BerkeleyClock


class ExamServerInstance:
    def __init__(self, port: int, server_id: str):
        self.app = Flask(__name__)
        self.port = port
        self.server_id = server_id
        self.clock_sync = None

        # Instance-specific state
        self.student_sessions = {}
        self.sessions_lock = threading.Lock()
        self.max_concurrent_sessions = 2
        self.exam_title = "Java Basics Exam"
        self.student_results = []

        # Default exam content
        self.questions = [
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
        self.exam_duration = 60  # seconds

        # Set up routes
        self.setup_routes()

    def setup_routes(self):
        """Configure all route handlers"""
        self.app.route('/start_exam', methods=['POST'])(self.handle_start_exam)
        self.app.route('/submit_answer',
                       methods=['POST'])(self.handle_submit_answer)
        self.app.route('/health', methods=['GET'])(self.health_check)
        self.app.route('/metrics', methods=['GET'])(self.metrics)
        self.app.route('/configure_exam',
                       methods=['POST'])(self.configure_exam)
        self.app.route('/exam_info', methods=['GET'])(self.exam_info)
        self.app.route('/results', methods=['GET'])(self.results)

    def get_question_by_index(self, index):
        """Safely gets a question by its index."""
        if 0 <= index < len(self.questions):
            return self.questions[index]
        return None

    def create_session(self, username):
        """Creates a new exam session for a user."""
        with self.sessions_lock:
            if len(self.student_sessions) >= self.max_concurrent_sessions:
                return None  # Server is at capacity

            current_time = self.clock_sync.get_current_time()
            session_id = f"session_{int(current_time)}_{username}"
            self.student_sessions[session_id] = {
                "username": username,
                "score": 0,
                "question_index": 0,
                "deadline": current_time + self.exam_duration
            }
            return session_id

    def handle_start_exam(self):
        """Starts a new exam session for a user."""
        data = request.get_json(silent=True) or {}
        username = data.get('username')
        if not username:
            return jsonify({"error": "Username is required."}), 400

        session_id = self.create_session(username)
        if not session_id:
            return jsonify({"error": "Server is at maximum capacity."}), 503

        first_question = self.get_question_by_index(0)
        with self.sessions_lock:
            deadline = self.student_sessions[session_id]['deadline']
        remaining = max(0, int(deadline - self.clock_sync.get_current_time()))

        return jsonify({
            "message": f"Welcome, {username}! You have {self.exam_duration} seconds.",
            "session_id": session_id,
            "question": first_question,
            "deadline": deadline,
            "time_remaining": remaining
        })

    def handle_submit_answer(self):
        """Submits an answer for the current question in a session."""
        data = request.get_json(silent=True) or {}
        session_id = data.get('session_id')
        user_answer = data.get('answer')

        with self.sessions_lock:
            session = self.student_sessions.get(session_id)
            if not session:
                return jsonify({"error": "Invalid session ID."}), 404

            # Check if the time is up using synchronized clock
            current_time = self.clock_sync.get_current_time()
            if current_time > session['deadline']:
                return self._end_session(session_id, "timeout")

            # Process the answer
            current_question_index = session['question_index']
            correct_answer = self.questions[current_question_index]['answer']
            feedback = "Incorrect!"
            if user_answer and user_answer.upper() == correct_answer:
                session['score'] += 1
                feedback = "Correct!"

            # Move to the next question
            session['question_index'] += 1
            next_question_index = session['question_index']

            # Recompute remaining time
            remaining = max(
                0, int(session['deadline'] - self.clock_sync.get_current_time()))

            # Check if the exam is finished
            if next_question_index >= len(self.questions):
                return self._end_session(session_id, "completed", feedback)
            else:
                next_question = self.get_question_by_index(next_question_index)
                return jsonify({
                    "feedback": feedback,
                    "next_question": next_question,
                    "time_remaining": remaining
                })

    def _end_session(self, session_id: str, reason: str, feedback: str = None):
        """End an exam session and record results."""
        session = self.student_sessions.get(session_id)
        if not session:
            return jsonify({"error": "Invalid session ID."}), 404

        final_score = session['score']
        username = session['username']

        # Record result
        self.student_results.append({
            "username": username,
            "score": final_score,
            "total": len(self.questions),
            "session_id": session_id,
            "ended_reason": reason,
            "ended_at": self.clock_sync.get_current_time()
        })

        # Clean up session
        del self.student_sessions[session_id]

        response = {
            "message": "Time's up!" if reason == "timeout" else "Exam finished!",
            "final_score": f"{final_score}/{len(self.questions)}"
        }
        if feedback:
            response["feedback"] = feedback

        return jsonify(response)

    def health_check(self):
        """Health check endpoint."""
        return "OK", 200

    def metrics(self):
        """Server metrics endpoint."""
        with self.sessions_lock:
            active_count = len(self.student_sessions)
        return jsonify({
            "active_sessions": active_count,
            "capacity": self.max_concurrent_sessions
        })

    def configure_exam(self):
        """Configure exam settings."""
        data = request.get_json(silent=True) or {}

        # Basic validation
        if not isinstance(data.get('title'), str) or not data['title'].strip():
            return jsonify({"error": "title (string) is required"}), 400
        if not isinstance(data.get('questions'), list) or len(data['questions']) == 0:
            return jsonify({"error": "questions (non-empty list) is required"}), 400
        if not isinstance(data.get('duration'), int) or data['duration'] <= 0:
            return jsonify({"error": "duration (positive integer seconds) is required"}), 400
        if not isinstance(data.get('capacity'), int) or data['capacity'] <= 0:
            return jsonify({"error": "capacity (positive integer) is required"}), 400

        # Validate questions minimally
        for q in data['questions']:
            if not isinstance(q, dict):
                return jsonify({"error": "each question must be an object"}), 400
            if not all(k in q for k in ['id', 'question', 'options', 'answer']):
                return jsonify({"error": "each question needs id, question, options, answer"}), 400
            if not isinstance(q['options'], list) or len(q['options']) < 2:
                return jsonify({"error": "each question must have at least 2 options"}), 400

        with self.sessions_lock:
            self.exam_title = data['title'].strip()
            self.questions = data['questions']
            self.exam_duration = data['duration']
            self.max_concurrent_sessions = data['capacity']
            # Reset any existing sessions on config change
            self.student_sessions.clear()
            self.student_results.clear()

        return jsonify({
            "message": "Exam configuration applied",
            "server_id": self.server_id,
            "questions": len(self.questions),
            "duration": self.exam_duration,
            "capacity": self.max_concurrent_sessions
        })

    def exam_info(self):
        """Get exam metadata."""
        with self.sessions_lock:
            return jsonify({
                "server_id": self.server_id,
                "title": self.exam_title,
                "num_questions": len(self.questions),
                "duration": self.exam_duration,
                "capacity": self.max_concurrent_sessions,
                "active_sessions": len(self.student_sessions)
            })

    def results(self):
        """Get exam results."""
        with self.sessions_lock:
            return jsonify({"results": list(self.student_results)})


# For running as standalone server
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python exam_server.py <port> <server_id>")
        sys.exit(1)

    port = int(sys.argv[1])
    server_id = sys.argv[2]

    # Create and start server
    server = ExamServerInstance(port, server_id)

    # Initialize clock sync (coordinator if port is 6001)
    is_coordinator = (port == 6001)
    server.clock_sync = BerkeleyClock(server_id, is_coordinator)
    server.clock_sync.start()

    # Run the server
    print(f"[{server_id}] Starting exam server on port {port}")
    server.app.run(host='0.0.0.0', port=port, debug=False)
