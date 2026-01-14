"""
Leaderboard Server for Blackjack.
A central HTTP API that stores and serves leaderboard data.
Uses SQLite for persistence.
"""

import json
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from typing import Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

LEADERBOARD_PORT = 8888
DB_FILE = "leaderboard.db"

# =============================================================================
# DATABASE
# =============================================================================

class LeaderboardDB:
    """SQLite-backed leaderboard database."""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self.lock = threading.Lock()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    ties INTEGER DEFAULT 0,
                    games_played INTEGER DEFAULT 0,
                    points INTEGER DEFAULT 0,
                    last_played TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_points ON players(points DESC)
            """)
            # Migration: add points column if it doesn't exist
            try:
                conn.execute("ALTER TABLE players ADD COLUMN points INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Column already exists
            conn.commit()
    
    def submit_result(self, player_name: str, wins: int, losses: int, ties: int, points: int = 0) -> dict:
        """
        Submit game results for a player.
        Updates existing player or creates new one.
        
        Args:
            player_name: Player's name
            wins: Number of wins in this session
            losses: Number of losses in this session
            ties: Number of ties in this session
            points: Points earned in this session
            
        Returns:
            dict: Updated player stats
        """
        with self.lock:
            with self._get_connection() as conn:
                # Check if player exists
                cursor = conn.execute(
                    "SELECT * FROM players WHERE name = ?", 
                    (player_name,)
                )
                existing = cursor.fetchone()
                
                games = wins + losses + ties
                now = datetime.now().isoformat()
                
                if existing:
                    # Update existing player
                    conn.execute("""
                        UPDATE players 
                        SET wins = wins + ?,
                            losses = losses + ?,
                            ties = ties + ?,
                            games_played = games_played + ?,
                            points = points + ?,
                            last_played = ?
                        WHERE name = ?
                    """, (wins, losses, ties, games, points, now, player_name))
                else:
                    # Create new player
                    conn.execute("""
                        INSERT INTO players (name, wins, losses, ties, games_played, points, last_played)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (player_name, wins, losses, ties, games, points, now))
                
                conn.commit()
                
                # Fetch updated stats
                cursor = conn.execute(
                    "SELECT * FROM players WHERE name = ?", 
                    (player_name,)
                )
                player = cursor.fetchone()
                
                return {
                    "name": player["name"],
                    "wins": player["wins"],
                    "losses": player["losses"],
                    "ties": player["ties"],
                    "games_played": player["games_played"],
                    "points": player["points"],
                    "win_rate": round(player["wins"] / player["games_played"] * 100, 1) if player["games_played"] > 0 else 0
                }
    
    def get_leaderboard(self, limit: int = 10) -> list:
        """
        Get the top players leaderboard (sorted by points).
        
        Args:
            limit: Maximum number of players to return
            
        Returns:
            list: Top players sorted by points
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT name, wins, losses, ties, games_played, points, last_played
                FROM players
                ORDER BY points DESC, wins DESC, games_played ASC
                LIMIT ?
            """, (limit,))
            
            players = []
            for rank, row in enumerate(cursor.fetchall(), 1):
                games = row["games_played"]
                players.append({
                    "rank": rank,
                    "name": row["name"],
                    "wins": row["wins"],
                    "losses": row["losses"],
                    "ties": row["ties"],
                    "games_played": games,
                    "points": row["points"] or 0,
                    "win_rate": round(row["wins"] / games * 100, 1) if games > 0 else 0,
                    "last_played": row["last_played"]
                })
            
            return players
    
    def get_player(self, player_name: str) -> Optional[dict]:
        """Get stats for a specific player."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM players WHERE name = ?", 
                (player_name,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            games = row["games_played"]
            return {
                "name": row["name"],
                "wins": row["wins"],
                "losses": row["losses"],
                "ties": row["ties"],
                "games_played": games,
                "points": row["points"] or 0,
                "win_rate": round(row["wins"] / games * 100, 1) if games > 0 else 0,
                "last_played": row["last_played"]
            }


# =============================================================================
# HTTP HANDLER
# =============================================================================

# Global database instance
db: Optional[LeaderboardDB] = None


class LeaderboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the leaderboard API."""
    
    def _send_json(self, data: dict, status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def _send_error(self, message: str, status: int = 400):
        """Send an error response."""
        self._send_json({"error": message}, status)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        if path == "/" or path == "/health":
            # Health check
            self._send_json({
                "status": "ok",
                "service": "Blackjack Leaderboard",
                "endpoints": {
                    "GET /leaderboard": "Get top players",
                    "GET /player?name=<name>": "Get player stats",
                    "POST /submit": "Submit game results"
                }
            })
        
        elif path == "/leaderboard":
            # Get leaderboard
            limit = int(query.get("limit", [10])[0])
            limit = min(max(limit, 1), 100)  # Clamp between 1-100
            
            leaderboard = db.get_leaderboard(limit)
            self._send_json({
                "leaderboard": leaderboard,
                "total_players": len(leaderboard)
            })
        
        elif path == "/player":
            # Get specific player
            name = query.get("name", [None])[0]
            if not name:
                self._send_error("Missing 'name' parameter")
                return
            
            player = db.get_player(name)
            if player:
                self._send_json({"player": player})
            else:
                self._send_error(f"Player '{name}' not found", 404)
        
        else:
            self._send_error("Not found", 404)
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/submit":
            # Submit game results
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode()
                data = json.loads(body)
                
                # Validate required fields
                required = ["player_name", "wins", "losses", "ties"]
                for field in required:
                    if field not in data:
                        self._send_error(f"Missing required field: {field}")
                        return
                
                # Submit to database
                result = db.submit_result(
                    player_name=data["player_name"],
                    wins=int(data["wins"]),
                    losses=int(data["losses"]),
                    ties=int(data["ties"]),
                    points=int(data.get("points", 0))
                )
                
                self._send_json({
                    "success": True,
                    "message": "Results submitted successfully",
                    "player": result
                })
                
            except json.JSONDecodeError:
                self._send_error("Invalid JSON")
            except ValueError as e:
                self._send_error(f"Invalid data: {e}")
            except Exception as e:
                self._send_error(f"Server error: {e}", 500)
        
        else:
            self._send_error("Not found", 404)
    
    def log_message(self, format, *args):
        """Custom log format."""
        print(f"[Leaderboard] {self.address_string()} - {args[0]}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Start the leaderboard server."""
    global db
    
    # Initialize database
    db = LeaderboardDB(DB_FILE)
    
    # Start server
    server_address = ("", LEADERBOARD_PORT)
    httpd = HTTPServer(server_address, LeaderboardHandler)
    
    print("=" * 60)
    print("  🏆 BLACKJACK LEADERBOARD SERVER")
    print("=" * 60)
    print(f"  Running on port {LEADERBOARD_PORT}")
    print(f"  Database: {DB_FILE}")
    print()
    print("  Endpoints:")
    print(f"    GET  http://localhost:{LEADERBOARD_PORT}/leaderboard")
    print(f"    GET  http://localhost:{LEADERBOARD_PORT}/player?name=<name>")
    print(f"    POST http://localhost:{LEADERBOARD_PORT}/submit")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down leaderboard server...")
        httpd.shutdown()


if __name__ == "__main__":
    main()

