import discord
from discord.ext import commands
import asyncio
import requests
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Initialize Flask app for Render Web Service
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nexon Status</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                background-color: #000000;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #00ff41;
                overflow: hidden;
            }
            .container {
                text-align: center;
                position: relative;
            }
            .icon-wrapper {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                margin-bottom: 20px;
            }
            .icon {
                width: 80px;
                height: 80px;
                border-radius: 50%;
                box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
                animation: pulse 2s infinite;
            }
            .online-dot {
                width: 12px;
                height: 12px;
                background-color: #00ff41;
                border-radius: 50%;
                box-shadow: 0 0 10px #00ff41, 0 0 20px #00ff41;
                animation: glow 1.5s infinite alternate;
            }
            .status-text {
                font-size: 2.5rem;
                font-weight: bold;
                text-shadow: 0 0 10px #00ff41, 0 0 20px #00ff41;
                animation: glitch 2s infinite linear, fadeIn 1s ease-in;
            }
            @keyframes pulse {
                0% {
                    box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
                }
                50% {
                    box-shadow: 0 0 30px rgba(0, 255, 65, 0.8);
                }
                100% {
                    box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
                }
            }
            @keyframes glow {
                0% {
                    box-shadow: 0 0 10px #00ff41;
                }
                100% {
                    box-shadow: 0 0 20px #00ff41;
                }
            }
            @keyframes glitch {
                0% {
                    transform: translate(0);
                }
                20% {
                    transform: translate(-2px, 2px);
                    text-shadow: 2px 0 #ff00ff, -2px 0 #00e6e6;
                }
                40% {
                    transform: translate(2px, -2px);
                    text-shadow: -2px 0 #ff00ff, 2px 0 #00e6e6;
                }
                60% {
                    transform: translate(-2px, 2px);
                    text-shadow: 2px 0 #ff00ff, -2px 0 #00e6e6;
                }
                80% {
                    transform: translate(2px, -2px);
                    text-shadow: -2px 0 #ff00ff, 2px 0 #00e6e6;
                }
                100% {
                    transform: translate(0);
                }
            }
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            /* Responsive Design */
            @media (max-width: 768px) {
                .status-text {
                    font-size: 2rem;
                }
                .icon {
                    width: 60px;
                    height: 60px;
                }
                .online-dot {
                    width: 10px;
                    height: 10px;
                }
            }
            @media (max-width: 480px) {
                .status-text {
                    font-size: 1.5rem;
                }
                .icon {
                    width: 50px;
                    height: 50px;
                }
                .online-dot {
                    width: 8px;
                    height: 8px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon-wrapper">
                <img src="nexon.webp" alt="Nexon Icon" class="icon">
                <div class="online-dot"></div>
            </div>
            <h1 class="status-text">Nexon is live</h1>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.getenv('PORT', 8080))  # Use Render's PORT or fallback to 8080
    app.run(host='0.0.0.0', port=port)

# Load environment variables
load_dotenv()

# Set up Discord bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Environment variables
API_URL = os.getenv('API_URL', 'http://localhost:5000/api/upload')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Validate Discord token
if not DISCORD_TOKEN:
    print("Error: DISCORD_TOKEN environment variable is not set!")
    exit(1)

print(f"Starting bot with token length: {len(DISCORD_TOKEN)} characters")
print("Attempting to connect to Discord...")

# Category configurations with channel mappings
CATEGORIES = {
    '🎉': 'Entertainment',
    '📚': 'Education',
    '🌐': 'Website',
    '🛠️': 'Hack',
    '❓': 'Others'
}

# Channel mappings - replace with actual channel IDs
CATEGORY_CHANNELS = {
    'Entertainment': 1413856614510755880,  # Replace with actual channel ID
    'Education': 1413881799322636319,      # Replace with actual channel ID
    'Website': 1413881852451885266,        # Replace with actual channel ID
    'Hack': 1413881887428055193,           # Replace with actual channel ID
    'Others': 1413881920248615143          # Replace with actual channel ID
}

@bot.event
async def on_ready():
    print(f'Bot is ready: {bot.user}')
    print(f"Use '!post' to start creating a new post")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Handle post creation replies
    if await handle_post_creation_reply(message):
        return

    await bot.process_commands(message)

# Global storage for ongoing post creation sessions
post_sessions = {}

@bot.command(name='post')
async def new_post(ctx):
    """Start creating a new post"""
    user_id = ctx.author.id

    # Check if user already has an active session
    if user_id in post_sessions:
        await ctx.send(
            "❌ You already have an active post creation session. Complete it first or wait for it to timeout."
        )
        return

    # Initialize session
    post_sessions[user_id] = {
        'step': 'topic',
        'channel': ctx.channel,
        'author': ctx.author,
        'data': {}
    }

    # Ask for topic
    await ctx.send(
        f"**📝 Creating new post - Step 1/3**\n{ctx.author.mention}, what's the topic of your post?"
    )

async def handle_post_creation_reply(message):
    """Handle replies during post creation"""
    user_id = message.author.id

    if user_id not in post_sessions:
        return False

    session = post_sessions[user_id]

    if message.content.lower() == 'cancel':
        del post_sessions[user_id]
        await message.channel.send(
            f"❌ {message.author.mention} Post creation cancelled.")
        return True

    if session['step'] == 'topic':
        session['data']['topic'] = message.content
        session['step'] = 'description'
        await message.channel.send(
            f"**📝 Creating new post - Step 2/3**\n{message.author.mention}, provide a description for your post:"
        )
        return True

    elif session['step'] == 'description':
        session['data']['description'] = message.content
        session['step'] = 'link'
        await message.channel.send(
            f"**📝 Creating new post - Step 3/3**\n{message.author.mention}, add a link (or type 'skip' if no link):"
        )
        return True

    elif session['step'] == 'link':
        if message.content.lower() == 'skip':
            session['data']['link'] = ''
        else:
            session['data']['link'] = message.content

        # Show category selection
        session['step'] = 'category'
        category_text = f"**📝 Creating new post - Final Step**\n{message.author.mention}, choose a category:\n"
        category_text += "🎉 Entertainment\n📚 Education\n🌐 Website\n🛠️ Hack\n❓ Others\n\n"
        category_text += "React with the appropriate emoji to select category:"

        category_msg = await message.channel.send(category_text)
        session['category_msg'] = category_msg

        # Add reaction options
        for emoji in CATEGORIES.keys():
            try:
                await category_msg.add_reaction(emoji)
            except:
                pass
        return True

    return False

@bot.event
async def on_reaction_add(reaction, user):
    """Handle category selection via reactions"""
    if user.bot:
        return

    user_id = user.id
    if user_id not in post_sessions:
        return

    session = post_sessions[user_id]
    if session['step'] != 'category':
        return

    if 'category_msg' not in session or reaction.message.id != session['category_msg'].id:
        return

    if str(reaction.emoji) not in CATEGORIES:
        return

    # Get category and complete post
    tag = CATEGORIES[str(reaction.emoji)]
    session['data']['tag'] = tag

    # Clear last 8 messages from the channel
    try:
        async for message in session['channel'].history(limit=8):
            try:
                await message.delete()
            except:
                pass
    except Exception as e:
        print(f"Error clearing messages: {e}")

    # Create and post final message
    await create_and_post_final(session['channel'], session['author'],
                                session['data']['topic'],
                                session['data']['description'],
                                session['data']['link'], tag)

    # Clean up session
    del post_sessions[user_id]

async def create_and_post_final(channel, author, topic, description, link, tag):
    """Create final plain text post and send to both Discord and website"""

    # Create plain text format
    message_content = f"# {topic}\n> {description}"

    if link and link.strip():
        message_content += f"\n{link}"

    # Post to current channel
    posted_msg = await channel.send(message_content)

    # Try to post to category-specific channel if configured
    target_channel_id = CATEGORY_CHANNELS.get(tag)
    if target_channel_id:
        try:
            target_channel = bot.get_channel(target_channel_id)
            if target_channel and target_channel != channel:
                await target_channel.send(message_content)
        except Exception as e:
            print(f"Error posting to category channel: {e}")

    # Send to website API
    payload = {
        'topic': topic,
        'description': description,
        'link': link if link and link.strip() else '',
        'tag': tag,
        'source': 'discord'
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Post uploaded to website: [{tag}] {topic}")
        else:
            print(
                f"❌ Website upload failed: {response.status_code} - {response.text}"
            )
    except Exception as e:
        print(f"❌ Error uploading to website: {e}")

@bot.command(name='setchannel')
@commands.has_permissions(administrator=True)
async def set_channel(ctx, category: str, channel_id: int = None):
    """Set the target channel for a specific category"""
    global CATEGORY_CHANNELS

    if category not in ['Entertainment', 'Education', 'Website', 'Hack', 'Others']:
        await ctx.send(
            "❌ Invalid category. Use: Entertainment, Education, Website, Hack, Others"
        )
        return

    if channel_id is None:
        CATEGORY_CHANNELS[category] = None
        await ctx.send(f"✅ Removed channel mapping for {category}")
    else:
        channel = bot.get_channel(channel_id)
        if channel:
            CATEGORY_CHANNELS[category] = channel_id
            await ctx.send(f"✅ Set {category} posts to go to {channel.mention}")
        else:
            await ctx.send("❌ Channel not found!")

@bot.command(name='channels')
async def show_channels(ctx):
    """Show current channel mappings"""
    embed = discord.Embed(title="📋 Channel Mappings", color=0x00ff41)

    for category, channel_id in CATEGORY_CHANNELS.items():
        if channel_id:
            channel = bot.get_channel(channel_id)
            value = channel.mention if channel else f"Invalid ID: {channel_id}"
        else:
            value = "Not set (posts to current channel)"
        embed.add_field(name=category, value=value, inline=False)

    await ctx.send(embed=embed)

# Start Flask and bot
Thread(target=run_flask).start()
bot.run(DISCORD_TOKEN)
