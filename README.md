# 🎰 Blackjack Network Application

## Overview

A **networked Blackjack game** for the Intro to Computer Networks 2025 Hackathon. Features a **Server** (dealer), **Client** (player), and **Leaderboard Server** that communicate using UDP for discovery and TCP for gameplay.

---

## 🚀 Quick Start

### 1. Start the Leaderboard Server (Optional)
```bash
python leaderboard_server.py
```

### 2. Start the Game
```bash
python main.py
```

### 3. Choose Your Role
- **Option 1**: Player (Client) - Play against a dealer
- **Option 2**: Dealer (Server) - Host games for other players
- **Option 3**: Instructions & Help
- **Option 4**: View Leaderboard

---

## 🎮 Game Modes

### With Statistics (10 pts per win)
- See your win/loss record during the game
- **Odds Calculator** shows probability of winning if you Hit vs Stand
- **AI Recommendation** suggests the best move

### Without Statistics - YOLO MODE (20 pts per win) 🚀
- Play **blind** - no odds calculator, no recommendations
- **Double points** as reward for the extra challenge!
- Test your true Blackjack instincts

---

## 🏆 Leaderboard System

A central HTTP server tracks all players globally:

| Outcome | With Stats | Without Stats |
|---------|-----------|---------------|
| Win     | +10 pts   | **+20 pts** (2x!) |
| Tie     | +5 pts    | +5 pts |
| Loss    | +0 pts    | +0 pts |

### Leaderboard Server Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/leaderboard?limit=N` | Get top N players |
| GET | `/player?name=X` | Get specific player stats |
| POST | `/submit` | Submit game results |

---

## 📡 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    NETWORK ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐     UDP Broadcast      ┌──────────────┐     │
│   │              │    (Port 13122)        │              │     │
│   │    SERVER    │ ─────────────────────► │    CLIENT    │     │
│   │   (Dealer)   │                        │   (Player)   │     │
│   │              │ ◄───────────────────── │              │     │
│   └──────────────┘     TCP Connection     └──────────────┘     │
│          │              (Game Play)              │              │
│          │                                       │              │
│          │         ┌──────────────────┐          │              │
│          └────────►│   LEADERBOARD    │◄─────────┘              │
│                    │     SERVER       │                         │
│          HTTP POST │   (Port 8888)    │ HTTP GET                │
│          (Submit)  └──────────────────┘ (Fetch)                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Packet Formats

### 1. Offer Message (Server → Client, UDP Broadcast)

| Field | Size | Description |
|-------|------|-------------|
| Magic Cookie | 4 bytes | `0xabcddcba` |
| Message Type | 1 byte | `0x02` (offer) |
| TCP Port | 2 bytes | Server's TCP port |
| Server Name | 32 bytes | Padded team name |

**Total: 39 bytes**

### 2. Request Message (Client → Server, TCP)

| Field | Size | Description |
|-------|------|-------------|
| Magic Cookie | 4 bytes | `0xabcddcba` |
| Message Type | 1 byte | `0x03` (request) |
| Number of Rounds | 1 byte | 1-255 rounds |
| Client Name | 32 bytes | Padded team name |

**Total: 38 bytes**

### 3. Client Payload (Client → Server, TCP)

| Field | Size | Description |
|-------|------|-------------|
| Magic Cookie | 4 bytes | `0xabcddcba` |
| Message Type | 1 byte | `0x04` (payload) |
| Decision | 5 bytes | `"Hittt"` or `"Stand"` |

**Total: 10 bytes**

### 4. Server Payload (Server → Client, TCP)

| Field | Size | Description |
|-------|------|-------------|
| Magic Cookie | 4 bytes | `0xabcddcba` |
| Message Type | 1 byte | `0x04` (payload) |
| Round Result | 1 byte | `0x00`=ongoing, `0x01`=tie, `0x02`=loss, `0x03`=win |
| Card Rank | 2 bytes | `01-13` (Ace=1, J=11, Q=12, K=13) |
| Card Suit | 1 byte | `0`=Heart, `1`=Diamond, `2`=Club, `3`=Spade |

