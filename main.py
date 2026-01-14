"""
Main entry point for the Blackjack game.
Allows user to choose between running as a client (player) or server (dealer).
"""

import socket
import sys
import time
from typing import Optional, Tuple

from config import UDP_BROADCAST_PORT
from protocol import unpack_offer
from utils import (
    log_info, log_success, log_warning, log_error,
    display_welcome, display_leaderboard_intro, colored, Colors, draw_box
)


def check_dealer_available(timeout: float = 5.0) -> Optional[Tuple[str, int, str]]:
    """
    Check if a dealer (server) is available by listening for UDP offers.
    
    Args:
        timeout: Maximum time to wait for an offer (in seconds)
        
    Returns:
        Tuple of (server_ip, tcp_port, server_name) if found, None otherwise
    """
    log_info(f"Checking for available dealers (timeout: {timeout}s)...")
    
    # Create UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # On Windows, SO_REUSEPORT doesn't exist, use SO_REUSEADDR
    try:
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass  # SO_REUSEPORT not available on Windows
    
    udp_socket.bind(('', UDP_BROADCAST_PORT))
    udp_socket.settimeout(timeout)
    
    try:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                remaining_time = timeout - (time.time() - start_time)
                udp_socket.settimeout(remaining_time)
                
                data, addr = udp_socket.recvfrom(1024)
                server_ip = addr[0]
                
                # Parse the offer
                offer = unpack_offer(data)
                if offer is None:
                    continue
                
                tcp_port, server_name = offer
                
                log_success(f"Found dealer: {server_name} at {server_ip}:{tcp_port}")
                udp_socket.close()
                return (server_ip, tcp_port, server_name)
                
            except socket.timeout:
                # Timeout reached, no dealer found
                break
            except Exception as e:
                log_warning(f"Error receiving offer: {e}")
                continue
        
        udp_socket.close()
        return None
        
    except Exception as e:
        log_error(f"Error checking for dealer: {e}")
        udp_socket.close()
        return None


def run_client(show_stats: bool = True) -> str:
    """Run the client application.
    
    Args:
        show_stats: Whether to show statistics (default True)
        
    Returns:
        str: "menu" to return to main menu, "exit" to quit
    """
    import client
    return client.main(show_stats)


def run_server():
    """Run the server application."""
    import server
    server.main()


def display_leaderboard():
    """Display the global leaderboard."""
    from leaderboard_client import LeaderboardClient, format_leaderboard, format_player_stats
    
    client = LeaderboardClient()
    
    if not client.is_available():
        print(f"\n  {colored('❌ Leaderboard server is not available!', Colors.RED)}")
        print(f"  {colored('Make sure leaderboard_server.py is running.', Colors.YELLOW)}\n")
        input(f"  Press {colored('Enter', Colors.CYAN)} to return to the main menu...")
        print()
        return
    
    while True:
        print()
        print(f"{colored('='*60, Colors.YELLOW)}")
        print(f"  {colored('🏆 LEADERBOARD MENU', Colors.BOLD)}")
        print(f"  {colored('1', Colors.GREEN)} - View Top 10")
        print(f"  {colored('2', Colors.CYAN)} - View Top 25")
        print(f"  {colored('3', Colors.MAGENTA)} - Search Player")
        print(f"  {colored('4', Colors.RED)} - Back to main menu")
        print(f"{colored('='*60, Colors.YELLOW)}\n")
        
        lb_choice = input(f"  Enter your choice: ").strip()
        
        if lb_choice == '1':
            leaderboard = client.get_leaderboard(10)
            if leaderboard:
                print()
                print(format_leaderboard(leaderboard, "🏆 TOP 10 PLAYERS"))
            else:
                print(f"\n  {colored('Could not fetch leaderboard.', Colors.RED)}")
        
        elif lb_choice == '2':
            leaderboard = client.get_leaderboard(25)
            if leaderboard:
                print()
                print(format_leaderboard(leaderboard, "🏆 TOP 25 PLAYERS"))
            else:
                print(f"\n  {colored('Could not fetch leaderboard.', Colors.RED)}")
        
        elif lb_choice == '3':
            player_name = input(f"\n  Enter player name: ").strip()
            if player_name:
                player = client.get_player(player_name)
                if player:
                    print()
                    print(format_player_stats(player))
                else:
                    msg = f'Player "{player_name}" not found.'
                    print(f"\n  {colored(msg, Colors.YELLOW)}")
        
        elif lb_choice == '4':
            print()
            return
        
        else:
            print(f"  {colored('Invalid choice.', Colors.RED)}")


