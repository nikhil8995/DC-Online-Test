import threading
import time
import requests
from flask import Flask, request, jsonify, redirect, render_template, url_for
import json

# --- App Configuration ---
app = Flask(__name__, template_folder='templates', static_folder='static')
PORT = 5555

# --- Load Balancer State ---
# List of backend exam servers
# Format: [{"url": "http://localhost:6001", "id": "S1", "healthy": True, "active_sessions": 0}]
SERVERS = [
    {"url": "http://localhost:6001", "id": "S1",
        "healthy": True, "active_sessions": 0},
    {"url": "http://localhost:6002", "id": "S2",
        "healthy": True, "active_sessions": 0},
    {"url": "http://localhost:6003", "id": "S3",
        "healthy": True, "active_sessions": 0},
]
server_lock = threading.Lock()
HEALTH_CHECK_INTERVAL = 10  # seconds
EXAM_CACHE = {
    "title": None,
    "num_questions": 0,
    "duration": 0,
    "capacity": 0,
}
SESSION_MAP = {}
session_lock = threading.Lock()

# --- Load Balancing Logic ---


def get_least_busy_server():
    """
    Finds the healthy server with the fewest active sessions.
    This is the 'Least Connections' strategy.
    """
    best_server = None
    min_sessions = float('inf')

    with server_lock:
        healthy_servers = [s for s in SERVERS if s["healthy"]]
        if not healthy_servers:
            return None

        # Find the server with the minimum number of active sessions
        for server in healthy_servers:
            if server["active_sessions"] < min_sessions:
                min_sessions = server["active_sessions"]
                best_server = server

    return best_server

# --- Health Checking ---


def health_check_servers():
    """Periodically checks the health of all backend servers."""
    while True:
        with server_lock:
            for server in SERVERS:
                try:
                    # Check the health endpoint
                    health_response = requests.get(
                        f"{server['url']}/health", timeout=2)
                    # Get the current load from the metrics endpoint
                    metrics_response = requests.get(
                        f"{server['url']}/metrics", timeout=2)

                    if health_response.status_code == 200 and metrics_response.status_code == 200:
                        server["healthy"] = True
                        server["active_sessions"] = metrics_response.json().get(
                            "active_sessions", 0)
                    else:
                        server["healthy"] = False
                        print(
                            f"[LB] Server {server['id']} ({server['url']}) is UNHEALTHY.")

                except requests.RequestException:
                    if server["healthy"]:
                        server["healthy"] = False
                        print(
                            f"[LB] Server {server['id']} ({server['url']}) is now UNHEALTHY (connection failed).")

        print_server_status()
        time.sleep(HEALTH_CHECK_INTERVAL)


def print_server_status():
    """Prints a neat status table of the servers."""
    with server_lock:
        print("\n--- Load Balancer Status ---")
        for server in SERVERS:
            status = "HEALTHY" if server['healthy'] else "UNHEALTHY"
            print(
                f"  - {server['id']} ({server['url']}): {status}, Active Sessions: {server['active_sessions']}")
        print("----------------------------")

# --- API Endpoints that forward requests ---


@app.route('/start_exam', methods=['POST'])
def handle_start_exam():
    """
    Finds the best server and forwards the /start_exam request.
    """
    # Accept JSON or form from web UI
    username = None
    if request.is_json:
        username = (request.get_json(silent=True) or {}).get('username')
    else:
        username = request.form.get('username')

    if not username:
        return jsonify({"error": "Username is required."}), 400

    target_server = get_least_busy_server()
    if not target_server:
        return jsonify({"error": "No healthy backend servers available."}), 503

    print(
        f"[LB] Forwarding new exam request to {target_server['id']} ({target_server['url']})")
    try:
        # Forward the request to the chosen server
        response = requests.post(
            f"{target_server['url']}/start_exam", json={"username": username}, timeout=5)
        # If success, store sticky mapping
        if response.status_code == 200:
            body = response.json()
            session_id = body.get('session_id')
            if session_id:
                with session_lock:
                    SESSION_MAP[session_id] = target_server['url']
        if request.form.get('from_ui'):
            # Render web flow
            if response.status_code != 200:
                return render_template('student.html', exams=fetch_exam_infos(), error=response.json().get('error', 'Failed to start exam')), response.status_code
            data = response.json()
            # Pass deadline/time_remaining to the template so client can show an accurate countdown
            return render_template('student_exam.html', session_id=data.get('session_id'), question=data.get('question'), message=data.get('message'), deadline=data.get('deadline'), time_remaining=data.get('time_remaining'))
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        print(f"[LB] Error forwarding request to {target_server['id']}: {e}")
        return jsonify({"error": "Failed to connect to backend server."}), 504


@app.route('/submit_answer', methods=['POST'])
def handle_submit_answer():
    """
    Forwards the /submit_answer request. In a real-world scenario, you would
    need to track which server a session belongs to. For this simple case,
    we'll just forward to any available server, assuming the session exists.
    A more robust solution would use a session store (like Redis) or sticky sessions.
    """
    # Use sticky session mapping if provided
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    target_server = None
    if session_id:
        with session_lock:
            target_url = SESSION_MAP.get(session_id)
        if target_url:
            with server_lock:
                for s in SERVERS:
                    if s["url"] == target_url and s["healthy"]:
                        target_server = s
                        break
    if not target_server:
        target_server = next((s for s in SERVERS if s["healthy"]), None)

    if not target_server:
        return jsonify({"error": "No healthy backend servers available."}), 503

    print(f"[LB] Forwarding answer to a healthy server...")
    try:
        response = requests.post(
            f"{target_server['url']}/submit_answer", json=data, timeout=5)
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        print(f"[LB] Error forwarding answer: {e}")
        return jsonify({"error": "Failed to connect to backend server."}), 504

