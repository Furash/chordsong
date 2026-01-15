<div class="logo-container">
    <img src="/chordsong/logo/chordsong_logo.png" alt="Logo" class="logo-dark">
    <img src="/chordsong/logo/chordsong_logo_inv.png" alt="Logo" class="logo-light">
</div>



**Chord Song** is an efficiency-focused Blender add-on that introduces `<Leader>` key functionality and chord-based mappings. Inspired by Neovim addon `which-key.nvim`, it allows you to trigger operators, execute custom Python scripts, and modify properties using short, memorable key sequences known as `chords`.

### Why Chords?
Traditional hotkey systems suffer from "keybind exhaustion," where users must memorize awkward combinations like `Ctrl+Alt+Shift+F12`. Chord Song solves this by:

- Reducing cognitive load: Use intuitive sequences (e.g., `m c` for **M**esh > **C**ube).
- Conserving hotkey real estate: A single leader key (e.g., `Space`) opens up dozens of unique combinations.
- Providing visual feedback: The dynamic overlay shows available options as you type, eliminating the need for perfect memory.

## Key Features

- **Context Menu Integration**: Right-click any Blender UI element to instantly add it to your chord library. Works with operators, properties, toggles, and Info panel history.
- **Leader Key System**: Initiate actions with a `<Leader>` key *(default: `Space`).*
- **Context Awareness**: Mappings dynamically filter based on your active editor (e.g., 3D View, UV, Shader Editor).
- **Smart Recents**: Double-tap the leader key to access your most recent actions.
- **Scripts Overlay**: Quick access to custom Python scripts with fuzzy search and numbered execution (default: `<Leader> x`).
- **Mapping System**: Bind chords to Operators, Properties, Toggles, or external Python files.

## Quick Start Guide

To get started with Chord Song, follow these steps:

### 1. Project Prerequisites (Required for Icons)
Chord Song uses **Nerd Font** icons to provide visual cues in the overlay. Without this, icons will appear as missing character boxes.

**Installation Steps:**