def display_instructions():
    """Display game instructions and explanation."""
    lines = [
        colored("📖 GAME OVERVIEW", Colors.CYAN),
        "",
        "Blackjack is a card game where you try to get a hand value",
        "closer to 21 than the dealer without going over.",
        "",
        colored("🎯 OBJECTIVE", Colors.GREEN),
        "",
        "Beat the dealer by:",
        "  • Getting 21 on your first two cards (Blackjack!)",
        "  • Having a higher hand value than the dealer",
        "  • Not going over 21 (busting)",
        "",
        colored("🎴 CARD VALUES", Colors.YELLOW),
        "",
        "  • Ace (A): 1 or 11 (whichever is better)",
        "  • Face cards (J, Q, K): 10",
        "  • Number cards: Their face value",
        "",
        colored("🎮 HOW TO PLAY", Colors.CYAN),
        "",
        "1. You receive 2 cards face up",
        "2. The dealer receives 2 cards (one face up, one hidden)",
        "3. On your turn, you can:",
        "   " + colored("H", Colors.GREEN) + "it - Take another card",
        "   " + colored("S", Colors.YELLOW) + "tand - Keep your current hand",
        "4. If you go over 21, you bust and lose",
        "5. After you stand, the dealer reveals their hidden card",
        "6. Dealer must hit until they reach 17 or higher",
        "7. Compare hands - closest to 21 wins!",
        "",
        colored("🌐 NETWORK GAME", Colors.MAGENTA),
        "",
        "This is a network-based Blackjack game:",
        "",
        colored("Dealer (Server):", Colors.YELLOW),
        "  • Broadcasts game availability via UDP",
        "  • Handles game logic and card dealing",
        "  • Manages multiple players",
        "",
        colored("Player (Client):", Colors.GREEN),
        "  • Listens for dealer broadcasts",
        "  • Connects to dealer via TCP",
        "  • Makes decisions and plays rounds",
        "",
        colored("💡 TIPS", Colors.CYAN),
        "",
        "  • The game shows odds calculations to help you decide",
        "  • You can play multiple rounds in one session",
        "  • Your win/loss record is tracked",
        "  • A dealer must be running before you can play",
        "",
        colored("⚠️  IMPORTANT", Colors.RED),
        "",
        "  • You need a dealer (server) running to play as a client",
        "  • Start the dealer first, then connect as a player",
        "  • Both can run on the same machine or different machines",
    ]
    
    print(draw_box(lines, width=70, title="📚 GAME INSTRUCTIONS"))
    print()
    
    input(f"  Press {colored('Enter', Colors.CYAN)} to return to the main menu...")
    print()