# --- Aggregation and management endpoints ---


def fetch_exam_infos():
    infos = []
    with server_lock:
        targets = list(SERVERS)
    for server in targets:
        try:
            resp = requests.get(f"{server['url']}/exam_info", timeout=2)
            if resp.status_code == 200:
                info = resp.json()
                info["server_id"] = server["id"]
                info["url"] = server["url"]
                infos.append(info)
        except requests.RequestException:
            continue
    return infos


def fetch_results():
    aggregated = []
    with server_lock:
        targets = list(SERVERS)
    for server in targets:
        try:
            resp = requests.get(f"{server['url']}/results", timeout=3)
            if resp.status_code == 200:
                body = resp.json()
                for r in body.get('results', []):
                    r['server_id'] = server['id']
                    aggregated.append(r)
        except requests.RequestException:
            continue
    # newest first
    aggregated.sort(key=lambda r: r.get('ended_at', 0), reverse=True)
    return aggregated


@app.route('/exams', methods=['GET'])
def list_exams():
    infos = fetch_exam_infos()
    # Cache the first exam for quick card render
    if infos:
        first = infos[0]
        EXAM_CACHE.update({
            "title": first.get("title"),
            "num_questions": first.get("num_questions", 0),
            "duration": first.get("duration", 0),
            "capacity": first.get("capacity", 0),
        })
    return jsonify({"exams": infos})


@app.route('/configure_exam_all', methods=['POST'])
def configure_exam_all():
    """Propagates a new exam configuration to all healthy servers."""
    payload = request.get_json(silent=True) or {}
    results = []
    with server_lock:
        targets = [s for s in SERVERS if s["healthy"]]
    for server in targets:
        try:
            resp = requests.post(
                f"{server['url']}/configure_exam", json=payload, timeout=4)
            results.append({"server_id": server["id"], "status": resp.status_code, "body": resp.json(
            ) if resp.content else {}})
        except requests.RequestException as e:
            results.append({"server_id": server["id"], "error": str(e)})

    return jsonify({"results": results})

# --- Web UI ---


@app.route('/')
def home_page():
    # Simple landing with links
    return render_template('home.html')


@app.route('/teacher', methods=['GET'])
def teacher_page():
    results = fetch_results()
    return render_template('teacher.html', results=results)


@app.route('/teacher/configure', methods=['POST'])
def teacher_configure():
    # Accept form submission for exam config
    title = request.form.get('title', '').strip()
    duration = int(request.form.get('duration', '60') or 60)
    capacity = int(request.form.get('capacity', '2') or 2)
    questions_raw = request.form.get('questions_json', '[]')
    try:
        questions = json.loads(questions_raw)
    except Exception:
        return render_template('teacher.html', error='Invalid questions JSON'), 400

    payload = {
        "title": title,
        "questions": questions,
        "duration": duration,
        "capacity": capacity,
    }
    resp = configure_exam_all_impl(payload)
    if resp.get('error'):
        return render_template('teacher.html', error=resp['error']), 500
    return render_template('teacher.html', success='Exam configuration pushed to servers.')


def configure_exam_all_impl(payload):
    try:
        with app.test_request_context():
            # Reuse the same propagation logic
            with server_lock:
                targets = [s for s in SERVERS if s["healthy"]]
            results = []
            for server in targets:
                try:
                    resp = requests.post(
                        f"{server['url']}/configure_exam", json=payload, timeout=4)
                    results.append(
                        {"server_id": server["id"], "status": resp.status_code})
                except requests.RequestException as e:
                    results.append(
                        {"server_id": server["id"], "error": str(e)})
            return {"results": results}
    except Exception as e:
        return {"error": str(e)}


@app.route('/student', methods=['GET'])
def student_page():
    infos = fetch_exam_infos()
    return render_template('student.html', exams=infos)


@app.route('/student/start', methods=['POST'])
def student_start():
    # Call the same handler but render templates
    return handle_start_exam()


@app.route('/student/answer', methods=['POST'])
def student_answer():
    session_id = request.form.get('session_id')
    answer = request.form.get('answer')
    question_id = request.form.get('question_id')
    payload = {"session_id": session_id, "answer": answer,
               "question_id": int(question_id) if question_id else None}
    try:
        # Reuse API
        resp = handle_submit_answer.__wrapped__() if hasattr(
            handle_submit_answer, '__wrapped__') else None
    except TypeError:
        resp = None
    if resp is None:
        try:
            # Fall back to posting to self
            r = requests.post(
                f"http://localhost:{PORT}/submit_answer", json=payload, timeout=5)
            result = r.json()
            status = r.status_code
        except Exception as e:
            return render_template('student_exam.html', session_id=session_id, error=str(e)), 500
    else:
        # When calling the function directly, resp is a tuple (json, status)
        result, status = resp

    if status != 200:
        return render_template('student_exam.html', session_id=session_id, error=result.get('error', 'Submission failed')), status

    # Render next step
    if result.get('final_score'):
        return render_template('student_exam.html', session_id=session_id, final_score=result['final_score'], message=result.get('message', 'Exam finished!'), feedback=result.get('feedback'))
    else:
        next_q = result.get('next_question')
        return render_template('student_exam.html', session_id=session_id, question=next_q, feedback=result.get('feedback'), time_remaining=result.get('time_remaining'))


if __name__ == '__main__':
    # Start the health checker in a background thread
    health_thread = threading.Thread(target=health_check_servers, daemon=True)
    health_thread.start()

    print(f"[LB] Load Balancer running on http://localhost:{PORT}")
    app.run(port=PORT, debug=False)
