"""
Blackjack Client Application.
Listens for server offers via UDP and plays games via TCP.
"""

import socket
import sys
import time
from typing import List, Tuple, Optional

from config import (
    UDP_BROADCAST_PORT, CLIENT_NAME, SOCKET_TIMEOUT,
    RESULT_ONGOING, RESULT_WIN, RESULT_LOSS, RESULT_TIE,
    SERVER_PAYLOAD_SIZE
)
from protocol import (
    unpack_offer, pack_request, pack_client_payload, unpack_server_payload
)
from game_logic import (
    Card, card_value, format_card, 
    calculate_odds_if_hit, calculate_odds_if_stand, get_recommendation
)
from utils import (
    log_info, log_success, log_warning, log_error,
    display_client_started, display_welcome, display_game_state, display_result,
    colored, Colors, bold, draw_box
)


# =============================================================================
# STATISTICS
# =============================================================================

class GameStats:
    """Track game statistics across sessions."""
    
    def __init__(self):
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.total_rounds = 0
    
    def record_win(self):
        self.wins += 1
        self.total_rounds += 1
    
    def record_loss(self):
        self.losses += 1
        self.total_rounds += 1
    
    def record_tie(self):
        self.ties += 1
        self.total_rounds += 1
    
    def win_rate(self) -> float:
        if self.total_rounds == 0:
            return 0.0
        return (self.wins / self.total_rounds) * 100
    
    def __str__(self):
        return f"W:{self.wins} L:{self.losses} T:{self.ties} ({self.win_rate():.1f}%)"


# =============================================================================
# HELPER FUNCTIONS  
# =============================================================================

def recv_exact(sock: socket.socket, num_bytes: int) -> bytes:
    """
    Receive exactly num_bytes from socket.
    TCP may deliver data in chunks, so we need to loop until we have all bytes.
    
    Args:
        sock: Socket to receive from
        num_bytes: Exact number of bytes to receive
        
    Returns:
        bytes: Exactly num_bytes of data, or empty bytes if connection closed
    """
    data = b''
    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))
        if not chunk:
            return b''  # Connection closed
        data += chunk
    return data


# =============================================================================
# UDP LISTENER
# =============================================================================

def listen_for_offer() -> Tuple[str, int, str]:
    """
    Listen for server offer broadcasts.
    
    Returns:
        Tuple of (server_ip, tcp_port, server_name)
    """
    log_info(f"Listening for offers on UDP port {UDP_BROADCAST_PORT}...")
    
    # Create UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # On Windows, SO_REUSEPORT doesn't exist, use SO_REUSEADDR
    try:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass  # SO_REUSEPORT not available on Windows
    
    udp_socket.bind(('', UDP_BROADCAST_PORT))
    
    while True:
        try:
            data, addr = udp_socket.recvfrom(1024)
            server_ip = addr[0]
            
            # Parse the offer
            offer = unpack_offer(data)
            if offer is None:
                continue
            
            tcp_port, server_name = offer
            
            log_success(f"Received offer from {server_ip} - \"{server_name}\"")
            udp_socket.close()
            return (server_ip, tcp_port, server_name)
            
        except Exception as e:
            log_warning(f"Error receiving offer: {e}")
            continue


# =============================================================================
# GAME PLAY
# =============================================================================

def format_cards_display(cards: List[Tuple[int, int]]) -> str:
    """Format a list of cards for display."""
    return ' '.join(format_card(rank, suit) for rank, suit in cards)


