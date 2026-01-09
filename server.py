"""
Blackjack Server Application.
Broadcasts offers via UDP and handles game sessions via TCP.
"""

import socket
import threading
import time
import sys
from typing import Optional

from config import (
    UDP_BROADCAST_PORT, BROADCAST_INTERVAL, SERVER_NAME,
    RESULT_ONGOING, RESULT_WIN, RESULT_LOSS, RESULT_TIE,
    SOCKET_TIMEOUT
)
from protocol import (
    pack_offer, pack_server_payload, unpack_request, unpack_client_payload
)
from game_logic import Deck, Card, calculate_hand_value, card_value
from utils import (
    log_info, log_success, log_warning, log_error,
    display_server_started, display_welcome, colored, Colors
)


# =============================================================================
# GLOBAL STATE
# =============================================================================

running = True  # Global flag to stop all threads


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_local_ip() -> str:
    """Get the local IP address of this machine."""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# =============================================================================
# UDP BROADCASTER
# =============================================================================

def udp_broadcaster(tcp_port: int):
    """
    Broadcast offer messages via UDP every BROADCAST_INTERVAL seconds.
    
    Args:
        tcp_port: The TCP port clients should connect to
    """
    global running
    
    # Create UDP socket for broadcasting
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Create the offer packet
    offer_packet = pack_offer(tcp_port, SERVER_NAME)
    
    log_info(f"UDP broadcaster started on port {UDP_BROADCAST_PORT}")
    
    while running:
        try:
            # Broadcast to all addresses on the network
            udp_socket.sendto(offer_packet, ('<broadcast>', UDP_BROADCAST_PORT))
            time.sleep(BROADCAST_INTERVAL)
        except Exception as e:
            if running:
                log_warning(f"Broadcast error: {e}")
            time.sleep(BROADCAST_INTERVAL)
    
    udp_socket.close()
    log_info("UDP broadcaster stopped")


# =============================================================================
# CLIENT HANDLER
# =============================================================================

