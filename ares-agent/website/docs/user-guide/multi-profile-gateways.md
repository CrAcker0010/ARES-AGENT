---
sidebar_position: 4
---

# Running Many Gateways at Once

Operate multiple [profiles](./profiles.md) — each with its own bot tokens,
sessions, and memory — as managed services on a single machine. This page
covers the operational concerns: starting them all together, viewing logs
across profiles, preventing the host from sleeping, and recovering from common
launchd/systemd quirks.

If you only run one Ares agent, you don't need this page — see
[Profiles](./profiles.md) for the basics.

## When to use this

You want this setup when you have two or more Ares agents that should all
be online at the same time. Common reasons:

- A personal assistant on one Telegram bot and a coding agent on another
- One agent per family member or one per Slack workspace
- Sandbox + production instances of the same configuration
- A research agent + a writing agent + a cron-driven bot — each with isolated
  memory and skills

Every profile already gets its own per-platform LaunchAgent
(`ai.ares.gateway-<name>.plist`) or systemd user service
(`ares-gateway-<name>.service`). This guide adds the patterns for managing
them collectively.

## Quick start

```bash
# Create profiles (once)
ares profile create coder
ares profile create personal-bot
ares profile create research

# Configure each
coder setup
personal-bot setup
research setup

# Install each gateway as a managed service
coder gateway install
personal-bot gateway install
research gateway install

# Start them all
coder gateway start
personal-bot gateway start
research gateway start
```

That's it — three independent agents, each on its own process, restarting
automatically on crash and on user login.

## Start, stop, or restart all gateways at once

The CLI ships with single-profile lifecycle commands. To act across every
profile, wrap them in a shell loop. Put the snippet below in
`~/.local/bin/ares-gateways` and `chmod +x` it:

```sh
#!/bin/sh
set -eu

# Add or remove profile names here as you create / delete profiles.
profiles="default coder personal-bot research"

usage() {
  echo "Usage: ares-gateways {start|stop|restart|status|list}"
}

run_for_profile() {
  profile="$1"
  action="$2"
  if [ "$profile" = "default" ]; then
    ares gateway "$action"
  else
    ares -p "$profile" gateway "$action"
  fi
}

action="${1:-}"
case "$action" in
  start|stop|restart|status)
    for profile in $profiles; do
      echo "==> $action $profile"
      run_for_profile "$profile" "$action"
    done
    ;;
  list)
    ares gateway list
    ;;
  *)
    usage
    exit 2
    ;;
esac
```

Then:

```bash
ares-gateways start      # start every configured profile
ares-gateways stop       # stop every configured profile
ares-gateways restart    # restart all
ares-gateways status     # status across all
ares-gateways list       # delegates to `ares gateway list`
```

:::tip
The `default` profile is targeted with `ares gateway <action>` (no `-p`),
not `ares -p default gateway <action>`. The wrapper above handles both forms.
:::

## Manage one profile

The shortcut commands every profile installs:

```bash
coder gateway run        # foreground (Ctrl-C to stop)
coder gateway start      # start the managed service
coder gateway stop       # stop the managed service
coder gateway restart    # restart
coder gateway status     # status
coder gateway install    # create the LaunchAgent / systemd unit
coder gateway uninstall  # remove the service file
```

These are equivalent to `ares -p coder gateway <action>` — useful if a
profile alias is not on `PATH` or if you target profiles dynamically from a
script.

## Service files

Each profile installs its own service with a unique name, so installations
never clash:

| Platform | Path                                                              |
| -------- | ----------------------------------------------------------------- |
| macOS    | `~/Library/LaunchAgents/ai.ares.gateway-<profile>.plist`        |
| Linux    | `~/.config/systemd/user/ares-gateway-<profile>.service`         |

The default profile keeps the historical names: `ai.ares.gateway.plist` /
`ares-gateway.service`.

## Viewing logs

Each profile writes to its own log files:

```bash
# Default profile
tail -f ~/.ares/logs/gateway.log
tail -f ~/.ares/logs/gateway.error.log

# Named profile
tail -f ~/.ares/profiles/<name>/logs/gateway.log
tail -f ~/.ares/profiles/<name>/logs/gateway.error.log
```

Stream every profile's log simultaneously:

```bash
tail -f ~/.ares/logs/gateway.log ~/.ares/profiles/*/logs/gateway.log
```

The CLI also has a structured log viewer:

```bash
ares logs -f                  # follow default profile
ares -p coder logs -f         # follow one profile
ares logs --help              # filters, levels, JSON output
```