1. Download a [Nerd Font](https://www.nerdfonts.com/font-downloads) (e.g., Ubuntu Nerd Font).
2. Install the font on your operating system.
3. In Blender, navigate to **Edit > Preferences > Interface > Text Rendering**.
4. Set the **Interface Font** to your installed Nerd Font.

![Text Rendering](/chordsong/scr/text_rendering.png){ width="640" }

### 2. Download the Add-on
Choose your preferred platform to download the latest `.zip` release:

<!-- markdownlint-disable -->
<div class="download-grid">

<a href="https://github.com/furash/chordsong/releases" class="download-card" target="_blank">
    <div class="download-card__icon">
        <svg viewBox="0 0 24 24" style="width: 2rem; height: 2rem; fill: currentColor;">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
        </svg>
    </div>
    <div class="download-card__title">GitHub</div>
</a>

<a href="https://furash.gumroad.com/l/chordsong" class="download-card" target="_blank">
    <div class="download-card__icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 157 22" style="max-width: 100%; height: 1.5rem; fill: currentColor;">
            <path fill="currentColor" d="M93.293.778c-3.243 0-6.413 2.805-6.777 6.858V1.112h-4.657v19.671h4.714v-9.521c0-2.667 1.979-6.43 6.72-6.43zm49.485 16.856V4.157h2.731c3.641 0 6.599 2.174 6.599 6.63s-2.958 6.847-6.599 6.847zm-4.665 3.152h7.965c4.892 0 10.922-3.043 10.922-9.999 0-6.847-6.03-9.673-10.922-9.673h-7.965zm-17.889-9.78c0-3.587 1.934-6.521 5.12-6.521 3.072 0 4.779 2.934 4.779 6.52 0 3.587-1.707 6.522-4.779 6.522-3.186 0-5.12-2.935-5.12-6.521m-4.779.217c0 5.869 3.186 9.999 8.192 9.999 3.641 0 5.803-2.282 6.941-5.978v5.543h4.664V1.116h-4.664v5.216C129.554 2.855 127.392.79 123.979.79c-5.12 0-8.534 4.456-8.534 10.433M9.216 21.222C3.413 21.222 0 16.766 0 11.223 0 5.463 3.755.79 10.923.79c7.395 0 9.898 4.782 10.012 7.499h-5.347c-.114-1.522-1.48-3.804-4.78-3.804-3.526 0-5.802 2.934-5.802 6.52 0 3.587 2.276 6.522 5.803 6.522 3.186 0 4.551-2.391 5.12-4.782h-5.12v-1.957h10.743v10H16.84v-6.304c-.341 2.282-1.82 6.738-7.623 6.738Zm21.892-.002c-4.437 0-7.168-2.825-7.168-8.477V1.114h4.779v11.63c0 2.934 1.479 4.347 3.982 4.347 4.892 0 6.713-5.76 6.713-9.782V1.114h4.778v19.672h-4.664v-7.282c-.91 4.021-3.414 7.717-8.42 7.717ZM72.741.778c-4.077 0-6.649 3.762-7.488 7.24-.144-4.66-2.544-7.24-6.383-7.24-3.318 0-6.396 2.826-7.195 7.297V1.113h-4.658v19.672h4.718v-7.052c0-1.749.763-8.924 5.512-8.924 3.077 0 3.398 2.651 3.398 6.275v9.701h4.716v-7.052c0-1.749.794-8.924 5.544-8.924 3.074 0 3.392 2.651 3.392 6.275v9.701h4.722V9.15c.022-5.582-2.042-8.37-6.278-8.37Zm30.674 0C97.306.778 93.168 5.353 93.168 11c0 6.221 3.936 10.22 10.247 10.22 6.108 0 10.32-4.574 10.32-10.22 0-6.222-4.013-10.222-10.32-10.222m0 16.96c-3.556 0-5.86-2.875-5.86-6.738s2.312-6.74 5.86-6.74c3.547 0 5.766 2.876 5.766 6.74 0 3.863-2.221 6.739-5.766 6.739Z"/>
        </svg>
    </div>
    <div class="download-card__title" style="color: #c4642b;">Buy me a coffee</div>
</a>

<a href="https://extensions.blender.org/add-ons/chordsong" class="download-card" target="_blank">
    <div class="download-card__icon">
        <svg viewBox="-10 -10 181.5 181.5" style="width: 1.75rem; height: 1.75rem; fill: currentColor; overflow: visible;">
            <path d="M61.1 104.56c.05 2.6.88 7.66 2.12 11.61a61.27 61.27 0 0 0 13.24 22.92 68.39 68.39 0 0 0 23.17 16.64 74.46 74.46 0 0 0 30.42 6.32 74.52 74.52 0 0 0 30.4-6.42 68.87 68.87 0 0 0 23.15-16.7 61.79 61.79 0 0 0 13.23-22.97 58.06 58.06 0 0 0 2.07-25.55 59.18 59.18 0 0 0-8.44-23.1 64.45 64.45 0 0 0-15.4-16.98h.02L112.76 2.46l-.16-.12c-4.09-3.14-10.96-3.13-15.46.02-4.55 3.18-5.07 8.44-1.02 11.75l-.02.02 26 21.14-79.23.08h-.1c-6.55.01-12.85 4.3-14.1 9.74-1.27 5.53 3.17 10.11 9.98 10.14v.02l40.15-.07-71.66 55-.27.2c-6.76 5.18-8.94 13.78-4.69 19.23 4.32 5.54 13.51 5.55 20.34.03l39.1-32s-.56 4.32-.52 6.91zm100.49 14.47c-8.06 8.2-19.34 12.86-31.54 12.89-12.23.02-23.5-4.6-31.57-12.79-3.93-4-6.83-8.59-8.61-13.48a35.57 35.57 0 0 1 2.34-29.25 39.1 39.1 0 0 1 9.58-11.4 44.68 44.68 0 0 1 28.24-9.85 44.59 44.59 0 0 1 28.24 9.77 38.94 38.94 0 0 1 9.58 11.36 35.58 35.58 0 0 1 4.33 14.18 35.1 35.1 0 0 1-1.98 15.05 37.7 37.7 0 0 1-8.61 13.52zm-57.6-27.91a23.55 23.55 0 0 1 8.55-16.68 28.45 28.45 0 0 1 18.39-6.57 28.5 28.5 0 0 1 18.38 6.57 23.57 23.57 0 0 1 8.55 16.67c.37 6.83-2.37 13.19-7.2 17.9a28.18 28.18 0 0 1-19.73 7.79c-7.83 0-14.84-3-19.75-7.8a23.13 23.13 0 0 1-7.19-17.88z"></path>
        </svg>
    </div>
    <div class="download-card__title">Blender Extensions</div>
</a>

</div>
<!-- markdownlint-enable -->

### 3. Installation
1. In Blender go to **Edit > Preferences > Extensions**.
2. Click **Install...** and select the downloaded `.zip` file.
3. Search for "Chord Song" and ensure the checkbox is enabled.

After installation, proceed to the [Chord Mappings](concepts/chord.md) to define your first sequence.

## Security & Safety

**Python Script Execution:**

Chord Song allows for the execution of arbitrary Python scripts via chord mappings. 

- **Safeguard Enabled**: Script execution is **disabled by default**. You must explicitly enable "Allow Custom User Scripts" in Preferences before script mappings will work.
- **Identify Your Scripts**: Only map chords to `.py` files you have written or audited.
- **Permission Boundary**: The add-on executes scripts within the standard Blender Python environment.

Always review the source code of any script before adding it to your library. See [Script Mappings](configuration/mappings/script.md#security-safeguard) for details on enabling script execution.