def handle_client(client_socket: socket.socket, client_address: tuple):
    """
    Handle a single client connection and game session.
    
    Args:
        client_socket: The client's TCP socket
        client_address: The client's address (ip, port)
    """
    client_ip = client_address[0]
    log_info(f"New connection from {client_ip}")
    
    try:
        client_socket.settimeout(SOCKET_TIMEOUT)
        
        # =====================================================================
        # RECEIVE REQUEST
        # =====================================================================
        
        # Receive the request message
        data = client_socket.recv(1024)
        if not data:
            log_warning(f"Client {client_ip} disconnected before sending request")
            return
        
        request = unpack_request(data)
        if request is None:
            log_error(f"Invalid request from {client_ip}")
            return
        
        num_rounds, client_name = request
        log_success(f"Client '{client_name}' wants to play {num_rounds} rounds")
        
        # =====================================================================
        # GAME LOOP
        # =====================================================================
        
        for round_num in range(1, num_rounds + 1):
            print(f"\n{colored('='*50, Colors.DIM)}")
            print(f"  Round {round_num}/{num_rounds} vs {client_name}")
            print(f"{colored('='*50, Colors.DIM)}")
            
            # Create fresh deck for this round
            deck = Deck()
            
            # Deal initial cards
            player_cards = [deck.deal(), deck.deal()]
            dealer_cards = [deck.deal(), deck.deal()]
            
            player_total = calculate_hand_value(player_cards)
            
            print(f"  Dealt to player: {player_cards[0]} {player_cards[1]} (Total: {player_total})")
            print(f"  Dealer has: {dealer_cards[0]} [hidden]")
            
            # Send player's 2 cards
            for card in player_cards:
                payload = pack_server_payload(RESULT_ONGOING, card.rank, card.suit)
                client_socket.send(payload)
            
            # Send dealer's visible card (first card)
            payload = pack_server_payload(RESULT_ONGOING, dealer_cards[0].rank, dealer_cards[0].suit)
            client_socket.send(payload)
            
            # -----------------------------------------------------------------
            # PLAYER'S TURN
            # -----------------------------------------------------------------
            
            player_busted = False
            
            while True:
                # Wait for player decision
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        log_warning(f"Client {client_ip} disconnected mid-game")
                        return
                except socket.timeout:
                    log_warning(f"Client {client_ip} timed out")
                    return
                
                decision = unpack_client_payload(data)
                if decision is None:
                    log_error(f"Invalid payload from {client_ip}")
                    continue
                
                print(f"  Player chose: {decision}")
                
                if decision == "Stand":
                    break
                
                # Player hits - deal a new card
                new_card = deck.deal()
                player_cards.append(new_card)
                player_total = calculate_hand_value(player_cards)
                
                print(f"  Dealt: {new_card} (New total: {player_total})")
                
                # Check for bust
                if player_total > 21:
                    # Player busted - send card with loss result
                    payload = pack_server_payload(RESULT_LOSS, new_card.rank, new_card.suit)
                    client_socket.send(payload)
                    print(f"  {colored('Player BUSTED!', Colors.RED)}")
                    player_busted = True
                    break
                else:
                    # Send the new card
                    payload = pack_server_payload(RESULT_ONGOING, new_card.rank, new_card.suit)
                    client_socket.send(payload)
            
            # -----------------------------------------------------------------
            # DEALER'S TURN (if player didn't bust)
            # -----------------------------------------------------------------
            
            if not player_busted:
                # Reveal hidden card
                print(f"  Dealer reveals: {dealer_cards[1]}")
                payload = pack_server_payload(RESULT_ONGOING, dealer_cards[1].rank, dealer_cards[1].suit)
                client_socket.send(payload)
                
                dealer_total = calculate_hand_value(dealer_cards)
                print(f"  Dealer total: {dealer_total}")
                
                # Dealer hits until 17 or more
                while dealer_total < 17:
                    new_card = deck.deal()
                    dealer_cards.append(new_card)
                    dealer_total = calculate_hand_value(dealer_cards)
                    
                    print(f"  Dealer draws: {new_card} (Total: {dealer_total})")
                    
                    # Send dealer's new card
                    payload = pack_server_payload(RESULT_ONGOING, new_card.rank, new_card.suit)
                    client_socket.send(payload)
                
                # -----------------------------------------------------------------
                # DETERMINE WINNER
                # -----------------------------------------------------------------
                
                if dealer_total > 21:
                    print(f"  {colored('Dealer BUSTED! Player wins!', Colors.GREEN)}")
                    result = RESULT_WIN
                elif dealer_total > player_total:
                    print(f"  {colored('Dealer wins!', Colors.RED)} ({dealer_total} > {player_total})")
                    result = RESULT_LOSS
                elif player_total > dealer_total:
                    print(f"  {colored('Player wins!', Colors.GREEN)} ({player_total} > {dealer_total})")
                    result = RESULT_WIN
                else:
                    print(f"  {colored('Tie!', Colors.YELLOW)} ({player_total} = {dealer_total})")
                    result = RESULT_TIE
                
                # Send final result with a dummy card (0,0)
                payload = pack_server_payload(result, 0, 0)
                client_socket.send(payload)
        
        # =====================================================================
        # SESSION COMPLETE
        # =====================================================================
        
        log_success(f"Completed {num_rounds} rounds with {client_name}")
        
    except socket.timeout:
        log_warning(f"Connection with {client_ip} timed out")
    except ConnectionResetError:
        log_warning(f"Connection with {client_ip} was reset")
    except Exception as e:
        log_error(f"Error handling client {client_ip}: {e}")
    finally:
        client_socket.close()
        log_info(f"Connection with {client_ip} closed")


# =============================================================================
# TCP SERVER
# =============================================================================

def tcp_server(port: int):
    """
    Main TCP server that accepts client connections.
    
    Args:
        port: The TCP port to listen on
    """
    global running
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.settimeout(1.0)  # Allow checking 'running' flag
    
    try:
        server_socket.bind(('', port))
        server_socket.listen(5)
        
        log_info(f"TCP server listening on port {port}")
        
        while running:
            try:
                client_socket, client_address = server_socket.accept()
                # Handle each client in a new thread
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if running:
                    log_error(f"Accept error: {e}")
    
    except Exception as e:
        log_error(f"Server error: {e}")
    finally:
        server_socket.close()
        log_info("TCP server stopped")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point for the server."""
    global running
    
    print(display_welcome())
    
    # Get a random available port for TCP
    temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    temp_socket.bind(('', 0))
    tcp_port = temp_socket.getsockname()[1]
    temp_socket.close()
    
    # Get local IP
    local_ip = get_local_ip()
    
    # Display server info
    print(display_server_started(local_ip, tcp_port, SERVER_NAME))
    print()
    
    # Start UDP broadcaster in background thread
    broadcaster_thread = threading.Thread(
        target=udp_broadcaster,
        args=(tcp_port,),
        daemon=True
    )
    broadcaster_thread.start()
    
    # Start TCP server in main thread (with keyboard interrupt handling)
    try:
        tcp_server(tcp_port)
    except KeyboardInterrupt:
        print(f"\n{colored('Shutting down server...', Colors.YELLOW)}")
        running = False
        time.sleep(1)
        print(colored("Server stopped. Goodbye!", Colors.GREEN))


if __name__ == "__main__":
    main()