## Identify what's actually running

```bash
ares profile list             # profiles + model + gateway state
ares-gateways status          # full status across every profile
launchctl list | grep ares    # macOS — PIDs and labels
systemctl --user list-units 'ares-gateway-*'   # Linux — units
```

## Editing configuration

Every profile keeps its config inside its own directory:

```
~/.ares/profiles/<name>/
├── .env              # API keys, bot tokens (chmod 600)
├── config.yaml       # model, provider, toolsets, gateway settings
└── SOUL.md           # personality / system prompt
```

The default profile uses `~/.ares/` directly with the same three files.

Edit them with any editor or via the CLI:

```bash
ares config set model.model anthropic/claude-sonnet-4    # default profile
coder config set model.model openai/gpt-5                  # named profile
```

After editing `.env` or `config.yaml`, restart the affected gateway:

```bash
coder gateway restart
# or, for everything:
ares-gateways restart
```

## Keeping the host awake

The gateway process can run all day, but the operating system will still try
to sleep when idle. Two patterns:

### macOS — `caffeinate`

`caffeinate` is built into macOS and prevents sleep while it runs. No install.

```bash
caffeinate -dis                    # block display, idle, and system sleep
caffeinate -dis -t 28800           # same, auto-exit after 8 hours
caffeinate -i -w $(cat ~/.ares/gateway.pid) &   # awake while default gateway runs

# Persistent: run in background and forget
nohup caffeinate -dis >/dev/null 2>&1 &
disown

# Inspect / stop
pmset -g assertions | grep -iE 'caffeinate|prevent|user is active'
pkill caffeinate
```

| Flag   | Effect                                            |
| ------ | ------------------------------------------------- |
| `-d`   | block display sleep                               |
| `-i`   | block idle system sleep (default)                 |
| `-m`   | block disk sleep                                  |
| `-s`   | block system sleep (AC-powered Macs only)         |
| `-u`   | simulate user activity (prevents screen lock)     |
| `-t N` | auto-exit after `N` seconds                       |
| `-w P` | exit when PID `P` exits                           |

:::warning Lid-close still sleeps the Mac
`caffeinate` cannot override the hardware-driven lid-close sleep on MacBooks.
For lid-closed operation, change your Energy Saver / Battery preferences or
use a third-party tool.
:::

### Linux — `systemd-inhibit` or `loginctl`

```bash
# Inhibit suspend while a command runs
systemd-inhibit --what=idle:sleep --who=ares --why="gateways running" \
  sleep infinity &

# Allow user services to keep running after logout (recommended)
sudo loginctl enable-linger "$USER"
```

After enabling lingering, your systemd user units (including
`ares-gateway-<profile>.service`) continue running across SSH disconnects
and reboots.

## Token-conflict safety

Each profile must use unique bot tokens for each platform. If two profiles
share a Telegram, Discord, Slack, WhatsApp, or Signal token, the second
gateway refuses to start with an error naming the conflicting profile.

To audit:

```bash
grep -H 'TELEGRAM_BOT_TOKEN\|DISCORD_BOT_TOKEN' \
     ~/.ares/.env ~/.ares/profiles/*/.env
```

## Updating the code

`ares update` pulls the latest code once and syncs new bundled skills into
every profile:

```bash
ares update
ares-gateways restart
```

User-modified skills are never overwritten.

## Troubleshooting

### "Could not find service in domain for user gui: 501"

You ran `ares gateway start` after a previous `ares gateway stop`. The
CLI's `stop` does a full `launchctl unload`, which removes the service from
launchd's registry. The CLI catches this specific error on `start` and
automatically re-loads the plist (`↻ launchd job was unloaded; reloading
service definition`). The service starts normally. Nothing to fix.

### Stale PID after a crash

If a profile's gateway shows `not running` but a process is still alive:

```bash
ps -ef | grep "ares_cli.*-p <profile>"
cat ~/.ares/profiles/<profile>/gateway.pid
kill -TERM <pid>          # graceful
kill -KILL <pid>          # if that fails after a few seconds
<profile> gateway start
```

### Forcing a hard reset of one service

```bash
# macOS
launchctl unload ~/Library/LaunchAgents/ai.ares.gateway-<profile>.plist
launchctl load   ~/Library/LaunchAgents/ai.ares.gateway-<profile>.plist

# Linux
systemctl --user restart ares-gateway-<profile>.service
```

### Health check

```bash
ares doctor                  # default profile
ares -p <profile> doctor     # one profile
```
