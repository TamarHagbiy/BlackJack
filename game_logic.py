"""
Game logic for the Blackjack network application.
Contains card/deck management, value calculation, and odds calculator.
"""

import random
from typing import List, Tuple, Dict
from config import SUIT_SYMBOLS, RANK_NAMES


# =============================================================================
# CARD CLASS
# =============================================================================

class Card:
    """Represents a playing card with rank and suit."""
    
    def __init__(self, rank: int, suit: int):
        """
        Create a new card.
        
        Args:
            rank: 1-13 (1=Ace, 11=Jack, 12=Queen, 13=King)
            suit: 0-3 (0=Heart, 1=Diamond, 2=Club, 3=Spade)
        """
        self.rank = rank
        self.suit = suit
    
    def value(self) -> int:
        """
        Get the blackjack value of this card.
        
        Returns:
            int: Card value (Ace=11, Face cards=10, others=face value)
        """
        if self.rank == 1:  # Ace
            return 11
        elif self.rank >= 11:  # Face cards (J, Q, K)
            return 10
        else:
            return self.rank
    
    def __str__(self) -> str:
        """Pretty print the card (e.g., 'A♠', 'K♥')."""
        return f"{RANK_NAMES[self.rank]}{SUIT_SYMBOLS[self.suit]}"
    
    def __repr__(self) -> str:
        return self.__str__()


# =============================================================================
# DECK CLASS
# =============================================================================

class Deck:
    """A standard 52-card deck with shuffle and deal methods."""
    
    def __init__(self):
        """Create a new shuffled deck."""
        self.reset()
    
    def reset(self):
        """Reset and shuffle the deck."""
        self.cards = []
        for suit in range(4):
            for rank in range(1, 14):
                self.cards.append(Card(rank, suit))
        random.shuffle(self.cards)
    
    def deal(self) -> Card:
        """
        Deal one card from the deck.
        
        Returns:
            Card: The dealt card
            
        Raises:
            IndexError: If deck is empty
        """
        if not self.cards:
            self.reset()
        return self.cards.pop()
    
    def remaining(self) -> int:
        """Get the number of remaining cards in the deck."""
        return len(self.cards)


# =============================================================================
# HAND VALUE CALCULATION
# =============================================================================

def calculate_hand_value(cards: List[Card]) -> int:
    """
    Calculate the total value of a hand.
    Note: Aces are always 11 in this simplified version.
    
    Args:
        cards: List of Card objects
        
    Returns:
        int: Total hand value
    """
    return sum(card.value() for card in cards)


def card_value(rank: int) -> int:
    """
    Convert a card rank to its blackjack point value.
    
    Args:
        rank: Card rank (1-13)
        
    Returns:
        int: Point value (Ace=11, Face=10, others=rank)
    """
    if rank == 1:
        return 11
    elif rank >= 11:
        return 10
    else:
        return rank


def format_card(rank: int, suit: int) -> str:
    """
    Format a card for display.
    
    Args:
        rank: Card rank (1-13)
        suit: Card suit (0-3)
        
    Returns:
        str: Formatted card string (e.g., 'A♠', 'K♥')
    """
    return f"{RANK_NAMES[rank]}{SUIT_SYMBOLS[suit]}"


def format_hand(cards: List[Card]) -> str:
    """
    Format a hand of cards for display.
    
    Args:
        cards: List of Card objects
        
    Returns:
        str: Formatted hand string (e.g., '10♥ 5♦')
    """
    return ' '.join(str(card) for card in cards)


# =============================================================================
# ODDS CALCULATOR
# =============================================================================

def get_remaining_deck_composition(known_cards: List[Tuple[int, int]]) -> Dict[int, int]:
    """
    Calculate remaining cards in deck by value.
    
    Args:
        known_cards: List of (rank, suit) tuples for known cards
        
    Returns:
        Dict mapping card value to count remaining
    """
    # Start with full deck composition by value
    # Values 2-9: 4 each, Value 10: 16 (10, J, Q, K), Value 11 (Ace): 4
    remaining = {
        2: 4, 3: 4, 4: 4, 5: 4, 6: 4, 7: 4, 8: 4, 9: 4,
        10: 16,  # 10, J, Q, K
        11: 4    # Aces
    }
    
    # Remove known cards
    for rank, suit in known_cards:
        value = card_value(rank)
        if value in remaining and remaining[value] > 0:
            remaining[value] -= 1
    
    return remaining


