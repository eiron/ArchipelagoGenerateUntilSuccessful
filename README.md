# Generate Until Successful

An Archipelago tool that repeatedly runs `ArchipelagoGenerate.exe` until a multiworld is successfully generated.

## How It Works

1. Runs `ArchipelagoGenerate.exe`
2. Watches the generator output for the success marker `Creating final archive at ...`
3. Treats that log line as a successful generation
4. Tracks total runs, successful runs, and failed runs separately
5. Keeps going until either the target number of successful runs is reached, the failure limit is hit, or the user stops it

## Installation

1. Copy `generate_until_successful.apworld` to your Archipelago `custom_worlds` directory
2. Restart the Archipelago launcher
3. The tool will appear in the **Tools** menu as "Generate Until Successful"

## Usage

1. Open the Archipelago Launcher
2. Go to Tools > "Generate Until Successful"
3. Choose a seed if needed
4. Optionally set a max failure limit and/or a target number of successful runs
5. Click **Start** to begin generation attempts
6. The tool will keep retrying until it reaches the target or you stop it
7. Click **Stop** at any time to cancel

## Features

- **Automatic Retries**: Keeps trying until generation succeeds
- **Failure Limit**: Abort after a chosen number of failed runs
- **Successful Run Target**: Stop after a chosen number of successful generations
- **Real-time Logging**: Shows attempt progress and generator output
- **Attempt Counter**: Displays current attempt number
- **MemoryError Detection**: Stops retries if a memory error is detected
- **Stop Button**: Cancel at any time

## System Requirements

- Archipelago (with `ArchipelagoGenerate.exe` present)
- Python 3.7+ (included with Archipelago)
- Kivy (for GUI - automatically handled by Archipelago)
