# Testing & verification loop

1. `VerseToolset.BuildAll` → must be `[]`.
2. `CompileWidgetBlueprint` → must be `true` (errors are raised with the binding path).
3. Session:
```python
S='ValkyrieToolset.SessionToolset.'
if T(S+'GetSessionStatus',{})['returnValue']=='Connected': T(S+'PushChanges',{'bVerseOnly':False})
else: T(S+'StartSession',{})
if T(S+'GetGameState',{})['returnValue']=='Running': T(S+'StopGame',{})
# poll until 'CanStart', then
T(S+'StartGame',{})
```
   `PushChanges(bVerseOnly=True)` is much faster when only Verse changed.
4. Look at the client: `scripts/windows/capture_fortnite_window.ps1 -Out frame.png` (PrintWindow; works behind other windows).
   Capture a burst (e.g. 30 frames × 250 ms) and build a contact sheet to judge animations.
5. You **cannot click** in the client (SendInput is ignored). Add debug device options (auto-open, auto-claim, short day length,
   reset save on join) to drive flows, and ask the human to test real clicks/hover/Escape.
6. Put `Print("[Feature] ...")` on every click handler — the user can grep the editor Output Log to tell
   "click didn't arrive" from "logic failed".
7. Restore production settings afterwards and say so.

8. Logic you can't click yourself: add a **self-test device** that drives the logic from Verse and prints a before/after state line
   (example: `examples/lamp-showroom/verse/lamp_selftest_device.verse`). It proves the logic, not the real button press.
9. Session start validation needs exactly one Island Settings device; a failed start leaves a blocking "Unable to Play" modal.

Debug options in the daily reward device: `SecondsPerDay`, `ResetProgressOnJoin`, `DebugAutoClaimAfter`, `AutoOpenOnJoin`, `AutoCloseAfter`.

10. Spawn the player where you want to look: `StartSession(location={x,y,z}, rotation={pitch,yaw,roll})` (Play From Here),
    poll `GetSessionStatus` = Connected + `GetGameState` = Running, then record the client:
    `scripts/windows/record_window.ps1 -Process FortniteClient-Win64-Shipping -Seconds 12 -Fps 1` (frames + `frames.txt`).
11. "Validation failed": grep the editor log on disk for `UEFNValidation` — disallowed engine references are listed
    per asset (`MCP_RULES.md` §9b).

