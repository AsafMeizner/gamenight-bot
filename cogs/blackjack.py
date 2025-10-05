import discord
from discord.ext import commands
from discord import app_commands
from utils.common import DATA_DIR, make_embed

class Blackjack(discord.ui.View):
    def __init__(self, inter: discord.Interaction):
        super().__init__(timeout=300.0)
        self.inter = inter
        self.player = inter.user
        self.dealer = "Dealer"
        self.deck = self.create_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.game_over = False

        # Initial deal
        self.player_hand.append(self.draw_card())
        self.dealer_hand.append(self.draw_card())
        self.player_hand.append(self.draw_card())
        self.dealer_hand.append(self.draw_card())

    async def start(self):
        initial_state = self.state_text(hide_dealer_card=True)
        em = make_embed("🎰 Blackjack Game Started!", initial_state, discord.Color.gold())
        em.set_footer(text="Good luck! 🍀")
        await self.inter.response.send_message(embed=em, view=self)

    @discord.ui.button(label="🃏 Hit", style=discord.ButtonStyle.green)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.hit(interaction)
    
    @discord.ui.button(label="✋ Stand", style=discord.ButtonStyle.red)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.stand(interaction)

    def get_card_emoji(self, card):
        """Convert card to emoji representation"""
        rank, suit = card
        
        # Suit emojis
        suit_emojis = {
            'Hearts': '♥️',
            'Diamonds': '♦️',
            'Clubs': '♣️',
            'Spades': '♠️'
        }
        
        # Rank display
        rank_display = {
            'J': 'J',
            'Q': 'Q', 
            'K': 'K',
            'A': 'A'
        }
        
        display_rank = rank_display.get(rank, rank)
        suit_emoji = suit_emojis.get(suit, suit)
        
        return f"`{display_rank}{suit_emoji}`"
    
    def state_text(self, hide_dealer_card=False):
        player_cards = " ".join([self.get_card_emoji(card) for card in self.player_hand])
        player_value = self.hand_value(self.player_hand)
        
        if hide_dealer_card:
            visible_card = self.get_card_emoji(self.dealer_hand[0])
            dealer_cards = f"{visible_card} `🂠`"
            dealer_value = "?"
        else:
            dealer_cards = " ".join([self.get_card_emoji(card) for card in self.dealer_hand])
            dealer_value = self.hand_value(self.dealer_hand)
        
        # Add value indicators with emojis
        player_status = ""
        if player_value == 21:
            player_status = " 🎯"
        elif player_value > 21:
            player_status = " 💥"
        
        dealer_status = ""
        if not hide_dealer_card:
            if dealer_value == 21:
                dealer_status = " 🎯"
            elif dealer_value > 21:
                dealer_status = " 💥"
        
        return (f"🎰 **BLACKJACK** 🎰\n\n"
                f"👤 **Your Hand** (Value: **{player_value}**){player_status}\n"
                f"{player_cards}\n\n"
                f"🤖 **Dealer's Hand** (Value: **{dealer_value}**){dealer_status}\n"
                f"{dealer_cards}")
    
    
    def create_deck(self):
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [(f"{rank}", f"{suit}") for suit in suits for rank in ranks]
        import random
        random.shuffle(deck)
        return deck
    
    def draw_card(self):
        return self.deck.pop()
    
    def hand_value(self, hand):
        value = 0
        aces = 0
        for card in hand:
            rank = card[0]
            if rank in ['J', 'Q', 'K']:
                value += 10
            elif rank == 'A':
                aces += 1
                value += 11
            else:
                value += int(rank)
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value
    
    async def stand(self, interaction: discord.Interaction):
        while self.hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.draw_card())
        self.game_over = True
        await self.end_game(interaction)

    async def hit(self, interaction: discord.Interaction):
        if self.game_over:
            await interaction.response.send_message("🚫 Game is already over.", ephemeral=True)
            return
        self.player_hand.append(self.draw_card())
        if self.hand_value(self.player_hand) > 21:
            self.game_over = True
            await self.end_game(interaction)
        else:
            state = self.state_text(hide_dealer_card=True)
            em = make_embed("🎰 Blackjack - Your Turn", state, discord.Color.gold())
            em.set_footer(text="Choose your next move! 🤔")
            await interaction.response.edit_message(embed=em, view=self)
    
    async def end_game(self, interaction: discord.Interaction):
        player_value = self.hand_value(self.player_hand)
        dealer_value = self.hand_value(self.dealer_hand)
        
        if player_value > 21:
            result = "💥 You bust! Dealer wins."
            color = discord.Color.red()
            emoji = "😞"
        elif dealer_value > 21:
            result = "🎉 Dealer busts! You win!"
            color = discord.Color.green()
            emoji = "🎊"
        elif player_value > dealer_value:
            result = "🏆 You win!"
            color = discord.Color.green()
            emoji = "🎉"
        elif player_value < dealer_value:
            result = "😔 Dealer wins!"
            color = discord.Color.red()
            emoji = "💔"
        else:
            result = "🤝 It's a tie!"
            color = discord.Color.orange()
            emoji = "🤷‍♂️"

        state = self.state_text(hide_dealer_card=False)
        final_text = f"{state}\n\n**{result}**"
        em = make_embed(f"🎰 Game Over! {emoji}", final_text, color)
        em.set_footer(text="Thanks for playing! 🎲")
        await interaction.response.edit_message(embed=em, view=None)

class BlackjackCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @app_commands.command(name="blackjack", description="Play a game of Blackjack")
    async def blackjack(self, inter: discord.Interaction):
        game = Blackjack(inter)
        await game.start()

async def setup(bot: commands.Bot):
    await bot.add_cog(BlackjackCog(bot))