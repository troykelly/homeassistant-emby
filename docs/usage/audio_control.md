# Audio Control (Volume & Mute)

> **Status**: Implemented & tested (Home Assistant ≥2025.6.0)

This document describes how the Emby for Home Assistant integration controls
*absolute* volume and the mute state of an Emby client, and why the payload
format matters.

The information was gathered while investigating
[GitHub issue #190 – *One-way audio control*](https://github.com/troykelly/homeassistant-emby/issues/190)
and validated against Emby v4.9 using the web UI, Android and LG TV clients.

---

## Remote-control commands used

| Action                              | Command  | JSON arguments | Notes |
| ----------------------------------- | -------- | -------------- | ----- |
| **Set absolute volume**             | `VolumeSet` | `{ "Volume": <int 0-100> }` | The value **must** be a number (not a string). |
| **Mute / Un-mute**                  | `Mute`      | `{ "Mute": <bool> }`        | Send `true` to mute, `false` to un-mute. |

The semantics are defined by the *GeneralCommand* schema in the official
Emby OpenAPI specification (`docs/emby/openapi.json`).

> 📌 Emby evaluates the **JSON data-type**, not just the lexical content.  If
> the integration passes `"55"` (a string) instead of `55` (a number) the
> server will accept the request but **silently ignore** it on many clients.

---

## Common pitfalls

1.  **String vs. number / boolean** – As described above, sending the wrong
    data-type causes the command to be treated as no-op by the client.
2.  **Out-of-range values** – Values outside 0-100 are clamped by the
    integration before transmission; negative numbers and floats are safe.
3.  **Legacy clients** – Very old Emby Theater builds (<2019) only support the
    *toggle* variant of `Mute` (no arguments).  All officially supported
    platforms honour the argument form shown above.

---

## Implementation details

The helpers live in `custom_components/embymedia/api.py`:

* `EmbyAPI.set_volume()` – clamps the Home Assistant `volume_level` (*float
  0.0-1.0*) and submits `VolumeSet` with an **integer** 0-100.
* `EmbyAPI.mute()` – forwards the boolean flag unchanged.

Both funnel into the private `_post_session_command()` utility which POSTs to
`/Sessions/{id}/Command`.

Extensive unit-tests were added in
`tests/unit/emby/test_api_helper_commands.py` to guarantee the correct JSON is
sent in future.

---

## Change-log

* **2025-06-24** – Initial documentation extracted from the investigation work
  carried out for issue #192 and the subsequent bug-fix pull request.