def simulate_dealer_outcomes(dealer_visible_value: int, remaining_deck: Dict[int, int]) -> Tuple[float, float, float]:
    """
    Simulate all possible dealer outcomes.
    
    Args:
        dealer_visible_value: Value of dealer's visible card
        remaining_deck: Dict of remaining card values
        
    Returns:
        Tuple of (bust_probability, distribution of final values)
    """
    # This is a simplified simulation using probabilities
    # We calculate the probability distribution of dealer's final hand
    
    total_remaining = sum(remaining_deck.values())
    if total_remaining == 0:
        return {}
    
    # Probability distribution of dealer's final hand value
    outcomes = {}
    
    # Dealer has one visible card, we need to account for hidden card + draws
    # Simplified: Calculate average outcomes
    
    # For each possible hidden card value
    for hidden_value, hidden_count in remaining_deck.items():
        if hidden_count <= 0:
            continue
            
        hidden_prob = hidden_count / total_remaining
        dealer_total = dealer_visible_value + hidden_value
        
        # Simulate dealer drawing until >= 17
        # This is recursive but we'll simplify with averages
        # Create deck with hidden card removed
        deck_after_hidden = remaining_deck.copy()
        deck_after_hidden[hidden_value] -= 1
        final_values = simulate_dealer_draw(dealer_total, deck_after_hidden)
        
        for value, prob in final_values.items():
            if value not in outcomes:
                outcomes[value] = 0
            outcomes[value] += hidden_prob * prob
    
    return outcomes


def simulate_dealer_draw(current_total: int, remaining_deck: Dict[int, int]) -> Dict[int, float]:
    """
    Recursively simulate dealer drawing cards.
    
    Args:
        current_total: Dealer's current hand total
        remaining_deck: Dict of remaining card values (already adjusted for known cards)
        
    Returns:
        Dict mapping final hand value (or 'bust') to probability
    """
    # Dealer stands on 17+
    if current_total >= 17:
        if current_total > 21:
            return {'bust': 1.0}
        return {current_total: 1.0}
    
    total_remaining = sum(remaining_deck.values())
    if total_remaining == 0:
        return {current_total: 1.0}
    
    outcomes = {}
    
    for draw_value, draw_count in remaining_deck.items():
        if draw_count <= 0:
            continue
            
        draw_prob = draw_count / total_remaining
        new_total = current_total + draw_value
        
        # Create a new deck with this card removed for recursive simulation
        next_deck = remaining_deck.copy()
        next_deck[draw_value] -= 1
        
        # Recursively simulate
        sub_outcomes = simulate_dealer_draw(new_total, next_deck)
        
        for value, prob in sub_outcomes.items():
            if value not in outcomes:
                outcomes[value] = 0
            outcomes[value] += draw_prob * prob
    
    return outcomes


def calculate_odds_if_stand(player_total: int, dealer_visible_value: int, 
                            known_cards: List[Tuple[int, int]]) -> Tuple[float, float, float]:
    """
    Calculate win/lose/tie probabilities if player stands.
    
    Args:
        player_total: Player's current hand total
        dealer_visible_value: Value of dealer's visible card
        known_cards: List of (rank, suit) tuples for all known cards
        
    Returns:
        Tuple of (win_prob, lose_prob, tie_prob) as percentages (0-100)
    """
    remaining_deck = get_remaining_deck_composition(known_cards)
    dealer_outcomes = simulate_dealer_outcomes(dealer_visible_value, remaining_deck)
    
    win_prob = 0.0
    lose_prob = 0.0
    tie_prob = 0.0
    
    for outcome, prob in dealer_outcomes.items():
        if outcome == 'bust':
            win_prob += prob
        elif outcome > player_total:
            lose_prob += prob
        elif outcome < player_total:
            win_prob += prob
        else:
            tie_prob += prob
    
    # Normalize and convert to percentages
    total = win_prob + lose_prob + tie_prob
    if total > 0:
        win_prob = (win_prob / total) * 100
        lose_prob = (lose_prob / total) * 100
        tie_prob = (tie_prob / total) * 100
    
    return (round(win_prob, 1), round(lose_prob, 1), round(tie_prob, 1))