def play_game(server_ip: str, tcp_port: int, server_name: str, 
              num_rounds: int, stats: GameStats):
    """
    Connect to server and play the specified number of rounds.
    
    Args:
        server_ip: Server IP address
        tcp_port: Server TCP port
        server_name: Server's team name
        num_rounds: Number of rounds to play
        stats: GameStats object to update
    """
    log_info(f"Connecting to {server_name} at {server_ip}:{tcp_port}...")
    
    try:
        # Create TCP connection
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(SOCKET_TIMEOUT)
        tcp_socket.connect((server_ip, tcp_port))
        
        log_success("Connected!")
        
        # Send request with number of rounds
        request = pack_request(num_rounds, CLIENT_NAME)
        tcp_socket.send(request)
        
        # Play rounds
        for round_num in range(1, num_rounds + 1):
            print(f"\n{colored('='*60, Colors.CYAN)}")
            print(f"  📍 Round {round_num}/{num_rounds} vs {server_name}")
            print(f"{colored('='*60, Colors.CYAN)}\n")
            
            result = play_round(tcp_socket, stats)
            
            if result is None:
                log_error("Connection lost during round")
                break
            
            # Small delay between rounds
            time.sleep(0.5)
        
        tcp_socket.close()
        
    except socket.timeout:
        log_error("Connection timed out")
    except ConnectionRefusedError:
        log_error("Connection refused by server")
    except Exception as e:
        log_error(f"Connection error: {e}")


