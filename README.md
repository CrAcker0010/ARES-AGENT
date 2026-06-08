# ARES-AGENT Repository Structure & Setup Guide

## 📁 Repository Structure

### Root Directory
```
ARES-AGENT/
├── ares-agent/                 # Main application directory
├── bin/                        # Binary/executable files
├── cron/                       # Scheduled tasks & cron jobs
├── gateway-service/            # Gateway service components
├── sessions/                   # Session management files
├── skills/                     # Skills modules and plugins
├── config.yaml                 # Main configuration file
├── channel_directory.json      # Channel platform mappings
├── SOUL.md                     # Project philosophy/soul
├── tasks_to_do.md             # Task tracking
├── migrate.ps1                # Migration scripts (PowerShell)
└── visual_memory.html         # Visual memory interface
```

### Core Application Directory: `ares-agent/`

#### Configuration & Setup Files
```
ares-agent/
├── .env.example               # Environment variables template (COPY THIS TO .env)
├── .envrc                     # Environment configuration for direnv
├── .gitignore                 # Git ignore patterns
├── .dockerignore              # Docker ignore patterns
├── .gitattributes            # Git attributes configuration
├── .hadolint.yaml            # Dockerfile linting rules
├── .mailmap                  # Git author mapping
├── cli-config.yaml.example   # CLI configuration template
├── pyproject.toml            # Python project configuration
├── setup.py                  # Python setup script
├── package.json              # Node.js dependencies
├── package-lock.json         # Lock file for npm packages
├── uv.lock                   # UV package manager lock file
├── Dockerfile                # Docker containerization
├── docker-compose.yml        # Docker compose configuration
├── docker-compose.windows.yml # Windows-specific compose config
├── LICENSE                   # License information
├── MANIFEST.in              # Package manifest
├── README.md                # Project README
├── README.zh-CN.md          # Chinese translation
├── README.ur-pk.md          # Urdu translation
├── AGENTS.md                # Agent documentation
├── CONTRIBUTING.md          # Contribution guidelines
├── SECURITY.md              # Security guidelines
└── ares-already-has-routines.md # Existing routines documentation
```

#### Main Application Code
```
ares-agent/
├── cli.py                   # Command-line interface (615KB)
├── run_agent.py             # Main agent runner (236KB)
├── ares_bootstrap.py        # Bootstrap initialization
├── ares_constants.py        # Constants definitions
├── ares_logging.py          # Logging configuration
├── ares_state.py            # State management (187KB)
├── ares_time.py             # Time utilities
├── batch_runner.py          # Batch processing
├── model_tools.py           # Model tools (55KB)
├── mcp_serve.py             # MCP server (31KB)
├── mini_swe_runner.py       # Mini SWE runner
├── trajectory_compressor.py # Trajectory compression (69KB)
├── toolsets.py              # Toolset definitions
├── toolset_distributions.py # Toolset distribution logic
├── utils.py                 # Utility functions
└── ares                     # Entry point script
```

#### Subdirectories

**Core Components:**
- `agent/` - Core agent implementation
- `ares_cli/` - CLI interface
- `gateway/` - Gateway service implementation
- `tools/` - Tool definitions and implementations
- `providers/` - Provider implementations
- `plugins/` - Plugin system

**Skills & Extensions:**
- `skills/` - Built-in skills
- `optional-skills/` - Optional skill modules
- `optional-mcps/` - Model Context Protocol servers

**Configuration & Data:**
- `acp_adapter/` - Adapter implementations
- `acp_registry/` - Registry for adaptive control
- `plans/` - Pre-built plans
- `.plans/` - Local plans storage

**UI & Web:**
- `ui-tui/` - Terminal UI
- `web/` - Web interface
- `apps/` - Desktop applications
- `tui_gateway/` - TUI gateway

**Utilities:**
- `scripts/` - Utility scripts
- `tests/` - Test suite
- `docs/` - Documentation
- `docker/` - Docker configurations
- `nix/` - Nix configurations
- `packaging/` - Packaging scripts
- `.github/` - GitHub workflows
- `locales/` - Internationalization files
- `infographic/` - Visual assets
- `datagen-config-examples/` - Data generation examples

### Skills Directory: `skills/`

The skills directory is organized by category:

```
skills/
├── apple/                    # Apple ecosystem integration
├── autonomous-ai-agents/     # AI agent frameworks
├── creative/                 # Creative tasks
├── data-science/            # Data science tools
├── devops/                   # DevOps tools
├── dogfood/                  # Internal testing
├── email/                    # Email integration
├── github/                   # GitHub integration
├── media/                    # Media handling
├── mlops/                    # ML operations
├── note-taking/              # Note-taking tools
├── productivity/             # Productivity tools
├── red-teaming/              # Security testing
├── research/                 # Research tools
├── smart-home/               # Smart home integration
├── social-media/             # Social media tools
├── software-development/     # Development tools
└── yuanbao/                  # Yuanbao integration
```

