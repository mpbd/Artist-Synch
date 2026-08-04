# Artist-Synch
Artist-Synch is a Python and Tkinter-based desktop utility designed for musicians and producers to manage repositories of bands/artists, organize project structures, and handle smart backups and synchronization without creating duplicate files.

Features

    Band & Artist Management: Easily select, add, and organize workspaces for multiple bands or musical projects, supporting multiple primary and secondary storage locations (local disks and network drives).
    
    Fully Modular & Custom Folder Structure: Define and edit custom folder structures per band with flexible options to toggle project attributes per folder.
    
    Smart Synchronization & Deduplication: Powered by RoboCopy under the hood to ensure efficient file transfers and backups across locations without duplicating existing assets.
    Operations:
        Tag songs
        Sync Folders
        Sync Drives

Configuration

    Settings, locations, and custom folder layouts are managed via JSON configuration under the data/settings.json file, handled seamlessly through the built-in Config tab and settings manager.