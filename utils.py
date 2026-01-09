"""
Utility functions for display and logging in the Blackjack application.
Provides colorful console output and formatting helpers.
"""

import sys
from typing import List, Tuple
from config import RESULT_WIN, RESULT_LOSS, RESULT_TIE, RESULT_ONGOING


# =============================================================================
# ANSI COLOR CODES
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Regular colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    # Suit colors
    HEART = '\033[91m'    # Red
    DIAMOND = '\033[91m'  # Red
    CLUB = '\033[97m'     # White
    SPADE = '\033[97m'    # White


def colored(text: str, color: str) -> str:
    """Wrap text with color codes."""
    return f"{color}{text}{Colors.RESET}"


def bold(text: str) -> str:
    """Make text bold."""
    return f"{Colors.BOLD}{text}{Colors.RESET}"


# =============================================================================
# CARD DISPLAY
# =============================================================================

def format_card_colored(rank: int, suit: int) -> str:
    """
    Format a card with color based on suit.
    
    Args:
        rank: Card rank (1-13)
        suit: Card suit (0-3)
        
    Returns:
        str: Colored card string
    """
    from config import RANK_NAMES, SUIT_SYMBOLS
    
    card_str = f"{RANK_NAMES[rank]}{SUIT_SYMBOLS[suit]}"
    
    if suit <= 1:  # Hearts and Diamonds are red
        return colored(card_str, Colors.RED)
    else:  # Clubs and Spades are white/default
        return colored(card_str, Colors.WHITE)


# =============================================================================
# BOX DRAWING
# =============================================================================

def draw_box(lines: List[str], width: int = 60, title: str = None) -> str:
    """
    Draw a box around text content.
    
    Args:
        lines: List of text lines
        width: Box width
        title: Optional title for the box
        
    Returns:
        str: Formatted box string
    """
    # Box characters
    TL, TR, BL, BR = '╔', '╗', '╚', '╝'
    H, V = '═', '║'
    ML, MR = '╠', '╣'
    
    result = []
    
    # Top border
    if title:
        title_str = f" {title} "
        padding = width - len(title_str) - 2
        left_pad = padding // 2
        right_pad = padding - left_pad
        result.append(f"{TL}{H * left_pad}{title_str}{H * right_pad}{TR}")
    else:
        result.append(f"{TL}{H * (width - 2)}{TR}")
    
    # Content lines
    for line in lines:
        # Pad line to width (account for color codes)
        visible_len = len(strip_ansi(line))
        padding = width - 4 - visible_len
        result.append(f"{V} {line}{' ' * padding} {V}")
    
    # Bottom border
    result.append(f"{BL}{H * (width - 2)}{BR}")
    
    return '\n'.join(result)


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


# =============================================================================
# GAME DISPLAY
# =============================================================================

def display_game_state(player_cards: str, player_total: int, 
                       dealer_cards: str, dealer_visible: int = None,
                       odds_hit: Tuple[float, float, float] = None,
                       odds_stand: Tuple[float, float, float] = None,
                       recommendation: str = None) -> str:
    """
    Display the current game state with odds.
    
    Args:
        player_cards: Formatted player cards string
        player_total: Player's hand total
        dealer_cards: Formatted dealer cards string
        dealer_visible: Dealer's visible card value (if hidden card exists)
        odds_hit: (win%, lose%, tie%) if hit
        odds_stand: (win%, lose%, tie%) if stand
        recommendation: Recommended action
        
    Returns:
        str: Formatted game state display
    """
    lines = []
    
    # Player's hand
    lines.append(f"Your hand: {player_cards}  (Total: {bold(str(player_total))})")
    
    # Dealer's hand
    if dealer_visible is not None:
        lines.append(f"Dealer shows: {dealer_cards}")
    else:
        lines.append(f"Dealer's hand: {dealer_cards}")
    
    # Odds display
    if odds_hit and odds_stand:
        lines.append("")
        lines.append(colored("📊 ODDS CALCULATOR", Colors.CYAN))
        lines.append("")
        lines.append("If you HIT:")
        lines.append(f"  Win: {colored(f'{odds_hit[0]}%', Colors.GREEN)} | " +
                    f"Lose: {colored(f'{odds_hit[1]}%', Colors.RED)} | " +
                    f"Tie: {colored(f'{odds_hit[2]}%', Colors.YELLOW)}")
        lines.append("")
        lines.append("If you STAND:")
        lines.append(f"  Win: {colored(f'{odds_stand[0]}%', Colors.GREEN)} | " +
                    f"Lose: {colored(f'{odds_stand[1]}%', Colors.RED)} | " +
                    f"Tie: {colored(f'{odds_stand[2]}%', Colors.YELLOW)}")
        
        if recommendation:
            diff = abs(odds_hit[0] - odds_stand[0])
            lines.append("")
            lines.append(f"💡 Recommendation: {colored(recommendation, Colors.GREEN)} (+{diff:.1f}% win chance)")
    
    return draw_box(lines, width=65, title="🎰 BLACKJACK")