## 🚀 Setup Guide

### Prerequisites

- **Python 3.11+** (recommended: 3.11 or higher)
- **Node.js 20+** (for web components)
- **Git**
- **Docker** (optional, for containerized deployment)
- **pip** or **uv** (Python package manager)

### Step 1: Clone the Repository

```bash
git clone https://github.com/CrAcker0010/ARES-AGENT.git
cd ARES-AGENT
```

### Step 2: Setup Python Environment

Navigate to the ares-agent directory:

```bash
cd ares-agent
```

**Option A: Using Python venv (Recommended)**
```bash
python3 -m venv venv

# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

**Option B: Using uv (Faster)**
```bash
# Install uv if you haven't already
pip install uv

# Create virtual environment with uv
uv sync
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Using pip
pip install -r requirements.txt  # If exists
# OR
pip install -e .

# Using uv
uv pip install -e .
```

### Step 4: Environment Configuration

Create your `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key  # If using OpenAI

# Model Configuration
DEFAULT_MODEL=gemini-2.5-flash

# Terminal Configuration
TERMINAL_BACKEND=local
CWD=.

# Web Configuration
WEB_BACKEND=ddgs  # DuckDuckGo search

# Browser Configuration
BROWSER_ENGINE=auto

# Additional configurations as needed
```

### Step 5: Install Node.js Dependencies (If Needed)

For web components:

```bash
npm install
# OR
yarn install
# OR
pnpm install
```

### Step 6: Initialize Configuration

Copy CLI configuration template:

```bash
cp cli-config.yaml.example cli-config.yaml
```

Edit `cli-config.yaml` with your preferences (optional).

### Step 7: Run the Application

#### Start the Agent

```bash
# Using the CLI
python -m ares_cli

# Or directly with Python
python cli.py

# Or using the ares command (if installed)
ares
```

#### Using Docker (Optional)

```bash
# Build the Docker image
docker build -t ares-agent .

# Run the container
docker-compose up -d

# Run with Windows-specific compose
docker-compose -f docker-compose.windows.yml up -d
```

### Step 8: Verify Installation

Test that everything is working:

```bash
# Check Python installation
python --version

# Test imports
python -c "import ares_cli; print('✓ ARES-AGENT imported successfully')"

# Run tests (if available)
pytest tests/
```

## 📋 Configuration Files Reference

### `.env` Variables
- `API_KEYS`: Store all API keys here (Git-ignored)
- `MODEL_CONFIGURATION`: Model preferences
- `TERMINAL_SETTINGS`: Terminal backend and behavior
- `WEB_SETTINGS`: Web search configuration

### `config.yaml` Structure
- `model`: Default model and provider settings
- `agent`: Agent behavior configuration
- `terminal`: Terminal execution settings
- `web`: Web search settings
- `browser`: Browser automation settings
- `memory`: Memory management settings
- `skills`: Skill system configuration
- `integrations`: Platform integrations (Discord, Slack, Telegram, etc.)

### `cli-config.yaml` Structure
- CLI-specific preferences
- Display settings
- Tool configurations
- Custom personalities and personas

## 🔐 Security Notes

✅ **Security Best Practices Implemented:**
- Sensitive data excluded via `.gitignore`
- `.env` files never committed
- Private keys protected
- Database files not tracked
- Configuration templates provided without secrets

### What's Ignored (Not in Repository)

```
.env                    # Local environment variables
*.db                    # Database files
auth.json              # Authentication data
*.pem, *.ppk          # Private keys
logs/                 # Log files
cache/                # Cache directories
venv/                 # Virtual environment
```

## 📚 Next Steps

1. **Read Documentation**: Check `ares-agent/README.md` for detailed information
2. **Explore Skills**: Browse `skills/` directory for available modules
3. **Review Agents**: See `ares-agent/AGENTS.md` for agent documentation
4. **Contribution**: Read `ares-agent/CONTRIBUTING.md` to start contributing
5. **Security**: Review `ares-agent/SECURITY.md` for security policies

## 🛠️ Common Commands

```bash
# Start interactive session
python cli.py

# Run batch operations
python batch_runner.py

# Start gateway service
python -m ares_cli gateway start

# Check configuration
python -m ares_cli config show

# Run tests
pytest tests/ -v

# Build documentation
python -m sphinx docs/ docs/_build/
```

## 📞 Support & Documentation

- **Main README**: `ares-agent/README.md`
- **Contributing**: `ares-agent/CONTRIBUTING.md`
- **Security**: `ares-agent/SECURITY.md`
- **Agents**: `ares-agent/AGENTS.md`
- **Project Philosophy**: `SOUL.md`

## 📄 License

See `ares-agent/LICENSE` for license information.

---

**Last Updated**: June 8, 2026
**Repository**: [CrAcker0010/ARES-AGENT](https://github.com/CrAcker0010/ARES-AGENT)
