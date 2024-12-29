from flask import Flask, request, jsonify
import random
import uuid
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import eventlet

app = Flask(__name__)

# Allow multiple origins
allowed_origins = [
    "https://676d80e025a5fb0008309898--courageous-cocada-d21642.netlify.app",
    "https://courageous-cocada-d21642.netlify.app",
    "http://127.0.0.1:5501",
    "http://localhost:5501",
]

# Add a regex pattern to match dynamic subdomains
dynamic_origin_pattern = r"https://[a-z0-9]+--courageous-cocada-d21642\.netlify\.app"

socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')
# Configure CORS with Flask-CORS
CORS(app, resources={
    r"/*": {"origins": allowed_origins + [dynamic_origin_pattern]}  # Combine static URLs and regex
})

# In-memory data storage
sessions = {}

# Helper function to create a new session ID
def generate_session_id():
    return str(uuid.uuid4())[:8]  # Generate a short unique ID

@app.route("/get_leader", methods=["POST"])
def get_leader():
    data = request.json
    session_id = data.get("sessionID")
    session_leader = sessions[session_id]["leader"]
    return {"leader": session_leader}

@app.route("/get_players", methods=["POST"])
def get_players():
    data = request.json
    session_id = data.get("sessionID")
    session_players = sessions[session_id]["players"]
    player_names = list(session_players.keys())
    return {"players": player_names}

@app.route("/check_session", methods=["GET"])
def check_session():
    serializable_sessions = {
        session_id: {
            key: list(value) if isinstance(value, set) else value
            for key, value in session_data.items()
        }
        for session_id, session_data in sessions.items()
    }
    return jsonify(serializable_sessions)

@app.route("/create_session", methods=["POST"])
def create_session():
    data = request.json
    leader = data.get("leader")
    if not leader:
        return jsonify({"error": "Leader name is required"}), 400

    session_id = generate_session_id()
    sessions[session_id] = {
        "session_active": True,
        "round_count": 0,
        "leader": leader,
        "players": {},  # Leader starts with a balance of 0
        "bets": {},
        "bets_submitted": set(),
        "results_submitted":{}
    }
    return jsonify({"message": "Session created", "session_id": session_id})

@socketio.on('join')
def on_join(data):
    session_id = data['session_id']
    print('session id: '+session_id)
    player_name = data['player_name']

    if session_id not in sessions:
        emit('error', {'error': 'Session not found'})
        return

    session = sessions[session_id]
    if player_name in session["players"]:
        emit('error', {'error': 'Player already joined'})
        return

    session["players"][player_name] = 0  # Initialize balance to 0
    join_room(session_id)
    print(f"Client added to room {session_id}")
    emit('player_joined', {'player': player_name}, room=session_id)

@socketio.on('place_bet')
def on_place_bet(data):
    print('it works')
    session_id = data['session_id']
    player_name = data['player_name']
    bet_amount = data['bet_amount']

    if session_id not in sessions:
        emit('error', {'error': 'Session not found'})
        return

    session = sessions[session_id]
    if player_name not in session["players"]:
        emit('error', {'error': 'Player not part of the session'})
        return

    if player_name == session["leader"]:
        emit('error', {'error': 'Leader cannot place bets'})
        return

    session["bets"][player_name] = bet_amount
    session["bets_submitted"].add(player_name)

    emit('bet_placed',{'playerName':player_name, 'currentBalance':session['players'][player_name], 'betAmount':session['bets'][player_name]},room = session_id)

    # Notify the leader when all bets are in
    non_leaders = set(session["players"].keys()) - {session["leader"]}
    if session["bets_submitted"] == non_leaders:
        emit('all_bets_received', {'bets': session["bets"]}, room=session_id)

@app.route('/check_bets/<session_id>', methods=['GET'])
def check_bets(session_id):
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    session = sessions[session_id]
    all_players = set(session["players"].keys()) - {session["leader"]}
    submitted_players = session["bets_submitted"]

    if all_players == submitted_players:
        return jsonify({"all_bets_in": True, "bets": session["bets"]})
    else:
        return jsonify({"all_bets_in": False, "missing_players": list(all_players - submitted_players)})

@socketio.on('start_round')
def on_start_round(data):
    session_id = data['session_id']
    player_name = data['player_name']
    if session_id not in sessions:
        print('sess')
        emit('error', {'error': 'Session not found'})
        return

    session = sessions[session_id]
    leader = session['leader']

    if player_name != leader:
        print('err')
        emit('error', {'error': 'Only the leader can start a round'})
        return

    session["bets"] = {}
    session["bets_submitted"] = set()

    # Notify non-leaders to place their bets
    emit('start_game', {'message': 'Round started! Please place your bets.'}, room=session_id)

