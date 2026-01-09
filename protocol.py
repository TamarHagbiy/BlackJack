"""
Protocol handling for the Blackjack network application.
Provides functions to pack and unpack all message types.
"""

import struct
from config import (
    MAGIC_COOKIE, MSG_TYPE_OFFER, MSG_TYPE_REQUEST, MSG_TYPE_PAYLOAD,
    NAME_FIELD_SIZE, OFFER_PACKET_SIZE, REQUEST_PACKET_SIZE,
    CLIENT_PAYLOAD_SIZE, SERVER_PAYLOAD_SIZE
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def pad_name(name: str) -> bytes:
    """
    Pad or truncate a name to exactly NAME_FIELD_SIZE bytes.
    
    Args:
        name: The team name string
        
    Returns:
        bytes: Exactly 32 bytes, padded with 0x00 or truncated
    """
    name_bytes = name.encode('utf-8')[:NAME_FIELD_SIZE]
    return name_bytes.ljust(NAME_FIELD_SIZE, b'\x00')


def unpad_name(name_bytes: bytes) -> str:
    """
    Remove padding from a name field.
    
    Args:
        name_bytes: 32-byte padded name
        
    Returns:
        str: The original name without padding
    """
    return name_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')


def validate_magic_cookie(data: bytes) -> bool:
    """
    Validate that a packet starts with the correct magic cookie.
    
    Args:
        data: The raw packet bytes
        
    Returns:
        bool: True if valid, False otherwise
    """
    if len(data) < 4:
        return False
    cookie = struct.unpack('>I', data[:4])[0]
    return cookie == MAGIC_COOKIE


# =============================================================================
# OFFER MESSAGE (Server -> Client, UDP)
# Format: Magic(4) + Type(1) + TCPPort(2) + ServerName(32) = 39 bytes
# =============================================================================

def pack_offer(tcp_port: int, server_name: str) -> bytes:
    """
    Create an offer packet for UDP broadcast.
    
    Args:
        tcp_port: The TCP port the server is listening on
        server_name: The server's team name
        
    Returns:
        bytes: 39-byte offer packet
    """
    return struct.pack(
        '>IbH',  # Big-endian: uint32, byte, uint16
        MAGIC_COOKIE,
        MSG_TYPE_OFFER,
        tcp_port
    ) + pad_name(server_name)


def unpack_offer(data: bytes) -> tuple:
    """
    Parse an offer packet.
    
    Args:
        data: Raw offer packet bytes
        
    Returns:
        tuple: (tcp_port, server_name) or None if invalid
    """
    if len(data) < OFFER_PACKET_SIZE:
        return None
    
    if not validate_magic_cookie(data):
        return None
    
    msg_type = struct.unpack('>b', data[4:5])[0]
    if msg_type != MSG_TYPE_OFFER:
        return None
    
    tcp_port = struct.unpack('>H', data[5:7])[0]
    server_name = unpad_name(data[7:39])
    
    return (tcp_port, server_name)


# =============================================================================
# REQUEST MESSAGE (Client -> Server, TCP)
# Format: Magic(4) + Type(1) + Rounds(1) + ClientName(32) = 38 bytes
# =============================================================================

def pack_request(num_rounds: int, client_name: str) -> bytes:
    """
    Create a request packet.
    
    Args:
        num_rounds: Number of rounds to play (1-255)
        client_name: The client's team name
        
    Returns:
        bytes: 38-byte request packet
    """
    return struct.pack(
        '>IbB',  # Big-endian: uint32, byte, unsigned byte
        MAGIC_COOKIE,
        MSG_TYPE_REQUEST,
        min(max(num_rounds, 1), 255)  # Clamp to 1-255
    ) + pad_name(client_name)


def unpack_request(data: bytes) -> tuple:
    """
    Parse a request packet.
    
    Args:
        data: Raw request packet bytes
        
    Returns:
        tuple: (num_rounds, client_name) or None if invalid
    """
    if len(data) < REQUEST_PACKET_SIZE:
        return None
    
    if not validate_magic_cookie(data):
        return None
    
    msg_type = struct.unpack('>b', data[4:5])[0]
    if msg_type != MSG_TYPE_REQUEST:
        return None
    
    num_rounds = struct.unpack('>B', data[5:6])[0]
    client_name = unpad_name(data[6:38])
    
    return (num_rounds, client_name)


# =============================================================================
# CLIENT PAYLOAD (Client -> Server, TCP)
# Format: Magic(4) + Type(1) + Decision(5) = 10 bytes
# Decision is "Hittt" or "Stand"
# =============================================================================

def pack_client_payload(decision: str) -> bytes:
    """
    Create a client payload packet with Hit or Stand decision.
    
    Args:
        decision: "Hit" or "Stand"
        
    Returns:
        bytes: 10-byte client payload packet
    """
    # Convert to protocol format: "Hittt" or "Stand"
    if decision.lower().startswith('h'):
        decision_bytes = b'Hittt'
    else:
        decision_bytes = b'Stand'
    
    return struct.pack(
        '>Ib',
        MAGIC_COOKIE,
        MSG_TYPE_PAYLOAD
    ) + decision_bytes


def unpack_client_payload(data: bytes) -> str:
    """
    Parse a client payload packet.
    
    Args:
        data: Raw client payload bytes
        
    Returns:
        str: "Hit" or "Stand", or None if invalid
    """
    if len(data) < CLIENT_PAYLOAD_SIZE:
        return None
    
    if not validate_magic_cookie(data):
        return None
    
    msg_type = struct.unpack('>b', data[4:5])[0]
    if msg_type != MSG_TYPE_PAYLOAD:
        return None
    
    decision = data[5:10].decode('utf-8', errors='replace')
    
    if decision == 'Hittt':
        return 'Hit'
    elif decision == 'Stand':
        return 'Stand'
    else:
        return None


# =============================================================================
# SERVER PAYLOAD (Server -> Client, TCP)
# Format: Magic(4) + Type(1) + Result(1) + Rank(2) + Suit(1) = 9 bytes
# =============================================================================

def pack_server_payload(result: int, rank: int, suit: int) -> bytes:
    """
    Create a server payload packet with game result and card.
    
    Args:
        result: RESULT_ONGOING, RESULT_TIE, RESULT_LOSS, or RESULT_WIN
        rank: Card rank (1-13, where 1=Ace, 11=J, 12=Q, 13=K)
        suit: Card suit (0=Heart, 1=Diamond, 2=Club, 3=Spade)
        
    Returns:
        bytes: 9-byte server payload packet
    """
    # Rank is encoded as 2 bytes (01-13 as text-like encoding)
    rank_bytes = f'{rank:02d}'.encode('utf-8')
    
    return struct.pack(
        '>IbB',
        MAGIC_COOKIE,
        MSG_TYPE_PAYLOAD,
        result
    ) + rank_bytes + struct.pack('>B', suit)


def unpack_server_payload(data: bytes) -> tuple:
    """
    Parse a server payload packet.
    
    Args:
        data: Raw server payload bytes
        
    Returns:
        tuple: (result, rank, suit) or None if invalid
    """
    if len(data) < SERVER_PAYLOAD_SIZE:
        return None
    
    if not validate_magic_cookie(data):
        return None
    
    msg_type = struct.unpack('>b', data[4:5])[0]
    if msg_type != MSG_TYPE_PAYLOAD:
        return None
    
    result = struct.unpack('>B', data[5:6])[0]
    
    # Rank is 2 bytes as text (e.g., "01", "13")
    try:
        rank = int(data[6:8].decode('utf-8'))
    except ValueError:
        return None
    
    suit = struct.unpack('>B', data[8:9])[0]
    
    return (result, rank, suit)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_message_type(data: bytes) -> int:
    """
    Get the message type from a packet.
    
    Args:
        data: Raw packet bytes
        
    Returns:
        int: Message type, or -1 if invalid
    """
    if len(data) < 5:
        return -1
    if not validate_magic_cookie(data):
        return -1
    return struct.unpack('>b', data[4:5])[0]
