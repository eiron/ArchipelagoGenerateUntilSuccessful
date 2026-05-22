# Generate Until Successful

An Archipelago tool that repeatedly runs `ArchipelagoGenerate.exe` until a multiworld is successfully generated.

## How It Works

1. Counts existing ZIP files in the `output` directory
2. Runs `ArchipelagoGenerate.exe`
3. Checks if a new ZIP file appeared in `output`
4. If not, retries automatically until successful (or stopped by user)

## Installation

1. Copy `generate_until_successful.apworld` to your Archipelago `custom_worlds` directory
2. Restart the Archipelago launcher
3. The tool will appear in the **Tools** menu as "Generate Until Successful"

## Usage

1. Open the Archipelago Launcher
2. Go to Tools > "Generate Until Successful"
3. Click **Start** to begin generation attempts
4. The tool will retry automatically until a ZIP is produced
5. Click **Stop** at any time to cancel

## Features

- **Automatic Retries**: Keeps trying until generation succeeds
- **Real-time Logging**: Shows attempt progress and generator output
- **Attempt Counter**: Displays current attempt number
- **MemoryError Detection**: Stops retries if a memory error is detected
- **Stop Button**: Cancel at any time

## System Requirements

- Archipelago (with `ArchipelagoGenerate.exe` present)
- Python 3.7+ (included with Archipelago)
- Kivy (for GUI - automatically handled by Archipelago)
