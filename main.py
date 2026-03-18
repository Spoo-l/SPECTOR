import asyncio
import json
import os
import random
from pathlib import Path

import discord
from discord.ext import commands, tasks

TOKEN = os.getenv("DISCORD_TOKEN")
CONFIG_FILE = Path("guild_config.json")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

CORRUPTED_ROLE_ID = 1483657249393213470
VC_PING_ROLE_ID = 1483651256433250537
DEAD_CHAT_ROLE_ID = 1483652493798801419
PINGS_OK_ROLE_ID = 1483654707175096400
NO_PINGS_ROLE_ID = 1483654795393896489

guild_config = {}
REACTION_ROLE_MESSAGES = []

FREQUENCY_CODES = [
    "4912-03-77", "8301-12-65", "1279-56-84", "6203-88-91", "5409-22-11",
    "3392-47-23", "1056-78-55", "7742-19-90", "9183-31-42", "4632-14-36",
    "2180-97-62", "5721-44-19", "8024-33-78", "6549-27-40", "3901-66-12",
    "1178-55-29", "9203-80-04", "3059-42-75", "4810-17-63", "7291-39-50",
    "6682-05-98", "1374-61-20", "8543-18-79", "3910-49-26", "5607-82-41",
    "2483-36-94", "7031-20-87", "4948-13-35", "8210-64-09", "1759-07-32"
]

GOODBYE_VARIANTS = [
    {"last_seen": "Signal terminated mid-transmission", "notes": "Encryption failed. Contents unrecoverable."},
    {"last_seen": "Emergency airlock access triggered", "notes": "We warned them not to open that door."},
    {"last_seen": "Final ping from quarantine zone", "notes": "Exposure protocol enacted too late."},
    {"last_seen": "Range book signed off", "notes": "Final qualification stamped. Weapon left clean."},
    {"last_seen": "Set off perimeter alarm, sector Bravo-2", "notes": "Guard detail responded, no breach located. Alarm reset."},
    {"last_seen": "Walking past the motor pool fence line", "notes": "Nobody volunteers for that route."},
    {"last_seen": "Corridor 13B — off-limits for a reason", "notes": "We really need to start locking doors."},
    {"last_seen": "Purging personal records", "notes": "Who would go looking?"},
    {"last_seen": "Exploding.", "notes": "Thanks for the mess."}
]

REACTION_ROLE_SECTIONS = [
    {
        "description": "Age Group",
        "roles": {
            "🔹": (1483605723186200748, "🔹 15–17"),
            "🔸": (1483605723186200749, "🔸 18+"),
        }
    },
    {
        "description": "Pronouns",
        "roles": {
            "🟦": (1483656499975946310, "🟦 He / Him"),
            "🟪": (1483656591784935515, "🟪 She / Her"),
            "⬜": (1483656706478182520, "⬜ They / Them"),
            "🔄": (1483656836921163796, "🔄 Any Pronouns"),
            "❓": (1483656989820190761, "❓ Ask"),
        }
    },
    {
        "description": "Pings",
        "roles": {
            "📢": (1483605723186200747, "📢 Announcements"),
            "🎉": (1483651160249204889, "🎉 Events"),
            "🎙️": (1483651256433250537, "🎙️ VC Pings"),
            "💀": (1483652493798801419, "💀 Dead Chat Ping"),
            "📡": (1483654707175096400, "📡 Pings okay"),
            "🔕": (1483654795393896489, "🔕 No Pings"),
        }
    }
]

def load_config():
    global guild_config

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                guild_config = json.load(f)
        except (json.JSONDecodeError, OSError):
            guild_config = {}
    else:
        guild_config = {}


def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(guild_config, f, indent=2)
    except OSError:
        print("Failed to save config file.")


