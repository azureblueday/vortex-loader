"""
Vortex Loader — Discord control bot
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("vortex")

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv()

DISCORD_TOKEN: str = os.environ["DISCORD_TOKEN"]
API_URL: str = os.environ["API_URL"].rstrip("/")
API_KEY: str = os.environ["API_KEY"]

# ---------------------------------------------------------------------------
# Persistent config
# ---------------------------------------------------------------------------
CONFIG_PATH = Path("config.json")

DEFAULT_CONFIG: dict = {
    "log_channel": None,
    "allowed_role": None,
    "script_channels": {},
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            data = json.load(f)
        for key, value in DEFAULT_CONFIG.items():
            data.setdefault(key, value)
        return data
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    with CONFIG_PATH.open("w") as f:
        json.dump(cfg, f, indent=2)


config: dict = load_config()

# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------------------------
# Helper: HTTP POST to Vercel
# ---------------------------------------------------------------------------
async def send_action(action: str, data: dict) -> dict:
    """POST to /api/control and return the parsed JSON response."""
    url = f"{API_URL}/api/control"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"action": action, "data": data}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.content_type == "application/json":
                    return await resp.json()
                # Non-JSON body (e.g. Vercel HTML error page)
                text = await resp.text()
                log.warning("Non-JSON response (%s): %s", resp.status, text[:200])
                return {
                    "success": False,
                    "message": f"API returned HTTP {resp.status} with non-JSON body.",
                }
    except aiohttp.ClientConnectorError:
        log.error("Could not connect to API at %s", url)
        return {"success": False, "message": "Could not connect to the API. Is the Vercel URL correct?"}
    except aiohttp.ServerTimeoutError:
        log.error("API request timed out")
        return {"success": False, "message": "API request timed out (>15 s)."}
    except Exception as exc:
        log.exception("Unexpected error during API call")
        return {"success": False, "message": f"Unexpected error: {exc}"}


# ---------------------------------------------------------------------------
# Helper: Execution log embed
# ---------------------------------------------------------------------------
async def log_execution(
    interaction: discord.Interaction,
    action: str,
    script: str,
    roblox_username: Optional[str],
    success: bool,
    message: str,
) -> None:
    log_channel_id = config.get("log_channel")
    if not log_channel_id:
        return

    channel = interaction.guild.get_channel(log_channel_id)
    if channel is None:
        log.warning("Log channel %s not found in guild.", log_channel_id)
        return

    colour = discord.Colour.green() if success else discord.Colour.red()
    result_text = "✅ Success" if success else "❌ Failed"

    embed = discord.Embed(
        title="Vortex Execution Log",
        colour=colour,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="User",
        value=f"{interaction.user.mention} (`{interaction.user.id}`)",
        inline=False,
    )
    embed.add_field(name="Channel", value=interaction.channel.mention, inline=True)
    embed.add_field(name="Script", value=f"`{script}`", inline=True)
    embed.add_field(name="Roblox User", value=roblox_username or "N/A", inline=True)
    embed.add_field(name="Action", value=action, inline=True)
    embed.add_field(name="Result", value=result_text, inline=True)
    embed.add_field(name="Response", value=message[:1024], inline=False)

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        log.warning("Missing permission to send in log channel %s", log_channel_id)
    except Exception as exc:
        log.exception("Failed to send log embed: %s", exc)


# ---------------------------------------------------------------------------
# Permission & setup checks
# ---------------------------------------------------------------------------
def has_allowed_role(interaction: discord.Interaction) -> bool:
    role_id = config.get("allowed_role")
    if role_id is None:
        return False
    return any(r.id == role_id for r in interaction.user.roles)


async def check_setup(interaction: discord.Interaction) -> bool:
    """Returns True if the bot is configured enough to run commands."""
    missing = []
    if not config.get("log_channel"):
        missing.append("`log_channel` — use `/config setlog`")
    if not config.get("allowed_role"):
        missing.append("`allowed_role` — use `/config setrole`")

    if missing:
        await interaction.response.send_message(
            "⚠️ **Bot not fully configured.** Missing:\n" + "\n".join(f"• {m}" for m in missing),
            ephemeral=True,
        )
        return False
    return True


async def check_permission(interaction: discord.Interaction) -> bool:
    """Returns True if the user has the allowed role."""
    if not has_allowed_role(interaction):
        await interaction.response.send_message(
            "❌ You don't have the required role to use script commands.",
            ephemeral=True,
        )
        return False
    return True


async def check_channel(interaction: discord.Interaction, script: str) -> bool:
    """Verify the command is run in the channel bound to this script."""
    bound: Optional[int] = config["script_channels"].get(script)
    if bound is None:
        return True  # Unbound — any channel is fine
    if interaction.channel.id != bound:
        ch = interaction.guild.get_channel(bound)
        mention = ch.mention if ch else f"<#{bound}>"
        await interaction.response.send_message(
            f"❌ This script can only be controlled in {mention}",
            ephemeral=True,
        )
        return False
    return True


async def run_script_command(
    interaction: discord.Interaction,
    action: str,
    script: str,
    payload: dict,
    roblox_username: Optional[str] = None,
    embed_title: str = "",
) -> None:
    """Shared runner for all script commands."""
    if not await check_setup(interaction):
        return
    if not await check_permission(interaction):
        return
    if not await check_channel(interaction, script):
        return

    await interaction.response.defer(thinking=True)

    result = await send_action(action, payload)
    success: bool = result.get("success", False)
    message: str = result.get("message", "No response from API.")

    embed = discord.Embed(
        title=embed_title or action.replace("_", " ").title(),
        description=message,
        colour=discord.Colour.green() if success else discord.Colour.red(),
    )
    embed.set_footer(text=f"Script: {script}")

    await interaction.followup.send(embed=embed)
    await log_execution(interaction, action, script, roblox_username, success, message)


# ---------------------------------------------------------------------------
# Script commands
# ---------------------------------------------------------------------------

@bot.tree.command(name="run", description="Execute a script for a Roblox user")
@app_commands.describe(script="Script name", roblox_username="Target Roblox username")
async def cmd_run(interaction: discord.Interaction, script: str, roblox_username: str):
    await run_script_command(
        interaction, "run", script,
        {"script": script, "roblox_username": roblox_username},
        roblox_username=roblox_username,
        embed_title="▶ Run",
    )


@bot.tree.command(name="setscript", description="Update a script to a new version")
@app_commands.describe(script="Script name", new_script_version="New script version / content")
async def cmd_setscript(interaction: discord.Interaction, script: str, new_script_version: str):
    await run_script_command(
        interaction, "set_script", script,
        {"script": script, "new_script_version": new_script_version},
        embed_title="📝 Set Script",
    )


@bot.tree.command(name="kickall", description="Kick all players from a script session")
@app_commands.describe(
    script="Script name",
    reason="Kick reason",
    roblox_username="Your Roblox username (for logging)",
)
async def cmd_kickall(interaction: discord.Interaction, script: str, reason: str, roblox_username: str):
    await run_script_command(
        interaction, "kick_all", script,
        {"script": script, "reason": reason, "roblox_username": roblox_username},
        roblox_username=roblox_username,
        embed_title="👢 Kick All",
    )


@bot.tree.command(name="shutdown", description="Send a shutdown signal to a script")
@app_commands.describe(script="Script name")
async def cmd_shutdown(interaction: discord.Interaction, script: str):
    await run_script_command(
        interaction, "shutdown", script,
        {"script": script},
        embed_title="⛔ Shutdown",
    )


@bot.tree.command(name="status", description="Check the current status of a script")
@app_commands.describe(script="Script name")
async def cmd_status(interaction: discord.Interaction, script: str):
    await run_script_command(
        interaction, "status", script,
        {"script": script},
        embed_title="📊 Status",
    )


# ---------------------------------------------------------------------------
# Global app command error handler
# ---------------------------------------------------------------------------
@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    msg = "❌ An unexpected error occurred."
    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ You need **Administrator** permission to use this command."
    elif isinstance(error, app_commands.BotMissingPermissions):
        msg = "❌ I'm missing required permissions to do that."
    elif isinstance(error, app_commands.CommandOnCooldown):
        msg = f"⏳ Command on cooldown. Try again in {error.retry_after:.1f}s."

    log.error("App command error: %s", error)

    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


# ---------------------------------------------------------------------------
# Admin /config command group
# ---------------------------------------------------------------------------
config_group = app_commands.Group(
    name="config",
    description="Bot configuration — Administrator only",
)


@config_group.command(name="setlog", description="Set the channel where execution logs are sent")
@app_commands.describe(channel="Text channel for logs")
@app_commands.checks.has_permissions(administrator=True)
async def cfg_setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    config["log_channel"] = channel.id
    save_config(config)
    log.info("Log channel set to #%s (%s)", channel.name, channel.id)
    await interaction.response.send_message(f"✅ Log channel set to {channel.mention}", ephemeral=True)


@config_group.command(name="setrole", description="Set the role allowed to use script commands")
@app_commands.describe(role="Role to grant script access")
@app_commands.checks.has_permissions(administrator=True)
async def cfg_setrole(interaction: discord.Interaction, role: discord.Role):
    config["allowed_role"] = role.id
    save_config(config)
    log.info("Allowed role set to @%s (%s)", role.name, role.id)
    await interaction.response.send_message(f"✅ Allowed role set to {role.mention}", ephemeral=True)


@config_group.command(name="bindscript", description="Restrict a script to a specific channel")
@app_commands.describe(script="Script name", channel="Channel that may control this script")
@app_commands.checks.has_permissions(administrator=True)
async def cfg_bindscript(interaction: discord.Interaction, script: str, channel: discord.TextChannel):
    config["script_channels"][script] = channel.id
    save_config(config)
    log.info("Script '%s' bound to #%s (%s)", script, channel.name, channel.id)
    await interaction.response.send_message(
        f"✅ Script `{script}` is now bound to {channel.mention}",
        ephemeral=True,
    )


@config_group.command(name="unbindscript", description="Remove the channel restriction from a script")
@app_commands.describe(script="Script name to unbind")
@app_commands.checks.has_permissions(administrator=True)
async def cfg_unbindscript(interaction: discord.Interaction, script: str):
    if script in config["script_channels"]:
        del config["script_channels"][script]
        save_config(config)
        log.info("Script '%s' unbound.", script)
        await interaction.response.send_message(f"✅ Script `{script}` unbound — usable from any channel.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ Script `{script}` was not bound.", ephemeral=True)


@config_group.command(name="view", description="View the current bot configuration")
@app_commands.checks.has_permissions(administrator=True)
async def cfg_view(interaction: discord.Interaction):
    log_ch_id = config.get("log_channel")
    role_id = config.get("allowed_role")
    script_chs: dict = config.get("script_channels", {})

    log_mention = f"<#{log_ch_id}>" if log_ch_id else "⚠️ Not set"
    role_mention = f"<@&{role_id}>" if role_id else "⚠️ Not set"

    if script_chs:
        bindings = "\n".join(f"`{s}` → <#{c}>" for s, c in script_chs.items())
    else:
        bindings = "*No scripts bound*"

    embed = discord.Embed(
        title="⚙️ Vortex Loader — Configuration",
        colour=discord.Colour.blurple(),
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="📋 Log Channel", value=log_mention, inline=False)
    embed.add_field(name="🎭 Allowed Role", value=role_mention, inline=False)
    embed.add_field(name="🔗 Script → Channel Bindings", value=bindings, inline=False)
    embed.set_footer(text="Use /config <command> to update settings")

    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.tree.add_command(config_group)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    log.info("Synced %d slash command(s).", len(synced))
    log.info("Config loaded: log_channel=%s | allowed_role=%s | scripts=%d",
             config.get("log_channel"),
             config.get("allowed_role"),
             len(config.get("script_channels", {})))


bot.run(DISCORD_TOKEN, log_handler=None)  # log_handler=None uses our custom logging
