# ChatGuard Roblox plugin (Roblox chat adapter)

A Roblox Studio plugin for intercepting messages detect whether they are safe, appropriate. This adaptor contains the Roblox-side code and project layout used to build and serve the place with Rojo.

# How to use this plugin

1. Install the plugin from the Roblox Marketplace.
2. Click the "ChatGuard init" button to generate the ChatGuard SDK.

## Prerequisites

- **Rojo** (recommended version 7.x): https://rojo.space/
- **Roblox Studio**: used to open and test the generated .rbxlx place

## Build

From the `roblox/roblox-chat-adaptor` directory, run:

```bash
rojo build -o "roblox-chat-adaptor.rbxlx"
```

This generates the place file `roblox-chat-adaptor.rbxlx` that can be opened in Roblox Studio.

## Serve (Development)

To run a live development server that syncs local changes to Roblox Studio, run:

```bash
rojo serve
```

Then open the generated/served place in Roblox Studio (use the Rojo plugin or open the provided place file) to see live updates.

## Folder structure

Top-level files

- **default.project.json**: Rojo project manifest used to map workspace files into the Roblox place.
- **roblox-adaptor-build.rbxlx**: (optional) pre-built place file you can open directly in Roblox Studio.

Key directories

- `src/init.server.luau` — entry point of the plugin
- `src/Modules/` — reusable modules for the installation process of the SDK
- `src/Template/` — represent how the SDK will be installed in Roblox Studio directory


## References

- Rojo docs: https://rojo.space/docs