def get_guild_settings(guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in guild_config:
        guild_config[gid] = {
            "welcome_channel_id": None,
            "goodbye_channel_id": None,
            "static_channel_id": None
        }
    return guild_config[gid]

def format_blockquote_code(text: str) -> str:
    lines = text.splitlines()
    formatted_lines = [f"> `{line}`" if line.strip() else ">" for line in lines]
    return "\n".join(formatted_lines)


def get_random_ping_ok_member(guild: discord.Guild):
    ping_ok_role = guild.get_role(PINGS_OK_ROLE_ID)
    no_ping_role = guild.get_role(NO_PINGS_ROLE_ID)

    if ping_ok_role is None:
        return None

    eligible = []
    for member in guild.members:
        if member.bot:
            continue
        if ping_ok_role not in member.roles:
            continue
        if no_ping_role is not None and no_ping_role in member.roles:
            continue
        eligible.append(member)

    if not eligible:
        return None

    return random.choice(eligible)


async def remove_corruption_later(member: discord.Member, delay: int = 900):
    await asyncio.sleep(delay)

    role = member.guild.get_role(CORRUPTED_ROLE_ID)
    if role and role in member.roles:
        try:
            await member.remove_roles(role, reason="Corruption expired")
        except discord.Forbidden:
            print("Couldn't remove corrupted role.")
        except discord.HTTPException as e:
            print(f"Error removing corrupted role: {e}")

def make_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="COMMAND DIRECTORY",
        description="How to use the bot:",
        color=discord.Color.dark_red()
    )

    embed.add_field(name="!help", value="Shows this command list.", inline=False)
    embed.add_field(name="!setwelcome #channel", value="Admin only. Sets where join messages are sent.", inline=False)
    embed.add_field(name="!setgoodbye #channel", value="Admin only. Sets where leave messages are sent.", inline=False)
    embed.add_field(name="!setstatic #channel", value="Admin only. Sets where static broadcasts are sent.", inline=False)
    embed.add_field(name="!setup_reactions", value="Admin only. Posts the reaction-role messages.", inline=False)
    embed.add_field(name="!pingvc", value="Pings the VC role.", inline=False)
    embed.add_field(name="!pingdead", value="Pings the dead chat role.", inline=False)
    embed.add_field(name="!testjoin", value="Tests the saved welcome channel.", inline=False)
    embed.add_field(name="!testleave", value="Tests the saved goodbye channel.", inline=False)
    embed.add_field(name="!teststatic", value="Tests the saved static channel.", inline=False)
    embed.add_field(
        name="Automatic stuff",
        value=(
            "Random signal callouts may target users with the `Pings okay` role.\n"
            "Users with `No Pings` are skipped.\n"
            "Corruption is applied randomly and wears off after a while."
        ),
        inline=False
    )

    return embed

async def send_welcome_message(member: discord.Member, channel: discord.TextChannel):
    freq_code = random.choice(FREQUENCY_CODES)

    embed = discord.Embed(
        title="REPORT:",
        description=(
            "**STATUS:** New Signal Detected\n"
            "**LOADING. . .**\n\n"
            f"**IDENTIFIED CONTACT:**\n{member.mention}\n\n"
            f"**FREQUENCY CODE:** {freq_code}\n"
            "**NOTES:** Read the handbook, friend"
        ),
        color=discord.Color.red()
    )
    await channel.send(embed=embed)


async def send_goodbye_message_from_name(display_name: str, channel: discord.TextChannel):
    variant = random.choice(GOODBYE_VARIANTS)

    embed = discord.Embed(
        title=f"DEPARTURE: {display_name}",
        description=(
            "**STATUS:** Lost Signal\n"
            f"**LAST SEEN:** {variant['last_seen']}\n\n"
            f"**NOTES:** {variant['notes']}"
        ),
        color=discord.Color.dark_gray()
    )
    await channel.send(embed=embed)


async def send_goodbye_message(member: discord.Member, channel: discord.TextChannel):
    await send_goodbye_message_from_name(member.display_name or member.name, channel)


async def send_static_payload(channel: discord.TextChannel):
    static_message = "STATIC . . ."

    rare_messages = [
        "SIGNAL . . . NOISE",
        "IDLE. . .",
        "BROADCAST LINK LOST. ATTEMPTING TO RECOVER. . .",
        "UNIDENTIFIED FREQUENCY DETECTED",
        "ERROR 504 — SIGNAL TIMEOUT. REBOOTING. . .",
        "CARRIER WAVE ONLY",
    ]

    super_rare_intro_message = "FOREIGN SIGNAL FOUND"

    super_rare_morse_messages = [
        ".... / ..- / -. / --. .-. / -.-- -.-- -.--",
        "... --- ...",
        "... - ..- -.-. -.-",
        ".... . .-.. .--. / -- .",
        ".. / -.-. .- -. / .... . .- .-. / .. - / -... .-. . .- - .... .. -. --.",
        ".--. .-.. . .- ... .",
        ".-.. / --- / --- / -.- / ..- .--. .--. .--.",
    ]

    roll = random.randint(1, 250)

    if roll == 1:
        await channel.send(format_blockquote_code(super_rare_intro_message))
        await asyncio.sleep(random.uniform(1.0, 2.0))
        await channel.send(format_blockquote_code(random.choice(super_rare_morse_messages)))
    elif roll <= 15:
        await channel.send(format_blockquote_code(random.choice(rare_messages)))
    else:
        await channel.send(format_blockquote_code(static_message))

