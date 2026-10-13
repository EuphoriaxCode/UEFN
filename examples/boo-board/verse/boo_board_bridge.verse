# Boo Board: device transform (old /UnrealEngine.com/Temporary/SpatialMath) -> Scene Graph transform.
# Kept in its own file: importing both SpatialMath modules makes vector3/rotation/transform ambiguous elsewhere.

using { /Verse.org/SpatialMath }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }

BooBoardDeviceTransform<internal>(Device:creative_device)<transacts>:(/Verse.org/SpatialMath:)transform =
    FromTransform(Device.GetTransform())

# Succeeds when any player's character is within Radius cm of the device (old SpatialMath: X/Y/Z).
BooBoardPlayerWithin<internal>(Device:creative_device, Radius:float)<transacts><decides>:void =
    C := Device.GetTransform().Translation
    var Found:logic = false
    for (P : Device.GetPlayspace().GetPlayers(), Char := P.GetFortCharacter[]):
        Pos := Char.GetTransform().Translation
        DX := Pos.X - C.X
        DY := Pos.Y - C.Y
        DZ := Pos.Z - C.Z
        if (DX * DX + DY * DY + DZ * DZ <= Radius * Radius):
            set Found = true
    Found?
