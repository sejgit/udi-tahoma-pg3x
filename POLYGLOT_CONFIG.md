# Somfy TaHoma — Polyglot Configuration
<!-- markdownlint-disable-file MD036 MD007 MD022 MD013 -->

Configuration guide for the **Somfy TaHoma NodeServer** (Polyglot V3 on EISY/Polisy). Phantom Blinds and other shade families are supported as **applications** on the same gateway — see [Applications](#applications).

## Applications

The NodeServer connects once to your TaHoma gateway and discovers all paired devices. The **protocol** reported by the gateway determines the ISY node type and available status fields:

- **RTS** (one-way radio)
  - Examples: **Phantom Blinds**, Somfy RTS rollers/awnings
  - Node type: **RTS Shade**
  - Status: Id, Battery, **Last Command** — no position or motion
- **io** (io-homecontrol)
  - Examples: Somfy RS100, many two-way rollers
  - Node type: **Shade**
  - Status: Position (and often tilt) when the gateway reports states
- **Zigbee**
  - Examples: TaHoma-paired Zigbee motors
  - Node type: **Shade**
  - Status: Varies; position when reported
- **Other**
  - Examples: Less common TaHoma device types
  - Node type: **Shade**
  - Status: Best-effort from discovery

### Phantom Blinds (RTS)

**Phantom Blinds** use Somfy RTS motors through TaHoma. They are discovered as **RTS Shade** nodes with Open, Close, Stop, and My Position only. See [RTS shades and Last Command](#rts-shades-and-last-command) for **Last Command (GV7)** behavior and timing.

If you have io or Zigbee shades as well, they appear as full **Shade** nodes alongside RTS nodes under the same controller.

## Prerequisites

1. Somfy TaHoma RTS/Zigbee gateway (Item #1811731) on your network
2. Shades paired and working in the TaHoma mobile app
3. Developer Mode enabled in the TaHoma app
4. Bearer token generated and saved securely (shown only once)
5. Gateway PIN noted (`XXXX-XXXX-XXXX`)

## Configuration parameters

Enter all values in the Polyglot UI **Configuration** tab. There is no separate YAML config file.

New installs show **placeholder defaults** until you enter your real TaHoma settings. The NodeServer will not connect while placeholders remain.

### Required

#### `gateway_pin`

TaHoma gateway PIN in `XXXX-XXXX-XXXX` format (12 digits with dashes).

- **Default (placeholder):** `0000-0000-0000` — replace with your PIN before starting
- **Example:** `2001-0001-1891`
- **Where to find:** Label on the bottom of the TaHoma unit, or TaHoma app → Menu → Help & Advanced Features → My Setup → TaHoma PIN

#### `tahoma_token`

Bearer token from TaHoma Developer Mode.

- **Default (placeholder):** 20 zeros — replace with your token before starting
- **Format:** Long alphanumeric string (typically 50+ characters); paste the token only, not a `Bearer ` prefix
- **Security:** Stored in Polyglot; used only to authenticate to your local gateway

### Optional

#### `gateway_ip`

Optional. Leave at the default unless you need an explicit address.

- **Default (placeholder):** `gateway-0000-0000-0000.local` — ignored; the NodeServer uses `gateway-{pin}.local` from your PIN
- **When to change:** If mDNS to `gateway-{pin}.local` is unreliable, enter the TaHoma **IP address** (for example `192.168.1.100`)
- **Important:** Assign the TaHoma a static IP or router DHCP reservation if you use an IP here

#### `verify_ssl`

Whether to verify the TaHoma HTTPS certificate.

- **Default:** `false`
- **Recommended:** Leave at `false`. TaHoma presents a self-signed certificate on your LAN; verification is not required for normal home use.

Setting **`true`** is optional and only makes sense if you install the [Somfy root CA][somfy-root-ca] on your **EISY or Polisy** so the system trusts that certificate. On FreeBSD (EISY/Polisy), copy the `.crt` file into the local trusted certs directory (for example `/usr/local/share/certs/`), then run `certctl rehash` as root over SSH. We do **not** recommend this for typical installations.

## TaHoma app scenes (optional)

**Shade control does not require Somfy cloud.** Only scene **Activate** may use cloud — and only if you choose to enter cloud credentials below.

- **Open / Close / Stop / My on shades**
  - Local API (LAN): Yes — always
  - Somfy cloud: Never
- **Discover scene node names**
  - Local API (LAN): Yes — from gateway
  - Somfy cloud: No
- **Scene Activate** (run a TaHoma app scene)
  - Local API (LAN): Usually **no** — local API lists scenes but omits device commands
  - Somfy cloud: Yes — when you set cloud email/password

TaHoma app scenes (Morning, All Close, etc.) are stored **server-side** on Somfy’s cloud ([Somfy Developer Mode limitation][somfy-scenes-issue]). The NodeServer still discovers them as **Scenario** nodes so you can use them in ISY programs — but **Activate** contacts `tahomalink.com` only when optional cloud credentials are configured.

**You can leave all cloud fields empty.** Scene nodes may appear after Discover; **Activate** is a no-op and **Last Command** stays unchanged. No errors, no cloud contact.

To enable scene Activate:

1. Enter the same email and password you use in the **TaHoma by Somfy** mobile app.
2. Set `tahoma_cloud_region` if login fails (see region table below).
3. Restart the NodeServer after saving configuration.

#### `tahoma_cloud_email` / `tahoma_cloud_password`

Optional. Same TaHoma app login. Stored in Polyglot on your ISY/EISY like other custom parameters.

- **Default:** empty (shades only — recommended if you do not use ISY scene Activate)
- **When set:** scene Activate runs via Somfy cloud; shades still use the local API only

#### `tahoma_cloud_region`

Somfy cloud hub for your account. **Default: `somfy_america` (North America).**

- **`somfy_america`** (default — North America)
  - Also accepted: `Somfy (North America)`, `north america`
  - For: United States, Canada, and other NA accounts
- **`somfy_europe`**
  - Also accepted: `Somfy (Europe)`, `europe`
  - For: Europe, UK, and other EU accounts
- **`somfy_oceania`**
  - Also accepted: `Somfy (Oceania)`, `oceania`
  - For: Australia, New Zealand, and other Oceania accounts

Change this only if cloud login fails with correct email/password — your region must match where you registered in the TaHoma app.

### Parameter reference

- **`gateway_pin`** — Required. Default: `0000-0000-0000`. Example: `2001-0001-1891`
- **`tahoma_token`** — Required. Default: 20 zeros. Example: token from TaHoma app
- **`gateway_ip`** — Optional. Default: `gateway-0000-0000-0000.local` (ignored). Example: `192.168.1.100`
- **`verify_ssl`** — Optional. Default: `false`. Example: `false`
- **`tahoma_cloud_email`** — Optional. Default: empty. Example: your TaHoma app login email
- **`tahoma_cloud_password`** — Optional. Default: empty. Example: your TaHoma app password
- **`tahoma_cloud_region`** — Optional. Default: **`somfy_america`**. Example: `somfy_europe`

## TaHoma setup

### Generating a Bearer token

1. Open the TaHoma app on your mobile device.
2. Tap **Menu** (bottom right) → **Configuration of the installation** → **Access the parameters**.
3. Tap the PIN number **7 times** to enable Developer Mode; accept the disclaimer.
4. Go to Menu → **Developer Mode**.
5. Tap **Generate Token** and copy the token immediately — it is only shown once.

If you lose the token, generate a new one in Developer Mode.

### Save and verify

1. Enter `gateway_pin` and `tahoma_token` (replace the placeholder defaults).
2. Leave `gateway_ip` at the default unless mDNS to `gateway-{pin}.local` fails; if you set an IP, use a static/reserved address on the TaHoma.
3. Leave `verify_ssl` at `false` unless you have installed the Somfy root CA on the EISY/Polisy.
4. **Optional:** add cloud credentials only if you want ISY **Activate** on TaHoma app scenes (see [TaHoma app scenes (optional)](#tahoma-app-scenes-optional)).
5. Click **Save**.
6. Start the NodeServer and check the log for successful authentication.
7. Run **Discover** on the controller node in the Admin Console.
8. Test Open/Close on a shade node.

### Network

The NodeServer reaches TaHoma on your LAN over HTTPS (port **8443**).

- **Default:** `gateway-{pin}.local` via mDNS (for example `gateway-2001-0001-1891.local`)
- **Fallback:** `gateway_ip` if mDNS is unreliable (static/reserved IP on the TaHoma recommended)

Ensure firewall rules allow HTTPS to the gateway.

### Polyglot shortPoll and longPoll

Polyglot calls **shortPoll** and **longPoll** on a schedule configured in the ISY/Polyglot interface (often every 10–60 seconds for shortPoll). **Leave these at the defaults** — do not change them unless Universal Devices support asks you to.

- **shortPoll** — Used: Yes (controller). Purpose: ISY heartbeat (DON/DOF), TaHoma reconnect watchdog, restarts event polling if it stopped
- **longPoll** — Used: No. Purpose: Ignored; TaHoma updates use the gateway event stream instead

Shade and scene nodes subscribe to shortPoll for Polyglot compatibility but do not poll the TaHoma box. All gateway communication (commands, events, health checks) runs in the NodeServer’s own background loop, not through Polyglot poll intervals.

## Troubleshooting

### Configuration errors

**Invalid Gateway PIN**

- Must match `^\d{4}-\d{4}-\d{4}$` (e.g. `2001-0001-1891`, not digits without dashes).

**Invalid Bearer token**

- Replace placeholder text with the token from the TaHoma app.
- Token must be at least 20 characters (typically 50+); no spaces or line breaks.
- Generate a new token if the old one was lost or revoked.

### Connection issues

**Cannot connect to TaHoma**

- Confirm TaHoma is online (green LED) and on the same network as Polisy/EISY.
- Try `ping gateway-{pin}.local`. If that fails, set `gateway_ip` to the TaHoma’s static/reserved IP.
- Verify Developer Mode is enabled and the token is current.
- Leave `verify_ssl` at `false` unless you installed the Somfy root CA on the EISY/Polisy.
- If the gateway was idle, **open the TaHoma mobile app** once — the local API on port 8443 sometimes does not respond until the app wakes the box. The NodeServer retries startup for up to 10 minutes and reconnects automatically while running.

**NodeServer won't start**

- Check the Polyglot log for validation errors on `gateway_pin` or `tahoma_token`.
- Restart Polyglot if dependencies failed to install: `sudo systemctl restart polyglot`

### Discovery and control

**No devices discovered**

- Confirm shades appear and respond in the TaHoma app.
- Wait a minute after startup, then right-click the controller → **Discover**.
- Review the NodeServer log for API errors.

**Shades don't respond**

- Test the shade in the TaHoma app first.
- Check RTS range (roughly 25–35 feet line of sight to the gateway).
- Check battery-powered motors for low battery.

**Position not updating**

- Applies to full **Shade** nodes (io/Zigbee), not **RTS Shade** nodes — RTS has no position feedback.
- Confirm the log shows the event polling loop running.
- Right-click the shade → **Query** to force a refresh.
- Restart the NodeServer if event polling stopped.

### RTS shades and Last Command

RTS devices are discovered as **RTS Shade** nodes (Id, Battery, **Last Command**, **Last Command Executed** — no position or motion fields).

**Last Command (GV7)** reports whether the TaHoma gateway finished handling your command:

- **—** — No command sent yet this session
- **Pending** — Gateway accepted the command (`execId` returned)
- **Completed** — Gateway reports the execution finished
- **Failed** — Gateway reports failure

**Last Command Executed (GV8)** records which shade command you last sent:

- **None** — At node startup (resets each restart)
- **Open**, **Close**, **Stop**, **My Position** — Set when that command is sent from the ISY

Use **Last Command Executed** in programs when you need to know *what* was sent; use **Last Command** when you need to know *whether the gateway finished* it.

**Important:** On RTS, the blind often stops moving long before **Last Command** shows **Completed**. The TaHoma gateway may keep the execution in a pending state for up to about a minute while its internal timers run — this is normal gateway behavior, not a stuck motor. **Completed** means the gateway finished processing the command, not that the shade reached a specific position.

The startup success notice in Polyglot clears automatically after 30 seconds.

### Scene Activate (optional, cloud-only)

Scene nodes list TaHoma app scenes from your gateway. **Activate** is optional and usually runs on Somfy cloud — not over the local Developer Mode API. Leave `tahoma_cloud_email` and `tahoma_cloud_password` empty if you only control individual shades.

- **Scene nodes appear but Activate does nothing** — Cloud credentials not set; expected if you chose shades-only
- **Activate fails; log mentions cloud region** — Wrong `tahoma_cloud_region` for your TaHoma account
- **Activate fails after setting credentials** — Check email/password; try `somfy_europe` vs `somfy_america`

See [TaHoma app scenes (optional)](#tahoma-app-scenes-optional) for the cloud region list.

### Easy UI after profile or NodeServer update

The **Java Admin Console** and **UD Mobile** often pick up profile changes after **Update Profile** and a console restart. **Easy UI** (Safari on Mac/iPad/iPhone) can keep a **stale cached copy** of the node tree or profile even after an EISY reboot and Safari restart.

If Easy UI shows errors like **Profiles loaded but nodedefs missing**, a blank node area, or **404** where nodes should appear — but Admin Console and UD Mobile look fine:

1. Run **Update Profile** on the TaHoma Controller (Polyglot restart also pushes profile on version change).
2. Close Easy UI completely (all Safari tabs/windows for the EISY URL).
3. **Clear Safari cache** for the EISY site (Safari → Settings → Privacy → Manage Website Data, or Develop → Empty Caches if enabled).
4. Reopen Easy UI and sign in again.

A full EISY reboot alone may **not** refresh Easy UI; clearing browser cache usually does.

### SSL certificate errors

The default is `verify_ssl` **`false`**, which skips verification of TaHoma’s self-signed certificate. That is appropriate for normal home use on a local network.

If you set `verify_ssl` to **`true`**, you must install the [Somfy root CA][somfy-root-ca] on the EISY or Polisy (SSH as root). On FreeBSD, copy the certificate into `/usr/local/share/certs/` (create the directory if needed), then run:

```bash
certctl rehash
```

We do not recommend enabling certificate verification unless you have a specific reason to do so.

## Uninstalling

1. Stop the NodeServer in Polyglot.
2. Delete the NodeServer.
3. Remove the NodeServer folder in the Admin Console if it remains.
4. Optionally revoke tokens in the TaHoma app Developer Mode.

## References

- [Project README][github-readme] — Overview and installation
- [Somfy Developer Mode API][somfy-dev-mode]
- [TaHoma documentation (Somfy Pro)][somfy-pro-docs]

[somfy-root-ca]: https://ca.overkiz.com/overkiz-root-ca-2048.crt
[somfy-scenes-issue]: https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode/issues/21
[somfy-dev-mode]: https://github.com/Somfy-Developer/Somfy-TaHoma-Developer-Mode
[somfy-pro-docs]: https://www.somfypro.com/tahomadocumentation
[github-readme]: https://github.com/sejgit/udi-tahoma-pg3x/blob/main/README.md