def display_result(result: int, player_total: int, dealer_total: int,
                   wins: int, losses: int, ties: int) -> str:
    """
    Display the round result.
    
    Args:
        result: RESULT_WIN, RESULT_LOSS, or RESULT_TIE
        player_total: Player's final hand total
        dealer_total: Dealer's final hand total
        wins: Total wins so far
        losses: Total losses so far
        ties: Total ties so far
        
    Returns:
        str: Formatted result display
    """
    lines = []
    
    if result == RESULT_WIN:
        lines.append(colored("🎉 YOU WIN! 🎉", Colors.GREEN))
    elif result == RESULT_LOSS:
        lines.append(colored("💔 You Lose", Colors.RED))
    else:
        lines.append(colored("🤝 It's a Tie", Colors.YELLOW))
    
    lines.append("")
    lines.append(f"Your total: {player_total}  |  Dealer total: {dealer_total}")
    lines.append("")
    
    total_games = wins + losses + ties
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    lines.append(f"Record: {colored(str(wins), Colors.GREEN)}W / " +
                f"{colored(str(losses), Colors.RED)}L / " +
                f"{colored(str(ties), Colors.YELLOW)}T  " +
                f"(Win rate: {win_rate:.1f}%)")
    
    return draw_box(lines, width=50, title="ROUND RESULT")


def display_welcome() -> str:
    """Display welcome banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     ♠ ♥ ♣ ♦   B L A C K J A C K   ♦ ♣ ♥ ♠              ║
    ║                                                          ║
    ║     Intro to Computer Networks 2025 Hackathon            ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    return colored(banner, Colors.CYAN)


def display_server_started(ip: str, tcp_port: int, server_name: str) -> str:
    """Display server started message."""
    lines = [
        f"Server Name: {colored(server_name, Colors.GREEN)}",
        f"IP Address: {colored(ip, Colors.CYAN)}",
        f"TCP Port: {colored(str(tcp_port), Colors.YELLOW)}",
        "",
        "Broadcasting offers via UDP...",
        colored("Waiting for players to connect...", Colors.DIM)
    ]
    return draw_box(lines, width=50, title="🎰 SERVER STARTED")


def display_client_started(client_name: str) -> str:
    """Display client started message."""
    lines = [
        f"Client Name: {colored(client_name, Colors.GREEN)}",
        "",
        "Listening for server offers on UDP port 13122...",
    ]
    return draw_box(lines, width=50, title="🎴 CLIENT STARTED")


# =============================================================================
# LOGGING
# =============================================================================

def log_info(message: str):
    """Print info message."""
    print(f"{colored('[INFO]', Colors.CYAN)} {message}")


def log_success(message: str):
    """Print success message."""
    print(f"{colored('[OK]', Colors.GREEN)} {message}")


def log_warning(message: str):
    """Print warning message."""
    print(f"{colored('[WARN]', Colors.YELLOW)} {message}")


def log_error(message: str):
    """Print error message."""
    print(f"{colored('[ERROR]', Colors.RED)} {message}")


def log_debug(message: str):
    """Print debug message."""
    print(f"{colored('[DEBUG]', Colors.DIM)} {message}")
