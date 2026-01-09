"""
Configuration constants for the Blackjack network application.
Contains all protocol constants, message types, and team names.
"""

# =============================================================================
# PROTOCOL CONSTANTS
# =============================================================================

# Magic cookie - all messages must start with this value
MAGIC_COOKIE = 0xabcddcba

# Message types
MSG_TYPE_OFFER = 0x02      # Server -> Client (UDP broadcast)
MSG_TYPE_REQUEST = 0x03    # Client -> Server (TCP)
MSG_TYPE_PAYLOAD = 0x04    # Both directions (TCP)

# =============================================================================
# NETWORK CONFIGURATION
# =============================================================================

# UDP port for offer broadcasts (hardcoded as per requirements)
UDP_BROADCAST_PORT = 13122

# Broadcast interval in seconds
BROADCAST_INTERVAL = 1.0

# Socket timeout in seconds (enough time for player to make decisions)
SOCKET_TIMEOUT = 120.0

# =============================================================================
# GAME RESULT CODES
# =============================================================================

RESULT_ONGOING = 0x00  # Round is not over yet
RESULT_TIE = 0x01      # Tie
RESULT_LOSS = 0x02     # Client loses
RESULT_WIN = 0x03      # Client wins

# =============================================================================
# CARD SUITS
# =============================================================================

SUIT_HEART = 0
SUIT_DIAMOND = 1
SUIT_CLUB = 2
SUIT_SPADE = 3

SUIT_SYMBOLS = {
    SUIT_HEART: '♥',
    SUIT_DIAMOND: '♦',
    SUIT_CLUB: '♣',
    SUIT_SPADE: '♠'
}

SUIT_NAMES = {
    SUIT_HEART: 'Heart',
    SUIT_DIAMOND: 'Diamond',
    SUIT_CLUB: 'Club',
    SUIT_SPADE: 'Spade'
}

# =============================================================================
# CARD RANKS
# =============================================================================

RANK_NAMES = {
    1: 'A',
    2: '2',
    3: '3',
    4: '4',
    5: '5',
    6: '6',
    7: '7',
    8: '8',
    9: '9',
    10: '10',
    11: 'J',
    12: 'Q',
    13: 'K'
}

# =============================================================================
# TEAM NAMES (CHANGE THESE!)
# =============================================================================

SERVER_NAME = "BlackjackMasters"  # Name broadcast by your server (max 32 chars)
CLIENT_NAME = "BlackjackMasters"  # Name sent when your client connects (max 32 chars)

# =============================================================================
# PACKET SIZES
# =============================================================================

OFFER_PACKET_SIZE = 39     # 4 + 1 + 2 + 32
REQUEST_PACKET_SIZE = 38   # 4 + 1 + 1 + 32
CLIENT_PAYLOAD_SIZE = 10   # 4 + 1 + 5
SERVER_PAYLOAD_SIZE = 9    # 4 + 1 + 1 + 2 + 1

# Name field size (padded/truncated)
NAME_FIELD_SIZE = 32