**Total: 9 bytes**

---

## 🎯 Game Flow Sequence

```
    SERVER                                          CLIENT
      │                                                │
      │◄──────── Listen for UDP offers ────────────────│
      │                                                │
      │──────────── UDP Offer (every 1s) ─────────────►│
      │                                                │
      │◄───────────── TCP Connect ─────────────────────│
      │◄───────────── Request (rounds, name) ──────────│
      │                                                │
      │    ┌─────────── ROUND LOOP ───────────┐        │
      │    │                                  │        │
      │────│── Player Card 1 ─────────────────│───────►│
      │────│── Player Card 2 ─────────────────│───────►│
      │────│── Dealer Visible Card ───────────│───────►│
      │    │                                  │        │
      │    │    ┌── PLAYER TURN ──┐           │        │
      │◄───│────│── Hit/Stand ────│───────────│────────│
      │────│────│── New Card ─────│───────────│───────►│
      │    │    └─────────────────┘           │        │
      │    │                                  │        │
      │────│── Dealer Hidden Card ────────────│───────►│
      │────│── Dealer Draws (until >=17) ─────│───────►│
      │────│── Final Result ──────────────────│───────►│
      │    │                                  │        │
      │    └──────────────────────────────────┘        │
      │                                                │
      │◄───────────── TCP Close ───────────────────────│
      │                                                │
```

---

## 📁 File Structure

```
BlackJack/
├── main.py              # Main entry point - game menu
├── server.py            # Dealer server (UDP broadcast + TCP game)
├── client.py            # Player client (UDP listen + TCP game)
├── protocol.py          # Packet encoding/decoding
├── game_logic.py        # Blackjack rules & odds calculator
├── config.py            # Constants & configuration
├── utils.py             # Display & logging utilities
├── leaderboard_server.py    # HTTP leaderboard API
├── leaderboard_client.py    # Leaderboard client library
└── README.md            # This file
```

---

## ⚙️ Configuration

Edit `config.py` to change:

```python
SERVER_NAME = "YourTeamName"    # Displayed when broadcasting
CLIENT_NAME = "YourTeamName"    # Sent when connecting
UDP_BROADCAST_PORT = 13122      # Fixed by protocol
```

---

## 🎲 Features

### Odds Calculator
When playing with statistics, see real-time probabilities:
```
╔═══════════════════════════════════════════════════════════════╗
║  Your hand: 10♥ 5♦  (Total: 15)                              ║
║  Dealer shows: 7♠ [?]                                         ║
╠═══════════════════════════════════════════════════════════════╣
║  📊 ODDS CALCULATOR                                           ║
║  If you HIT:   Win: 38% | Lose: 54% | Tie: 8%                ║
║  If you STAND: Win: 26% | Lose: 66% | Tie: 8%                ║
║  💡 Recommendation: HIT (+12% win chance)                     ║
╚═══════════════════════════════════════════════════════════════╝
```

### Colored Cards
- ♥ Hearts → Red
- ♦ Diamonds → Red
- ♠ Spades → White
- ♣ Clubs → White

---

## 🔧 Technical Details

### Threading Model
- **Server**: Main thread for TCP, daemon thread for UDP broadcasts
- **Client**: Single-threaded, blocking I/O
- **Leaderboard**: Single-threaded HTTP server with SQLite

### Network Protocols
- **UDP**: Connectionless broadcast for server discovery
- **TCP**: Reliable stream for gameplay messages
- **HTTP**: REST API for leaderboard (optional component)

### Error Handling
| Scenario | Handling |
|----------|----------|
| Invalid magic cookie | Reject packet |
| Client disconnect | Clean up, continue |
| Timeout | Return to listening |
| Network error | Log and retry |

---

## 🧪 Testing

### Local Testing (Same Machine)
1. Terminal 1: `python main.py` → Choose Dealer
2. Terminal 2: `python main.py` → Choose Player

### Network Testing
1. Run dealer on one machine
2. Run player on another machine (same network)
3. Player auto-discovers dealer via UDP broadcast

---

## 📝 License

Created for Intro to Computer Networks 2025 Hackathon.