@socketio.on('triggerEnterWLandMultiples')
def trigger_enter_WL_and_Multiples(data):
    session_id = data['session_id']
    emit('enterWLandMultiples',{'message':'Input whether you won, draw or loss against the banker and the multiplier'}, room=session_id)

#after a non leader submits the results (win/draw/lose and multiplier), this is to process the individual results and let banker check
@socketio.on('results_sent')
def results_sent(data):
    session_id = data['session_id']
    results = data['results']
    playerName = results['playerName']
    outcome = results['outcome']
    multiplier = float(results['multiplier'])
    session = sessions[session_id]
    results_submitted = session['results_submitted']
    results_submitted[playerName] = {'outcome':outcome, 'multiplier':multiplier}
    print('results sent')
    socketio.emit('update_leaders_UI', {'session_id': session_id}, room=session_id)

@app.route('/check_results_submissions', methods=['POST'])
def check_results_submissions():
    data = request.json
    session_id = data['session_id']
    bets_submitted = sessions[session_id].get("bets_submitted", set())
    results_submitted = sessions[session_id].get("results_submitted", {})

    missing_players = bets_submitted - results_submitted.keys()

    print('missing players')
    print(missing_players)

    if missing_players:
        return {'success':False}
    else:
        return {'success':True}

@socketio.on('process_results')
def process_results(data):
    print(data)
    session_id = data['session_id']
    results = data['results']

    session = sessions.get(session_id)
    if not session:
        print(f"Session {session_id} not found.")
        return

    leader = session['leader']
    balances = session['players']
    bets = session['bets']

    for key, value in results.items():
        player = key
        outcome = value['outcome']
        multiplier = value['multiplier']

        bet_amount = bets.get(player, 0)

        # Calculate the total change (bet_amount * multiplier)
        total_change = int(bet_amount) * int(multiplier)

        if outcome == 'Win':
            # Leader wins: Increase leader's balance and decrease player's balance
            balances[leader] += int(total_change)
            balances[player] -= int(total_change)
        
        elif outcome == 'Lose':
            balances[leader] -= int(total_change)
            balances[player] += int(total_change)

        elif outcome == 'Draw':
            balances[leader] = balances[leader]
            balances[player] = balances[player]

    session['round_count']+=1
    # session["bets"] = {}
    # Emit the updated balances to all players
    print(f"Updated balances for session {session_id}: {balances}")

    session["results_submitted"] = {}
    socketio.emit('next_round', {'session_id': session_id}, room=session_id)

# @app.route("/start_round/<session_id>", methods=["POST"])
# def start_round(session_id):
#     if session_id not in sessions:
#         return jsonify({"error": "Session not found"}), 404

#     session = sessions[session_id]
#     if not session["bets"]:
#         return jsonify({"error": "No bets placed"}), 400

#     session["round_count"] += 1
#     leader = session["leader"]
#     leader_number = random.randint(1, 100)

#     results = {"leader_number": leader_number, "results": []}
#     for player, bet in session["bets"].items():
#         player_number = random.randint(1, 100)
#         if leader_number > player_number:
#             session["players"][leader] += bet
#             session["players"][player] -= bet
#             result = f"{leader} wins against {player}. {leader} gains {bet}, {player} loses {bet}."
#         elif leader_number < player_number:
#             session["players"][leader] -= bet
#             session["players"][player] += bet
#             result = f"{player} wins against {leader}. {player} gains {bet}, {leader} loses {bet}."
#         else:
#             result = f"{leader} and {player} tie. No balance changes."

#         results["results"].append(
#             {"player": player, "player_number": player_number, "result": result}
#         )

#     session["bets"] = {}  # Clear bets after the round
#     return jsonify(results)


@app.route("/end_session/<session_id>", methods=["POST"])
def end_session(session_id):
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    session = sessions.pop(session_id)
    return jsonify({"message": "Session ended", "final_balances": session["players"]})

@app.route('/room_clients/<session_id>', methods=['GET'])
def room_clients(session_id):
    room = socketio.server.manager.rooms.get('/', {}).get(session_id, {})
    num_clients = len(room) if room else 0
    return jsonify({"session_id": session_id, "clients": num_clients})

# @app.route('/get_non_leaders', methods = ['POST'])
# def get_non_leaders():
#     data = request.json
#     session_id = data.get("sessionID")
#     print(session_id)
#     session_players = sessions[session_id]["players"]
#     session_leader = sessions[session_id]['leader']
#     player_names = list(session_players.keys())
#     player_names = player_names.remove(session_leader)
#     return {"players": player_names}

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000)