def calculate_odds_if_hit(player_total: int, dealer_visible_value: int,
                          known_cards: List[Tuple[int, int]]) -> Tuple[float, float, float]:
    """
    Calculate win/lose/tie probabilities if player hits.
    
    Args:
        player_total: Player's current hand total
        dealer_visible_value: Value of dealer's visible card
        known_cards: List of (rank, suit) tuples for all known cards
        
    Returns:
        Tuple of (win_prob, lose_prob, tie_prob) as percentages (0-100)
    """
    remaining_deck = get_remaining_deck_composition(known_cards)
    total_remaining = sum(remaining_deck.values())
    
    if total_remaining == 0:
        return (0.0, 100.0, 0.0)
    
    win_prob = 0.0
    lose_prob = 0.0
    tie_prob = 0.0
    
    # For each possible card we could draw
    for draw_value, draw_count in remaining_deck.items():
        if draw_count <= 0:
            continue
            
        draw_prob = draw_count / total_remaining
        new_total = player_total + draw_value
        
        if new_total > 21:
            # Bust - we lose
            lose_prob += draw_prob
        else:
            # We don't bust - calculate odds if we stand with new total
            # Add the drawn card to known cards (use rank that matches value)
            new_known = known_cards.copy()
            if draw_value == 11:
                new_known.append((1, 0))  # Ace
            elif draw_value == 10:
                new_known.append((10, 0))  # Use 10 (could be J/Q/K but value is same)
            else:
                new_known.append((draw_value, 0))  # 2-9 have rank == value
            
            stand_odds = calculate_odds_if_stand(new_total, dealer_visible_value, new_known)
            
            win_prob += draw_prob * (stand_odds[0] / 100)
            lose_prob += draw_prob * (stand_odds[1] / 100)
            tie_prob += draw_prob * (stand_odds[2] / 100)
    
    # Convert to percentages
    win_prob *= 100
    lose_prob *= 100
    tie_prob *= 100
    
    return (round(win_prob, 1), round(lose_prob, 1), round(tie_prob, 1))


def get_recommendation(player_total: int, dealer_visible_value: int,
                       known_cards: List[Tuple[int, int]]) -> Tuple[str, float, float]:
    """
    Get the recommended action (Hit or Stand) with odds.
    
    Args:
        player_total: Player's current hand total
        dealer_visible_value: Value of dealer's visible card
        known_cards: List of (rank, suit) tuples for all known cards
        
    Returns:
        Tuple of (recommendation, hit_win_prob, stand_win_prob)
    """
    hit_odds = calculate_odds_if_hit(player_total, dealer_visible_value, known_cards)
    stand_odds = calculate_odds_if_stand(player_total, dealer_visible_value, known_cards)
    
    hit_win = hit_odds[0]
    stand_win = stand_odds[0]
    
    if hit_win > stand_win:
        return ("Hit", hit_win, stand_win)
    else:
        return ("Stand", hit_win, stand_win)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test the deck and cards
    deck = Deck()
    print("Testing Deck:")
    print(f"Deck has {deck.remaining()} cards")
    
    hand = [deck.deal() for _ in range(2)]
    print(f"Dealt hand: {format_hand(hand)}")
    print(f"Hand value: {calculate_hand_value(hand)}")
    
    # Test odds calculator
    print("\nTesting Odds Calculator:")
    player_cards = [(10, 0), (5, 1)]  # 10♥, 5♦
    dealer_visible = (7, 3)  # 7♠
    
    player_total = card_value(10) + card_value(5)
    dealer_value = card_value(7)
    known = player_cards + [dealer_visible]
    
    print(f"Player total: {player_total}")
    print(f"Dealer shows: {dealer_value}")
    
    hit_odds = calculate_odds_if_hit(player_total, dealer_value, known)
    stand_odds = calculate_odds_if_stand(player_total, dealer_value, known)
    
    print(f"\nIf you HIT:")
    print(f"  Win: {hit_odds[0]}% | Lose: {hit_odds[1]}% | Tie: {hit_odds[2]}%")
    
    print(f"\nIf you STAND:")
    print(f"  Win: {stand_odds[0]}% | Lose: {stand_odds[1]}% | Tie: {stand_odds[2]}%")
    
    rec, hit_win, stand_win = get_recommendation(player_total, dealer_value, known)
    win_diff = abs(hit_win - stand_win)
    print(f"\n💡 Recommendation: {rec} (+{win_diff:.1f}% better than {'Stand' if rec == 'Hit' else 'Hit'})")