def main():
    """Main entry point."""
    print(display_welcome())
    print(display_leaderboard_intro())
    print()
    
    while True:
        try:
            print(f"{colored('='*60, Colors.CYAN)}")
            print(f"  {colored('Choose your role:', Colors.BOLD)}")
            print(f"  {colored('1', Colors.GREEN)} - Player (Client)")
            print(f"  {colored('2', Colors.YELLOW)} - Dealer (Server)")
            print(f"  {colored('3', Colors.CYAN)} - Instructions & Help")
            print(f"  {colored('4', Colors.MAGENTA)} - 🏆 Leaderboard")
            print(f"{colored('='*60, Colors.CYAN)}\n")
            
            choice = input(f"  Enter your choice ({colored('1', Colors.GREEN)}/{colored('2', Colors.YELLOW)}/{colored('3', Colors.CYAN)}/{colored('4', Colors.MAGENTA)}): ").strip()
            
            if choice == '1':
                # User wants to be a client (player) - ask about statistics
                print()
                print(f"{colored('='*60, Colors.GREEN)}")
                print(f"  {colored('Choose game mode:', Colors.BOLD)}")
                print(f"  {colored('1', Colors.GREEN)} - With Statistics (10 pts per win)")
                print(f"  {colored('2', Colors.YELLOW)} - Without Statistics {colored('(20 pts per win - 2x BONUS!)', Colors.CYAN)}")
                print(f"  {colored('3', Colors.RED)} - Back to main menu")
                print(f"{colored('='*60, Colors.GREEN)}\n")
                
                mode_choice = input(f"  Enter your choice ({colored('1', Colors.GREEN)}/{colored('2', Colors.YELLOW)}/{colored('3', Colors.RED)}): ").strip()
                
                if mode_choice == '3':
                    # Back to main menu
                    print()
                    continue
                elif mode_choice not in ['1', '2']:
                    print(f"  {colored('Invalid choice. Please enter 1, 2, or 3.', Colors.RED)}\n")
                    continue
                
                show_stats = (mode_choice == '1')
                
                print()
                print(f"  {colored('Checking for available dealers...', Colors.CYAN)}")
                print()
                
                dealer_info = check_dealer_available(timeout=5.0)
                
                if dealer_info is None:
                    print()
                    print(f"{colored('='*60, Colors.RED)}")
                    print(f"  {colored('❌ No dealer available!', Colors.RED)}")
                    print(f"  {colored('No dealers are currently broadcasting on the network.', Colors.YELLOW)}")
                    print()
                    print(f"  {colored('What would you like to do?', Colors.CYAN)}")
                    print(f"  {colored('1', Colors.GREEN)} - Try again (wait for a dealer)")
                    print(f"  {colored('2', Colors.YELLOW)} - Switch and become the dealer yourself")
                    print(f"  {colored('3', Colors.RED)} - Exit")
                    print(f"{colored('='*60, Colors.RED)}\n")
                    
                    action = input(f"  Enter your choice ({colored('1', Colors.GREEN)}/{colored('2', Colors.YELLOW)}/{colored('3', Colors.RED)}): ").strip()
                    
                    if action == '1':
                        # Try again
                        print()
                        continue
                    elif action == '2':
                        # Switch to dealer
                        print()
                        print(f"  {colored('Switching to dealer mode...', Colors.CYAN)}\n")
                        run_server()
                        break
                    else:
                        # Exit
                        print(f"\n{colored('Goodbye!', Colors.GREEN)}")
                        return
                
                # Dealer found, run client
                print()
                result = run_client(show_stats)
                if result == "menu":
                    # Return to main menu
                    print()
                    continue
                else:
                    # Exit
                    break
                
            elif choice == '2':
                # User wants to be a server (dealer)
                print()
                print(f"  {colored('Starting dealer (server)...', Colors.CYAN)}\n")
                run_server()
                break
                
            elif choice == '3':
                # User wants to see instructions
                print()
                display_instructions()
                continue
            
            elif choice == '4':
                # User wants to see leaderboard
                display_leaderboard()
                continue
                
            else:
                print(f"  {colored('Invalid choice. Please enter 1, 2, 3, or 4.', Colors.RED)}\n")
                continue
                
        except (EOFError, KeyboardInterrupt):
            print(f"\n{colored('Goodbye!', Colors.GREEN)}")
            return
        except Exception as e:
            log_error(f"Unexpected error: {e}")
            return


if __name__ == "__main__":
    main()