@bot.event
async def on_ready():
    load_config()
    print(f"Bot is online as {bot.user}")

    if not send_static_message.is_running():
        send_static_message.start()


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    if random.randint(1, 45) == 1:
        target = get_random_ping_ok_member(message.guild)

        if target is not None:
            responses = [
                f"> `UNSTABLE SIGNAL LOCKED ON: {target.mention}`",
                f"> `TRACE DETECTED: {target.mention}`",
                f"> `WATCHING TRANSMISSION SOURCE: {target.mention}`",
                f"> `SIGNAL QUALITY DEGRADED: {target.mention}`",
                f"> `SIGNAL DRIFT DETECTED: {target.mention}`",
                f"> `UNAUTHORIZED FREQUENCY FOUND: {target.mention}`",
            ]

            await message.channel.send(
                random.choice(responses),
                allowed_mentions=discord.AllowedMentions(
                    users=True,
                    roles=False,
                    everyone=False
                )
            )

    if random.randint(1, 75) == 1:
        role = message.guild.get_role(CORRUPTED_ROLE_ID)

        if role and role not in message.author.roles:
            try:
                await message.author.add_roles(role, reason="Random corruption event")
                await message.channel.send(
                    f"> `CORRUPTION DETECTED`\n> `USER MARKED: {message.author.mention}`",
                    allowed_mentions=discord.AllowedMentions(
                        users=True,
                        roles=False,
                        everyone=False
                    )
                )
                bot.loop.create_task(remove_corruption_later(message.author, 900))
            except discord.Forbidden:
                print("Couldn't assign corrupted role.")
            except discord.HTTPException as e:
                print(f"Error assigning corrupted role: {e}")

    await bot.process_commands(message)


@bot.event
async def on_member_join(member: discord.Member):
    print(f"JOIN EVENT FIRED: {member} in {member.guild.name}")

    settings = get_guild_settings(member.guild.id)
    channel_id = settings.get("welcome_channel_id")

    if not channel_id:
        print("No welcome channel set.")
        return

    channel = member.guild.get_channel(channel_id)
    print(f"Welcome channel lookup: {channel}")

    if isinstance(channel, discord.TextChannel):
        await send_welcome_message(member, channel)


@bot.event
async def on_member_remove(member: discord.Member):
    print(f"LEAVE EVENT FIRED: {member} in {member.guild.name}")

    settings = get_guild_settings(member.guild.id)
    channel_id = settings.get("goodbye_channel_id")

    if not channel_id:
        print("No goodbye channel set.")
        return

    channel = member.guild.get_channel(channel_id)
    print(f"Goodbye channel lookup: {channel}")

    if isinstance(channel, discord.TextChannel):
        await send_goodbye_message(member, channel)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    if payload.message_id not in REACTION_ROLE_MESSAGES:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None:
        return

    emoji_str = str(payload.emoji)

    for section in REACTION_ROLE_SECTIONS:
        role_data = section["roles"].get(emoji_str)
        if role_data:
            role_id = role_data[0]
            role = guild.get_role(role_id)

            if role is not None:
                try:
                    await member.add_roles(role, reason="Reaction role added")
                except discord.Forbidden:
                    print(f"Missing permission to add role {role.name} in {guild.name}")
                except discord.HTTPException as e:
                    print(f"Failed to add role: {e}")
            break


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.message_id not in REACTION_ROLE_MESSAGES:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None:
        return

    emoji_str = str(payload.emoji)

    for section in REACTION_ROLE_SECTIONS:
        role_data = section["roles"].get(emoji_str)
        if role_data:
            role_id = role_data[0]
            role = guild.get_role(role_id)

            if role is not None:
                try:
                    await member.remove_roles(role, reason="Reaction role removed")
                except discord.Forbidden:
                    print(f"Missing permission to remove role {role.name} in {guild.name}")
                except discord.HTTPException as e:
                    print(f"Failed to remove role: {e}")
            break

@tasks.loop(minutes=60)
async def send_static_message():
    for guild in bot.guilds:
        settings = get_guild_settings(guild.id)
        channel_id = settings.get("static_channel_id")

        if not channel_id:
            continue

        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            try:
                await send_static_payload(channel)
            except discord.Forbidden:
                print(f"No permission to send static message in {guild.name}")
            except discord.HTTPException as e:
                print(f"Failed static send in {guild.name}: {e}")


