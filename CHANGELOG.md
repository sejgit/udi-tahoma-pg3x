# Changelog



## 0.0.27

- **RTS Move By Percent**: new **MOVEPCT** command (percent 1–99, direction Up/Open or Down/Close) sends open or close, waits `(percent × total span) / 100` seconds, then sends stop; **SETSPAN** sets per-shade **Total Span Move Time** (GV1, default 8 s, persisted); **Last Command Executed** adds **Move By Percent**; RTS-only — io/Zigbee shades keep SETPOS
- **Fix RTS Total Span Move Time units**: GV1 and SETSPAN use UOM 58 (seconds), not UOM 101 (degrees)
- **Fix SETSPAN not updating GV1**: link command param to GV1 (`init="GV1"`) and read `command["value"]` like other PG3 plugins

## 0.0.26

- **Skip OGP protocol gateway during discovery**: TaHoma reports `ogp:Bridge` (Open Generic Protocol gateway) as a device; it is infrastructure, not a shade. Previously it appeared as an extra node with no useful commands. Run **Discover** after updating to remove an existing OGP node automatically.

## 0.0.25

- **Shade Last Command Executed (GV8)**: new status alongside Last Command (GV7); reports Open, Close, Stop, or My Position when sent; starts as None on node startup; GV7 still tracks Pending / Completed / Failed from the gateway

## 0.0.24

- **Clear server error sooner when the TaHoma gateway recovers**: auto-reconnect restores controller Connection status (ST=1) and clears the Polyglot error notice without a NodeServer restart
- **PG3 store manifest** (`server.json`) with executable `udi-tahoma-pg3x.py` — use **Update** from the store (validated on beta)
- **Rename entry script** from `udi-tahoma-pg3x` (no extension) to `udi-tahoma-pg3x.py`
- **Standard bootstrap** (error handling; version in `VERSION` / `profile/version.txt` / `server.json`)
- **Rename** `VersionHistory.md` to `CHANGELOG.md` (template standard)
- **Developer toolchain**: uv, pytest profile sync test, Makefile, CONTRIBUTING (runtime install unchanged: `install.sh` + `requirements.txt`)

## 0.0.23

- **Fix intermittent discovery failure**: TaHoma `setup/devices` sometimes returns partial records missing `controllableName`, `definition`, or `type`. pyoverkiz then raises `TypeError` and discovery aborts even though the gateway is online. Device fetch now uses a tolerant parser (same pattern as scenario `actionGroups`) that fills defaults and logs skipped records instead of failing startup.
- **Dependency security updates**: pin runtime floors in `requirements.txt` and refresh `Pipfile.lock` — `aiohttp>=3.13.4`, `requests>=2.33.0`, `pyasn1>=0.6.2`, `pyoverkiz>=1.13.0,<2.0.0` (cap 1.x API used by this plugin), plus dev lockfile bumps for urllib3, virtualenv, and filelock to clear Dependabot alerts.

## 0.0.22

- **Fix EISY Easy UI profile errors**: add `profile/version.txt`; align nodedefs with Python commands (`UPDATE_PROFILE` on controller, `ACTIVATE` in scene sends); fix controller NLS keys (`ST-ctl-*`); explicit editor subsets; remove unused debug editor/NLS

## 0.0.21

- **Docs: EISY-friendly formatting** — replace pipe tables with bullet lists in README and POLYGLOT_CONFIG (Polyglot on EISY does not render GFM tables)

## 0.0.20

- **Document optional cloud-only scenes**: clarify shades stay local; scene Activate is optional Somfy cloud; empty cloud credentials are OK; region table with `somfy_america` NA default; softer logs and no GV7 Failed when Activate skipped without credentials

## 0.0.19

- **Fix cloud region lookup**: pyoverkiz uses keys `somfy_america` / `somfy_europe` / `somfy_oceania`, not display names like `Somfy (North America)` — v0.0.18 cloud login never ran; alias mapping accepts both forms

## 0.0.18

