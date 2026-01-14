"""
Leaderboard Client - API for interacting with the leaderboard server.
Used by game clients to submit results and fetch leaderboards.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, List, Dict

# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_LEADERBOARD_HOST = "localhost"
DEFAULT_LEADERBOARD_PORT = 8888
REQUEST_TIMEOUT = 5  # seconds

# =============================================================================
# LEADERBOARD CLIENT
# =============================================================================

class LeaderboardClient:
    """Client for interacting with the leaderboard server."""
    
    def __init__(self, host: str = DEFAULT_LEADERBOARD_HOST, port: int = DEFAULT_LEADERBOARD_PORT):
        """
        Initialize leaderboard client.
        
        Args:
            host: Leaderboard server hostname
            port: Leaderboard server port
        """
        self.base_url = f"http://{host}:{port}"
    
    def _request(self, method: str, endpoint: str, data: Optional[dict] = None) -> Optional[dict]:
        """
        Make an HTTP request to the leaderboard server.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            data: Optional JSON data for POST requests
            
        Returns:
            dict: Response data or None if error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                req = urllib.request.Request(url)
            else:
                json_data = json.dumps(data).encode() if data else None
                req = urllib.request.Request(
                    url, 
                    data=json_data,
                    headers={"Content-Type": "application/json"}
                )
                req.method = method
            
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                return json.loads(response.read().decode())
                
        except urllib.error.URLError:
            return None
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode())
            except:
                return None
        except Exception:
            return None
    
    def is_available(self) -> bool:
        """Check if the leaderboard server is available."""
        result = self._request("GET", "/health")
        return result is not None and result.get("status") == "ok"
    
    def submit_results(self, player_name: str, wins: int, losses: int, ties: int, points: int = 0) -> Optional[dict]:
        """
        Submit game results to the leaderboard.
        
        Args:
            player_name: Player's name
            wins: Number of wins
            losses: Number of losses
            ties: Number of ties
            points: Points earned
            
        Returns:
            dict: Updated player stats or None if error
        """
        result = self._request("POST", "/submit", {
            "player_name": player_name,
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "points": points
        })
        
        if result and result.get("success"):
            return result.get("player")
        return None
    
    def get_leaderboard(self, limit: int = 10) -> Optional[List[dict]]:
        """
        Fetch the leaderboard.
        
        Args:
            limit: Maximum number of players to fetch
            
        Returns:
            list: List of player stats or None if error
        """
        result = self._request("GET", f"/leaderboard?limit={limit}")
        
        if result:
            return result.get("leaderboard", [])
        return None
    
    def get_player(self, player_name: str) -> Optional[dict]:
        """
        Get stats for a specific player.
        
        Args:
            player_name: Player's name
            
        Returns:
            dict: Player stats or None if not found/error
        """
        # URL encode the player name
        encoded_name = urllib.parse.quote(player_name)
        result = self._request("GET", f"/player?name={encoded_name}")
        
        if result:
            return result.get("player")
        return None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_leaderboard(leaderboard: List[dict], title: str = "🏆 LEADERBOARD") -> str:
    """
    Format leaderboard for display.
    
    Args:
        leaderboard: List of player stats
        title: Title for the leaderboard
        
    Returns:
        str: Formatted leaderboard string
    """
    if not leaderboard:
        return "  No players on the leaderboard yet!"
    
    lines = []
    lines.append("=" * 75)
    lines.append(f"  {title}")
    lines.append("=" * 75)
    lines.append(f"  {'Rank':<6}{'Player':<18}{'Points':<10}{'Wins':<8}{'Games':<8}{'Win %':<10}")
    lines.append("-" * 75)
    
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    
    for player in leaderboard:
        rank = player["rank"]
        medal = medals.get(rank, "  ")
        name = player["name"][:16]  # Truncate long names
        points = player.get("points", 0)
        
        lines.append(
            f"  {medal}{rank:<4}{name:<18}{points:<10}{player['wins']:<8}"
            f"{player['games_played']:<8}{player['win_rate']:.1f}%"
        )
    
    lines.append("=" * 75)
    
    return "\n".join(lines)


def format_player_stats(player: dict) -> str:
    """
    Format player stats for display.
    
    Args:
        player: Player stats dict
        
    Returns:
        str: Formatted player stats string
    """
    lines = []
    lines.append("=" * 40)
    lines.append(f"  📊 Stats for {player['name']}")
    lines.append("=" * 40)
    lines.append(f"  Points:      {player.get('points', 0)} ⭐")
    lines.append(f"  Wins:        {player['wins']}")
    lines.append(f"  Losses:      {player['losses']}")
    lines.append(f"  Ties:        {player['ties']}")
    lines.append(f"  Games:       {player['games_played']}")
    lines.append(f"  Win Rate:    {player['win_rate']:.1f}%")
    if player.get('last_played'):
        lines.append(f"  Last Played: {player['last_played'][:10]}")
    lines.append("=" * 40)
    
    return "\n".join(lines)


# =============================================================================
# STANDALONE USAGE
# =============================================================================

if __name__ == "__main__":
    # Test the client
    import sys
    
    client = LeaderboardClient()
    
    print("Checking leaderboard server...")
    if not client.is_available():
        print("❌ Leaderboard server is not available!")
        print(f"   Make sure it's running on {client.base_url}")
        sys.exit(1)
    
    print("✅ Leaderboard server is available!\n")
    
    # Fetch and display leaderboard
    leaderboard = client.get_leaderboard(10)
    if leaderboard:
        print(format_leaderboard(leaderboard))
    else:
        print("Could not fetch leaderboard")

