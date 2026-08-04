# Artist-Synch
Artist-Synch is a lightweight Python and Tkinter desktop application designed to streamline project management and backups across multiple bands and artists. It leverages RoboCopy under the hood to perform efficient, zero-duplicate synchronization between local drives, external disks, and network shares.

## Key Features

Multi-Band Workspaces — Easily switch between different artist repositories and manage their storage locations in one central dashboard.
    
Fully Modular Folder Structures — Tailor your directory layouts per band (e.g., Projetos, Audio, Visual, Documentos) with customizable project attribute toggles.
    
Smart Deduplication & Syncing — Powered by RoboCopy for robust, fast, and safe file transfers without redundant copies.
    
Core Operations:
    Tag Songs — Organize and tag your audio stems and track assets.
    Sync Folders — Keep specific project directories aligned across storage paths.
    Sync Drives — Perform full backup sweeps across drives and network nodes (e.g., bd-music-1).

## Configuration

All configurations, paths, and custom folder layouts are stored locally under data/settings.json, and can be managed seamlessly through the built-in Config interface inside the app.