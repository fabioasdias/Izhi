# Izhi

Analyze PR review comments across a GitHub organization.

## Name Origins

Both names come from [Ojibwe](https://en.wikipedia.org/wiki/Ojibwe_language) (also known as Anishinaabemowin), an Algonquian language spoken by the Anishinaabe people around the Great Lakes region of North America, from Quebec through Ontario and Manitoba, and in the US from Michigan to Montana.

- **izhi** - A verb meaning "say to, speak so to" ([source](https://ojibwe.lib.umn.edu/main-entry/izhi-vta)). The stem /iN-/ carries the sense of "thus, in a certain direction, in a certain manner." Used in contexts like telling someone something, giving directions, or conveying a message.

- **mikan** - A verb meaning "find it" ([source](https://ojibwe.lib.umn.edu/main-entry/mikan-vti)). From the stem /mik-/, used when locating or discovering something—"I find it" (*nimikaan*), "try to find it," or "I can't find the document."

## Installation

```bash
pip install izhi
```

## Usage

### Collect PR Data

```bash
# Set your GitHub token
export GITHUB_TOKEN=ghp_...

# Fetch PR data for an organization
izhi --org myorg --output data.json

# Filter by date range
izhi --org myorg --since 2024-01-01 --until 2024-12-31 --output data.json
```

### View Dashboard

```bash
# Open dashboard in browser (default port 8080)
mikan

# Use custom port
mikan --port 3000

# Don't auto-open browser
mikan --no-browser
```

Load your JSON data file in the dashboard to visualize PR review patterns.

## Commands

- `izhi` - Collect PR review data from GitHub
- `mikan` - Serve the visualization dashboard

## Requirements

- Python 3.10+
- GitHub Personal Access Token with repo read access