@send_static_message.before_loop
async def before_static_loop():
    await bot.wait_until_ready()

@bot.command()
async def help(ctx):
    await ctx.send(embed=make_help_embed())


@bot.command()
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, channel: discord.TextChannel):
    settings = get_guild_settings(ctx.guild.id)
    settings["welcome_channel_id"] = channel.id
    save_config()
    await ctx.send(f"Welcome channel set to {channel.mention}")


@bot.command()
@commands.has_permissions(administrator=True)
async def setgoodbye(ctx, channel: discord.TextChannel):
    settings = get_guild_settings(ctx.guild.id)
    settings["goodbye_channel_id"] = channel.id
    save_config()
    await ctx.send(f"Goodbye channel set to {channel.mention}")


@bot.command()
@commands.has_permissions(administrator=True)
async def setstatic(ctx, channel: discord.TextChannel):
    settings = get_guild_settings(ctx.guild.id)
    settings["static_channel_id"] = channel.id
    save_config()
    await ctx.send(f"Static channel set to {channel.mention}")


@bot.command()
@commands.has_permissions(administrator=True)
async def setup_reactions(ctx):
    global REACTION_ROLE_MESSAGES
    REACTION_ROLE_MESSAGES.clear()

    if not REACTION_ROLE_SECTIONS or all(not s["roles"] for s in REACTION_ROLE_SECTIONS):
        await ctx.send("Reaction roles are not configured yet.")
        return

    for section in REACTION_ROLE_SECTIONS:
        embed = discord.Embed(
            title="SELECT YOUR ROLES",
            description=section["description"],
            color=discord.Color.blue()
        )

        for role_data in section["roles"].values():
            embed.add_field(name=role_data[1], value="\u200b", inline=False)

        msg = await ctx.send(embed=embed)
        REACTION_ROLE_MESSAGES.append(msg.id)

        for emoji in section["roles"]:
            try:
                await msg.add_reaction(emoji)
            except discord.HTTPException:
                print(f"Failed to add reaction {emoji} to message {msg.id}")


@bot.command()
async def pingvc(ctx):
    role = ctx.guild.get_role(VC_PING_ROLE_ID)
    if not role:
        return await ctx.send("VC ping role not found.")

    await ctx.send(
        f"> `SIGNAL BROADCAST INITIATED`\n{role.mention}",
        allowed_mentions=discord.AllowedMentions(
            users=False,
            roles=True,
            everyone=False
        )
    )


@bot.command()
async def pingdead(ctx):
    role = ctx.guild.get_role(DEAD_CHAT_ROLE_ID)
    if not role:
        return await ctx.send("Dead chat ping role not found.")

    await ctx.send(
        f"> `DORMANT CHANNEL DETECTED`\n{role.mention}",
        allowed_mentions=discord.AllowedMentions(
            users=False,
            roles=True,
            everyone=False
        )
    )


@bot.command()
async def testjoin(ctx):
    settings = get_guild_settings(ctx.guild.id)
    channel_id = settings.get("welcome_channel_id")

    if not channel_id:
        return await ctx.send("No welcome channel is set.")

    channel = ctx.guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return await ctx.send("Saved welcome channel could not be found.")

    await send_welcome_message(ctx.author, channel)
    await ctx.send(f"Sent test welcome message to {channel.mention}")


@bot.command()
async def testleave(ctx):
    settings = get_guild_settings(ctx.guild.id)
    channel_id = settings.get("goodbye_channel_id")

    if not channel_id:
        return await ctx.send("No goodbye channel is set.")

    channel = ctx.guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return await ctx.send("Saved goodbye channel could not be found.")

    await send_goodbye_message(ctx.author, channel)
    await ctx.send(f"Sent test goodbye message to {channel.mention}")


@bot.command()
async def teststatic(ctx):
    settings = get_guild_settings(ctx.guild.id)
    channel_id = settings.get("static_channel_id")

    if not channel_id:
        return await ctx.send("No static channel is set.")

    channel = ctx.guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return await ctx.send("Saved static channel could not be found.")

    await send_static_payload(channel)
    await ctx.send(f"Sent test static message to {channel.mention}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don’t have permission to use that command.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("That channel or argument looks wrong.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You’re missing part of the command.")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        print(f"Unhandled command error: {error}")
        await ctx.send("Something broke. Check the console.")


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing.")

bot.run(TOKEN)