def play_round(tcp_socket: socket.socket, stats: GameStats) -> Optional[int]:
    """
    Play a single round of blackjack.
    
    Args:
        tcp_socket: Connected TCP socket
        stats: GameStats object to update
        
    Returns:
        Result code (RESULT_WIN/LOSS/TIE) or None if error
    """
    player_cards: List[Tuple[int, int]] = []
    dealer_cards: List[Tuple[int, int]] = []
    known_cards: List[Tuple[int, int]] = []
    
    # =========================================================================
    # RECEIVE INITIAL CARDS
    # =========================================================================
    
    # Receive player's 2 cards
    for i in range(2):
        data = recv_exact(tcp_socket, SERVER_PAYLOAD_SIZE)
        if not data:
            return None
        
        payload = unpack_server_payload(data)
        if payload is None:
            log_error("Invalid payload from server")
            continue
        
        result, rank, suit = payload
        if rank > 0:  # Valid card
            player_cards.append((rank, suit))
            known_cards.append((rank, suit))
    
    # Receive dealer's visible card
    data = recv_exact(tcp_socket, SERVER_PAYLOAD_SIZE)
    if not data:
        return None
    
    payload = unpack_server_payload(data)
    if payload:
        result, rank, suit = payload
        if rank > 0:
            dealer_cards.append((rank, suit))
            known_cards.append((rank, suit))
    
    # Calculate initial totals
    player_total = sum(card_value(rank) for rank, suit in player_cards)
    dealer_visible_value = card_value(dealer_cards[0][0]) if dealer_cards else 0
    
    # =========================================================================
    # PLAYER'S TURN
    # =========================================================================
    
    while True:
        # Calculate odds
        hit_odds = calculate_odds_if_hit(player_total, dealer_visible_value, known_cards)
        stand_odds = calculate_odds_if_stand(player_total, dealer_visible_value, known_cards)
        rec, hit_win, stand_win = get_recommendation(player_total, dealer_visible_value, known_cards)
        
        # Display game state with odds
        print(display_game_state(
            player_cards=format_cards_display(player_cards),
            player_total=player_total,
            dealer_cards=format_cards_display(dealer_cards) + " [?]",
            dealer_visible=dealer_visible_value,
            odds_hit=hit_odds,
            odds_stand=stand_odds,
            recommendation=rec
        ))
        print()
        
        # Get player decision
        while True:
            try:
                decision = input(f"  Enter decision ({colored('H', Colors.GREEN)}it / {colored('S', Colors.YELLOW)}tand): ").strip().lower()
                if decision in ['h', 'hit', 's', 'stand']:
                    break
                print(f"  {colored('Invalid input. Please enter H or S.', Colors.RED)}")
            except EOFError:
                decision = 's'
                break
        
        # Send decision to server
        if decision in ['h', 'hit']:
            payload = pack_client_payload("Hit")
            tcp_socket.send(payload)
            
            # Receive new card
            data = recv_exact(tcp_socket, SERVER_PAYLOAD_SIZE)
            if not data:
                return None
            
            response = unpack_server_payload(data)
            if response is None:
                log_error("Invalid response from server")
                continue
            
            result, rank, suit = response
            
            if rank > 0:
                player_cards.append((rank, suit))
                known_cards.append((rank, suit))
                player_total = sum(card_value(r) for r, s in player_cards)
                
                print(f"\n  {colored('Drew:', Colors.CYAN)} {format_card(rank, suit)} (Total: {player_total})")
            
            # Check for bust
            if result == RESULT_LOSS:
                print(f"\n  {colored('💥 BUST! You lose this round.', Colors.RED)}")
                stats.record_loss()
                
                print(display_result(
                    RESULT_LOSS, player_total, 0,
                    stats.wins, stats.losses, stats.ties
                ))
                return RESULT_LOSS
        else:
            # Stand
            payload = pack_client_payload("Stand")
            tcp_socket.send(payload)
            print(f"\n  {colored('You stand at', Colors.YELLOW)} {player_total}")
            break
    
    # =========================================================================
    # DEALER'S TURN
    # =========================================================================
    
    print(f"\n  {colored('Dealer reveals hidden card...', Colors.CYAN)}")
    
    # Receive dealer's hidden card
    data = recv_exact(tcp_socket, SERVER_PAYLOAD_SIZE)
    if not data:
        return None
    
    response = unpack_server_payload(data)
    if response and response[1] > 0:
        result, rank, suit = response
        dealer_cards.append((rank, suit))
        print(f"  Dealer has: {format_cards_display(dealer_cards)}")
    
    dealer_total = sum(card_value(r) for r, s in dealer_cards)
    print(f"  Dealer total: {dealer_total}")
    
    # Receive any additional dealer cards until result
    while True:
        data = recv_exact(tcp_socket, SERVER_PAYLOAD_SIZE)
        if not data:
            return None
        
        response = unpack_server_payload(data)
        if response is None:
            continue
        
        result, rank, suit = response
        
        # Check if we got a card
        if rank > 0:
            dealer_cards.append((rank, suit))
            dealer_total = sum(card_value(r) for r, s in dealer_cards)
            print(f"  Dealer draws: {format_card(rank, suit)} (Total: {dealer_total})")
        
        # Check for final result
        if result != RESULT_ONGOING:
            break
    
    # =========================================================================
    # DISPLAY RESULT
    # =========================================================================
    
    print()
    
    if result == RESULT_WIN:
        stats.record_win()
    elif result == RESULT_LOSS:
        stats.record_loss()
    else:
        stats.record_tie()
    
    print(display_result(
        result, player_total, dealer_total,
        stats.wins, stats.losses, stats.ties
    ))
    
    return result


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point for the client."""
    
    print(display_welcome())
    print(display_client_started(CLIENT_NAME))
    print()
    
    stats = GameStats()
    
    while True:
        # Ask for number of rounds
        while True:
            try:
                num_rounds = input(f"\n  How many rounds do you want to play? (1-255): ").strip()
                num_rounds = int(num_rounds)
                if 1 <= num_rounds <= 255:
                    break
                print(f"  {colored('Please enter a number between 1 and 255.', Colors.RED)}")
            except ValueError:
                print(f"  {colored('Please enter a valid number.', Colors.RED)}")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{colored('Goodbye!', Colors.GREEN)}")
                return
        
        print()
        
        # Listen for server offer
        try:
            server_ip, tcp_port, server_name = listen_for_offer()
        except KeyboardInterrupt:
            print(f"\n{colored('Goodbye!', Colors.GREEN)}")
            return
        
        # Play game
        play_game(server_ip, tcp_port, server_name, num_rounds, stats)
        
        # Print session summary
        print(f"\n{colored('='*50, Colors.GREEN)}")
        print(f"  Finished playing {num_rounds} rounds")
        print(f"  Win rate: {stats.win_rate():.1f}%")
        print(f"  Total: {stats}")
        print(f"{colored('='*50, Colors.GREEN)}\n")


if __name__ == "__main__":
    main()