- **Fix cloud scene Activate crash**: v0.0.17 raised `NameError: SUPPORTED_SERVERS is not defined` before Somfy cloud login could run; import fixed, cloud uses a separate HTTP session from local gateway auth, optional `tahoma_cloud_region` (default `somfy_america`)

## 0.0.17

- **Scene Activate via Somfy cloud**: local Developer Mode `actionGroups` list includes scene names but not device commands (`has no executable actions` in logs). TaHoma app scenes are server-side ([Somfy wontfix #21](https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode/issues/21)). Optional `tahoma_cloud_email` / `tahoma_cloud_password` run scenes through Somfy cloud `exec/{oid}`; shade commands stay local
- Try `GET actionGroups/{oid}` for full action details before cloud fallback; log per-scene local action counts at discovery

## 0.0.16

- **Scene Activate actually runs shades**: local Developer Mode API only supports `POST exec/apply` for action groups — not `POST exec/{oid}` for persisted TaHoma scenes. v0.0.15 masked the failure as Completed; scenes now copy the actionGroup's device commands to `exec/apply` (same path as shade commands)
- Revert v0.0.15 optimistic Completed for scenario parent exec

## 0.0.15

- **Scene Activate Last Command**: ignore spurious FAILED on scenario parent exec (TaHoma local API quirk); mark Completed ~5s after successful Activate

## 0.0.14

- **Fix custom data purge crash**: use `Custom.delete()` instead of `del` for custom data keys during stale node cleanup

## 0.0.13

- **Remove stale scene/shade nodes** from Polyglot DB during discovery cleanup (fixes orphan UUID scenes after v0.0.12)

## 0.0.12

- **Skip unnamed actionGroups** during scenario discovery (orphan/system records with no TaHoma label)

## 0.0.11

- **Fix scene node addresses** exceeding Polyglot 14-character limit (startup lockup)
- Scene OID persisted in custom data; addNode wait timeout prevents infinite hang

## 0.0.10

- **TaHoma scenario discovery** via raw actionGroups API (fixes pyoverkiz model mismatch)
- Scenario nodes: Activate plus Last Command (GV7), matching RTS shade feedback

## 0.0.9

- **Startup connect retries** with backoff (up to 10 min); health check and auto-reconnect while running

## 0.0.8

- **TaHoma plugin branding**: controller name TaHoma Controller; Applications docs (RTS/io/Zigbee)
- Phantom Blinds documented as primary RTS application
- Entry script renamed to `udi-tahoma-pg3x` (fresh Polyglot install required)

## 0.0.7

- **Dedicated RTS Shade nodedef** (Id, Battery, Last Command; Open/Close/Stop/MY only)
- Startup success notice auto-clears after 30 seconds
- User docs for RTS Last Command delay (TaHoma gateway timer)

## 0.0.6

- **Shade GV7 Last Command** driver (— / Pending / Completed / Failed) from TaHoma exec status
- Execution events logged at INFO; poll fallback via get_current_execution
- Preserve config placeholder notice during startup; show success notice after discovery
- Clearer Polyglot notice when TaHoma gateway is unreachable (offline/starting)

## 0.0.5

- Preserve config placeholder notice during startup; show success notice after discovery
- Clearer Polyglot notice when TaHoma gateway is unreachable (offline/starting)

## 0.0.4

- **Fix shade discovery** when gateway returns CommandDefinition lists (EISY/pyoverkiz)
- Default `tahoma_token` placeholder shortened to 20 zeros

## 0.0.3

- User docs consolidated to README.md and POLYGLOT_CONFIG.md
- Removed use_local_api parameter; default verify_ssl to false; clearer SSL verification errors
- Polyglot placeholder defaults for gateway_pin, tahoma_token, and gateway_ip

## 0.0.2

- Generic full-UI shade nodes for all discovered blinds (field feedback refines behavior)
- DeviceProfile from TaHoma discovery (protocol, commands, states)
- Skip gateway devices (Pod, WiFi, Zigbee transceiver) during discovery

## 0.0.1

- Initial repo setup
